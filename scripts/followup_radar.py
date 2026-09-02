#!/usr/bin/env python3
"""
followup_radar.py -- which live conversations have gone quiet, and whose turn it is.

WHY THIS EXISTS (27 Aug 2026)
Elena could not remember which company "GTM Engineer / AI Engineer" was. It turned
out to be Florencia Mayer at globaltalent.co: interviewed 21 Aug, files exchanged
both ways, and then six days of silence with HER message last. Nothing was broken
-- there was simply nothing watching. Five live processes in one week is more than
a person tracks reliably from an inbox with 335 unread.

response_detector.py already detects employer REPLIES, but it is imported only by
orchestrator.py, which runs under no cron and no PM2 -- so it has never produced a
stored result. This is deliberately NOT that. Detecting a reply answers "did they
write back". This answers the question that actually loses opportunities:

    whose turn is it, and how long has it been?

Two classes, and the second is the expensive one:

  OWED BY THEM  -- you sent last, N days ago. A nudge is free and often works.
  OWED BY YOU   -- THEY sent last and you have not replied. This is worse: a warm
                   employer is waiting on you right now.

SAFETY
- IMAP is opened READONLY. This script cannot alter, move or delete a message.
- Credentials are read from .env and never logged, printed or passed on argv.
- Read-only by design: it reports, it does not reply on anyone's behalf.

Usage:
    python3 scripts/followup_radar.py                 # print the report
    python3 scripts/followup_radar.py --notify        # also send to Telegram
    python3 scripts/followup_radar.py --hubspot       # also raise HubSpot tasks
    python3 scripts/followup_radar.py --days 60       # widen the window
"""
import email
import imaplib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, parseaddr

VJH_ENV = "/home/ubuntu/VibeJobHunterAIPA_AIMCF/.env"
CTO_ENV = "/home/ubuntu/cto-aipa/.env"

# Shared with the Telegram bot (cto-aipa). The radar PROPOSES; only a tap in
# Telegram dismisses. Nothing here ever deletes mail or touches a mailbox --
# "clean" means "stop showing me this thread", and it is reversible by editing
# one JSON file.
RADAR_DIR = os.environ.get("RADAR_STATE_DIR", "/home/ubuntu/cto-aipa/data")
DISMISSED_PATH = os.path.join(RADAR_DIR, "radar-dismissed.json")
PROPOSAL_PATH = os.path.join(RADAR_DIR, "radar-proposal.json")
# A thread this old with no movement is dead. Conservative on purpose: a school
# appointment four days old must never appear in a cleanup proposal.
CLEAN_AFTER_DAYS = int(os.environ.get("RADAR_CLEAN_AFTER_DAYS", "30"))
# A thread younger than this is never CLEARABLE, not even under "Show all".
# Elena cleared her daughter's school appointment twice in ten minutes: 4 days
# old, genuinely live, sitting in a column of identical-looking buttons right
# beside the dead recruiters she was pruning. Offering a one-tap clear on a
# fresh thread is inviting exactly that misfire. It still appears in the radar --
# it simply has no button.
MIN_CLEARABLE_DAYS = int(os.environ.get("RADAR_MIN_CLEARABLE_DAYS", "7"))


def load_dismissed():
    """{key: {"at": iso, "until": iso|None}} -- `until` set means snoozed, not dead."""
    try:
        with open(DISMISSED_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def is_hidden(key, dismissed, now):
    """Hidden from the RADAR entirely. Only a dismissal does this."""
    rec = dismissed.get(key)
    if not rec:
        return False
    if rec.get("kind") == "kept":
        return False  # kept = still mine, keep showing it
    until = rec.get("until")
    if not until:
        return True  # permanently dismissed
    try:
        return now < datetime.fromisoformat(until)
    except Exception:
        return True


def is_kept(key, dismissed, now):
    """Still on the radar, but do not keep ASKING me to clear it.

    "Keep" and "hide" are different answers and collapsing them was a bug: the
    first version snoozed a kept thread, which removed from the radar the very
    thread she had just said she wanted to watch.
    """
    rec = dismissed.get(key)
    if not rec or rec.get("kind") != "kept":
        return False
    until = rec.get("until")
    if not until:
        return True
    try:
        return now < datetime.fromisoformat(until)
    except Exception:
        return False

# A conversation only counts once both sides have spoken. These senders never
# speak -- they announce. Counting them would bury the real threads.
NOISE_SENDER = re.compile(
    r"(no-?reply|notification|newsletter|digest|mailer|bounce|do-?not-?reply"
    r"|calendar|billing|invoice|receipt|support@|noreply)",
    re.I,
)
NOISE_SUBJECT = re.compile(
    r"^(reminder:|invitation:|updated invitation:|canceled event:|accepted:|declined:"
    r"|your meeting recap|weekly digest|re: invitation)",
    re.I,
)


def load_env(path):
    """Minimal .env reader. Values with spaces or < > break `source`, not this."""
    out = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return out


def decode(s):
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def norm_subject(s):
    """Strip reply/forward prefixes so a thread collapses to one key."""
    s = decode(s or "")
    for _ in range(6):
        new = re.sub(r"^\s*(re|fwd|fw|rv|aw)\s*:\s*", "", s, flags=re.I)
        if new == s:
            break
        s = new
    return re.sub(r"\s+", " ", s).strip().lower()


def fetch(host, user, pw, folder, since):
    """Read headers from one folder. READONLY -- cannot modify the mailbox."""
    rows = []
    try:
        M = imaplib.IMAP4_SSL(host)
        M.login(user, pw)
    except Exception as e:
        print(f"  ! {host} login failed: {type(e).__name__}", file=sys.stderr)
        return rows
    try:
        status, _ = M.select(f'"{folder}"', readonly=True)
        if status != "OK":
            return rows
        crit = f'(SINCE "{since.strftime("%d-%b-%Y")}")'
        status, data = M.search(None, crit)
        if status != "OK" or not data or not data[0]:
            return rows
        ids = data[0].split()
        # Newest first, capped -- this is a radar, not an archive crawl.
        for chunk in [ids[i:i + 200] for i in range(0, len(ids), 200)][-4:]:
            seq = b",".join(chunk).decode()
            status, msgs = M.fetch(seq, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM TO DATE)])")
            if status != "OK":
                continue
            for part in msgs:
                if not isinstance(part, tuple):
                    continue
                msg = email.message_from_bytes(part[1])
                try:
                    when = parsedate_to_datetime(msg.get("Date"))
                    if when.tzinfo is None:
                        when = when.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                rows.append(
                    {
                        "subject": msg.get("Subject", ""),
                        "from": msg.get("From", ""),
                        "to": msg.get("To", ""),
                        "date": when,
                    }
                )
    finally:
        try:
            M.close()
        except Exception:
            pass
        M.logout()
    return rows


def build(inbox, sent, mine):
    """Pair inbound and outbound by normalised subject; decide whose turn it is."""
    threads = defaultdict(lambda: {"in": None, "out": None, "who": "", "subject": ""})
    for r in inbox:
        key = norm_subject(r["subject"])
        if not key or NOISE_SUBJECT.search(decode(r["subject"])):
            continue
        addr = parseaddr(r["from"])[1].lower()
        if not addr or NOISE_SENDER.search(addr) or addr in mine:
            continue
        t = threads[key]
        t["subject"] = t["subject"] or decode(r["subject"])
        if t["in"] is None or r["date"] > t["in"]:
            t["in"] = r["date"]
            t["who"] = addr
    for r in sent:
        key = norm_subject(r["subject"])
        if not key or key not in threads:
            continue
        t = threads[key]
        if t["out"] is None or r["date"] > t["out"]:
            t["out"] = r["date"]
    return threads


# ---------------------------------------------------------------------------
# HubSpot -- the queue lives where the money queue lives
#
# Telegram is a notification: it scrolls away and takes the task with it.
# HubSpot is the playground, so a stalled thread has to become a real Task with
# an owner and a due date, sitting in the same pipeline as everything else.
#
# The hard part is NOT creating the task, it is creating it ONCE. This runs
# daily; a blind create would manufacture ~15 duplicates a day and make the
# queue useless within a week -- the same shape as the blog publishing
# near-duplicates. So every task carries a deterministic subject that doubles as
# its dedupe key, and we search for an open one before writing.
# ---------------------------------------------------------------------------
HS = "https://api.hubapi.com"
TASK_TO_CONTACT = 204  # HUBSPOT_DEFINED association type


def hs_call(token, method, path, payload=None):
    """
    Paced and 429-aware. HubSpot enforces a SECONDLY limit, and the first run
    tripped it: two threads lost their task because the DEDUPE SEARCH 429'd.
    That failed safe -- an errored search skips rather than creating a duplicate
    -- but a skipped task is a silently dropped follow-up, which is the thing
    this whole script exists to prevent. So pace, and retry rather than drop.
    """
    data = None if payload is None else json.dumps(payload).encode()
    for attempt in range(4):
        req = urllib.request.Request(f"{HS}{path}", data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            time.sleep(0.3)  # stay under the secondly limit by construction
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read().decode()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:200]
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}") from None
    raise RuntimeError("HTTP 429: retries exhausted")


def hs_find_contact(token, addr):
    res = hs_call(token, "POST", "/crm/v3/objects/contacts/search", {
        "filterGroups": [{"filters": [
            {"propertyName": "email", "operator": "EQ", "value": addr}]}],
        "properties": ["email"], "limit": 1,
    })
    hits = res.get("results") or []
    return hits[0]["id"] if hits else None


def hs_upsert_contact(token, addr):
    existing = hs_find_contact(token, addr)
    if existing:
        return existing
    try:
        created = hs_call(token, "POST", "/crm/v3/objects/contacts",
                          {"properties": {"email": addr}})
        return created.get("id")
    except RuntimeError as e:
        # 409 = created between our search and our write. Re-read, do not guess.
        if "409" in str(e):
            return hs_find_contact(token, addr)
        raise


def hs_open_task_exists(token, subject):
    """The dedupe gate. An open task with this exact subject means today's run
    has nothing new to say -- the thread is already in her queue."""
    res = hs_call(token, "POST", "/crm/v3/objects/tasks/search", {
        "filterGroups": [{"filters": [
            {"propertyName": "hs_task_subject", "operator": "EQ", "value": subject},
            {"propertyName": "hs_task_status", "operator": "NEQ", "value": "COMPLETED"},
        ]}],
        "properties": ["hs_task_subject"], "limit": 1,
    })
    return bool(res.get("results"))


def hs_sync(token, owner, owed_by_you, owed_by_them):
    created, skipped, failed = 0, 0, 0
    batches = [("YOUR MOVE", "HIGH", 4, owed_by_you),
               ("NUDGE THEM", "MEDIUM", 24, owed_by_them)]
    for label, priority, due_hours, rows in batches:
        for age, t, *_rest in rows:
            addr = t["who"]
            subject = f"[FOLLOWUP-RADAR] {label} — {addr} — {t['subject'][:48]}"
            try:
                if hs_open_task_exists(token, subject):
                    skipped += 1
                    continue
                cid = hs_upsert_contact(token, addr)
                due = datetime.now(timezone.utc) + timedelta(hours=due_hours)
                body = (
                    f"Thread: {t['subject']}\n"
                    f"Counterpart: {addr}\n"
                    f"Silent for: {age} days\n"
                    f"Whose turn: {'THEY wrote last — she owes a reply' if label == 'YOUR MOVE' else 'SHE wrote last — a nudge is free'}\n\n"
                    f"Raised automatically by followup_radar.py. Closing this task is the "
                    f"signal it is handled; the radar will not re-open it while it is open."
                )
                payload = {"properties": {
                    "hs_task_subject": subject,
                    "hs_task_body": body,
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": priority,
                    "hs_timestamp": due.isoformat(),
                    "hubspot_owner_id": owner,
                }}
                if cid:
                    payload["associations"] = [{
                        "to": {"id": cid},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED",
                                   "associationTypeId": TASK_TO_CONTACT}],
                    }]
                hs_call(token, "POST", "/crm/v3/objects/tasks", payload)
                created += 1
            except Exception as e:
                failed += 1
                print(f"  ! hubspot {addr}: {e}", file=sys.stderr)
    return created, skipped, failed


def main():
    days = 45
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            pass
    notify = "--notify" in sys.argv
    to_hubspot = "--hubspot" in sys.argv

    env = load_env(VJH_ENV)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    mine = set()
    inbox, sent = [], []

    boxes = [
        ("imap.zoho.com", env.get("ZOHO_EMAIL"), env.get("ZOHO_APP_PASSWORD"), "Sent"),
        ("imap.gmail.com", env.get("GMAIL_EMAIL"), env.get("GMAIL_APP_PASSWORD"), "[Gmail]/Sent Mail"),
    ]
    for host, user, pw, sent_folder in boxes:
        if not user or not pw:
            print(f"  - {host}: no credentials, skipped")
            continue
        mine.add(user.lower())
        got_in = fetch(host, user, pw, "INBOX", since)
        got_out = fetch(host, user, pw, sent_folder, since)
        print(f"  - {host}: {len(got_in)} inbox / {len(got_out)} sent (last {days}d)")
        inbox += got_in
        sent += got_out

    if not inbox:
        print("\nNothing could be read. This is 'not measured', not 'nothing waiting'.")
        sys.exit(1)

    threads = build(inbox, sent, mine)
    now = datetime.now(timezone.utc)
    owed_by_you, owed_by_them = [], []

    dismissed = load_dismissed()
    hidden = 0
    for key, t in threads.items():
        if t["in"] is None or t["out"] is None:
            continue  # one-sided: never a real conversation
        if is_hidden(key, dismissed, now):
            hidden += 1
            continue  # she has already said this one is done
        if t["out"] > t["in"]:
            age = (now - t["out"]).days
            if age >= 3:
                owed_by_them.append((age, t, key))
        else:
            age = (now - t["in"]).days
            if age >= 2:
                owed_by_you.append((age, t, key))

    owed_by_you.sort(key=lambda x: x[0], reverse=True)  # key only: equal ages must not fall through to comparing dicts
    owed_by_them.sort(key=lambda x: x[0], reverse=True)

    lines = []
    if owed_by_you:
        lines.append("🔴 THEY WROTE LAST — your move")
        for age, t, _k in owed_by_you[:12]:
            lines.append(f"  {age}d  {t['who']}\n       {t['subject'][:70]}")
    if owed_by_them:
        lines.append("")
        lines.append("🟡 YOU WROTE LAST — gone quiet, a nudge is free")
        for age, t, _k in owed_by_them[:12]:
            lines.append(f"  {age}d  {t['who']}\n       {t['subject'][:70]}")
    if not lines:
        lines.append("✅ No stalled conversations. Everything is either fresh or closed.")

    report = "\n".join(lines)
    print("\n=== FOLLOW-UP RADAR ===")
    print(report)
    print(
        f"\n{len(owed_by_you)} waiting on you · {len(owed_by_them)} waiting on them "
        f"· {len(threads)} two-way threads in {days}d"
        + (f" · {hidden} hidden by you" if hidden else "")
    )

    if to_hubspot:
        cto = load_env(CTO_ENV)
        hs_token = cto.get("HUBSPOT_API_KEY")
        owner = cto.get("HUBSPOT_OWNER_ID", "91612860")
        if not hs_token:
            print("  ! HUBSPOT_API_KEY not set — HubSpot sync skipped", file=sys.stderr)
        else:
            c, s_, f = hs_sync(hs_token, owner, owed_by_you, owed_by_them)
            print(f"  hubspot: {c} task(s) created, {s_} already open, {f} failed")

    if notify:
        tok = load_env(CTO_ENV).get("TELEGRAM_BOT_TOKEN")
        chat = load_env(CTO_ENV).get("CONCIERGE_TG_CHAT")
        if not tok or not chat:
            print("  ! Telegram not configured — printed only", file=sys.stderr)
            return
        # Cleanup proposal. The radar recomputes from the mailbox every morning,
        # so a dead thread returns forever. Propose the clearly-dead ones and let
        # her approve with ONE TAP; the bot writes the ledger. Nothing is cleaned
        # without that tap, and nothing touches the mailbox -- "clean" here means
        # "stop showing me this thread", and it is reversible by editing one file.
        # Every listed thread becomes a candidate, not only the old ones.
        # The threshold decides what is PROPOSED; it must not decide what is
        # POSSIBLE. Elena knows a contact has vanished long before a day counter
        # agrees, and a cleaner that refuses to clear what she can plainly see is
        # dead just sends her back to doing it by hand.
        allrows = []
        for lane, rows in (("them", owed_by_you), ("you", owed_by_them)):
            for age, t, key in rows[:12]:
                if age < MIN_CLEARABLE_DAYS:
                    continue  # too fresh to be a cleanup candidate -- listed, not clearable
                allrows.append({"key": key, "who": t["who"],
                                "subject": t["subject"][:90], "age": age, "lane": lane,
                                # A thread she has explicitly kept is never proposed
                                # again while the keep is live -- but it stays listed.
                                "stale": age >= CLEAN_AFTER_DAYS
                                and not is_kept(key, dismissed, now)})
        allrows.sort(key=lambda x: x["age"], reverse=True)
        stale = [r for r in allrows if r["stale"]]

        markup = None
        if allrows:
            pid = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
            try:
                os.makedirs(RADAR_DIR, exist_ok=True)
                with open(PROPOSAL_PATH, "w", encoding="utf-8") as fh:
                    # EVERY listed thread is written, not only the stale ones, so
                    # "Show all" can offer any of them without a second run.
                    json.dump({"id": pid, "created": now.isoformat(), "items": allrows},
                              fh, indent=2)
            except Exception as e:
                print("  ! could not write proposal: " + type(e).__name__, file=sys.stderr)
                allrows = []
        if allrows:
            if stale:
                report += (
                    "\n\n\U0001F9F9 " + str(len(stale))
                    + " thread(s) silent " + str(CLEAN_AFTER_DAYS) + "d+ look dead."
                    + "\nTap one to clear it — or Show all to prune anything here."
                )
            else:
                report += "\n\n\U0001F9F9 Nothing looks dead by age. Show all to prune by hand."
            # One button per thread. The threshold decides what is PROPOSED, never
            # what is POSSIBLE -- she knows a contact has vanished long before a
            # day counter agrees.
            rows = []
            for n, it in enumerate(allrows):
                if not it["stale"]:
                    continue
                who = it["who"].split("@")[0][:18]
                dom = it["who"].split("@")[-1][:14]
                rows.append([{
                    "text": "🧹 " + str(it["age"]) + "d  " + who + "@" + dom,
                    "callback_data": "rdrone:" + pid + ":" + str(n),
                }])
            tail = []
            if len(allrows) > len(stale):
                tail.append({"text": "📋 Show all " + str(len(allrows)),
                             "callback_data": "rdrall:" + pid})
            if stale:
                tail.append({"text": "🧹 Clear " + str(len(stale)),
                             "callback_data": "rdrclean:" + pid})
            tail.append({"text": "Keep all", "callback_data": "rdrkeep:" + pid})
            rows.append(tail)
            markup = json.dumps({"inline_keyboard": rows})

        text = "📡 Follow-up radar\n\n" + report
        payload = {"chat_id": chat, "text": text[:3900], "disable_web_page_preview": "true"}
        if markup:
            payload["reply_markup"] = markup
        body = urllib.parse.urlencode(payload).encode()
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{tok}/sendMessage", data=body
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"  telegram: HTTP {r.status}")
        except Exception as e:
            print(f"  ! telegram failed: {type(e).__name__}", file=sys.stderr)


if __name__ == "__main__":
    main()
