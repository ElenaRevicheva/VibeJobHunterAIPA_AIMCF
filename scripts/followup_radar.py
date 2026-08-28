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
    python3 scripts/followup_radar.py --days 60       # widen the window
"""
import email
import imaplib
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, parseaddr

VJH_ENV = "/home/ubuntu/VibeJobHunterAIPA_AIMCF/.env"
CTO_ENV = "/home/ubuntu/cto-aipa/.env"

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


def main():
    days = 45
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            pass
    notify = "--notify" in sys.argv

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

    for key, t in threads.items():
        if t["in"] is None or t["out"] is None:
            continue  # one-sided: never a real conversation
        if t["out"] > t["in"]:
            age = (now - t["out"]).days
            if age >= 3:
                owed_by_them.append((age, t))
        else:
            age = (now - t["in"]).days
            if age >= 2:
                owed_by_you.append((age, t))

    owed_by_you.sort(key=lambda x: x[0], reverse=True)  # key only: equal ages must not fall through to comparing dicts
    owed_by_them.sort(key=lambda x: x[0], reverse=True)

    lines = []
    if owed_by_you:
        lines.append("🔴 THEY WROTE LAST — your move")
        for age, t in owed_by_you[:12]:
            lines.append(f"  {age}d  {t['who']}\n       {t['subject'][:70]}")
    if owed_by_them:
        lines.append("")
        lines.append("🟡 YOU WROTE LAST — gone quiet, a nudge is free")
        for age, t in owed_by_them[:12]:
            lines.append(f"  {age}d  {t['who']}\n       {t['subject'][:70]}")
    if not lines:
        lines.append("✅ No stalled conversations. Everything is either fresh or closed.")

    report = "\n".join(lines)
    print("\n=== FOLLOW-UP RADAR ===")
    print(report)
    print(
        f"\n{len(owed_by_you)} waiting on you · {len(owed_by_them)} waiting on them "
        f"· {len(threads)} two-way threads in {days}d"
    )

    if notify:
        tok = load_env(CTO_ENV).get("TELEGRAM_BOT_TOKEN")
        chat = load_env(CTO_ENV).get("CONCIERGE_TG_CHAT")
        if not tok or not chat:
            print("  ! Telegram not configured — printed only", file=sys.stderr)
            return
        text = "📡 Follow-up radar\n\n" + report
        body = urllib.parse.urlencode(
            {"chat_id": chat, "text": text[:3900], "disable_web_page_preview": "true"}
        ).encode()
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
