"""
judge_feedback_sync.py — the weekly "learn from Elena's real behavior" loop (July 9 2026).

Adapts JobCopilot's "delete jobs you don't like — this trains your copilot" idea to VJH,
honestly: pulls [HIRING-*] deal outcomes from HubSpot and writes the titles Elena
demonstrably ACTED ON vs REJECTED into autonomous_data/judge_feedback.json. The LLM judge
(src/core/llm_judge.py) appends those as few-shot taste-calibration examples to its prompt
— so the judge drifts toward her demonstrated behavior without anyone editing code.

Signal honesty (learned July 9 from the outcome report): the bot itself files new
iron-clad fits into qualifiedtobuy ("I Act TODAY"), so that stage does NOT prove Elena
acted. Only stages she moves deals into by hand count:
  POSITIVE  = presentationscheduled ("I Act this week"), contractsent ("They replied"),
              closedwon ("Won")
  NEGATIVE  = closedlost ("No fit / Rejected / ghosted")

Fail-safe by design:
  - If HubSpot is unreachable or returns nothing, the existing judge_feedback.json is
    LEFT UNTOUCHED (atomic tmp+rename write happens only on success).
  - If the file is absent/invalid, the judge prompt is simply unchanged (see
    _feedback_block in llm_judge.py) — identical to pre-feature behavior.

2026-08-14 — the loop now learns her REASONS, not just her verdicts. A rejected
title teaches the judge nothing; "manual coding required" teaches it a rule. Each
negative carries her own note text, and when her note only points at an attached
screenshot ("look at the image") the screenshot itself is read. See _rejection_reason
and _read_screenshot. Screenshot reading needs the `files` scope on the HubSpot
private app — without it that half is silently skipped and text reasons still work.

Runs DAILY via cron on Oracle (ubuntu crontab) — it is a read-only HubSpot pull, and
a week of her manual triage was sitting unlearned between Sunday runs. Stdlib-only —
no venv dependencies.

Usage:  python3 scripts/judge_feedback_sync.py
Key:    HUBSPOT_API_KEY from env, VJH .env, or /home/ubuntu/cto-aipa/.env (in that order).
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "autonomous_data" / "judge_feedback.json"

POSITIVE_STAGES = {"presentationscheduled", "contractsent", "closedwon"}
NEGATIVE_STAGES = {"closedlost"}

# ── ELENA'S OWN APPLICATIONS: the strongest signal there is (added 2026-08-09) ──
# Her "⏳ Sent" stage is `decisionmakerboughtin`, and it was in NEITHER set — so
# every job she personally chose to apply to was invisible to this loop. 18 deals
# of the clearest possible taste data ("I wanted this one enough to apply"),
# ignored, while the loop trained on 1 positive.
#
# It is NOT enough to count the whole stage: the label is "AI or Elena sent
# outreach", so bot-sent outreach lands here too, and training on the bot's own
# decisions would just teach the judge to agree with itself.
#
# The disambiguator is her note. Verified against the real notes on these deals:
#     "i applied manually"      "i applied."      "Applied ⚠️ MANUAL APPLY..."
# The trap: VJH's OWN note reads "⚠️ MANUAL APPLY REQUIRED — VJH found this; you
# submit", which contains "APPLY". Searching naively marks every deal as applied.
# And she sometimes prepends her word to the bot's note, so excluding notes that
# mention the template would miss those. Therefore: strip the bot's template
# first, then look for a past-tense "applied" in whatever SHE wrote.
MANUAL_APPLY_STAGE = "decisionmakerboughtin"
_BOT_NOTE_TEMPLATE = re.compile(
    r"manual apply required.*?(?:you submit\.?|apply page)"
    r"|vjh found this[^.]*\.?"
    r"|open job\s*/\s*apply page"
    r"|source:\s*\w+"
    # The Telegram-approval note is ALSO a bot template and was not being stripped —
    # verified on "Machine Learning Engineer @ Micro1", whose only note is this.
    r"|needs manual apply"
    r"|approve in telegram:?\s*\S*"
    r"|score:\s*\d+"
    r"|apply(?:\s+at)?:\s*https?://\S+"
    # Leftovers of the template above. Without these the residual of a bot-only
    # note is "⚠️ Apply:", which is 9 characters and therefore sailed through the
    # length check — every negative came back with "her reason: ⚠️ Apply".
    r"|⚠️|⚠"
    r"|\bapply\s*:"
    r"|\bopen job\b"
    r"|---\s*cover\s*/\s*outreach letter.*",
    re.IGNORECASE | re.DOTALL,
)

# Elena does not write one fixed word. Verified against the real notes on her own
# deals, the sync used to see only `\bapplied\b` and therefore threw away
# "I have just submitted manually" (AI Automation & Operations @ Rove Concepts) —
# a genuine application, invisible to the loop purely on vocabulary.
_APPLIED_MARK = re.compile(
    r"\b(applied|submitted|aplicad[oa]|apliqu[ée]|postul[ée]|enviad[oa])\b"
    r"|\bsent (?:it|in|my|the)\b",
    re.IGNORECASE,
)


def _elena_said_applied(notes) -> bool:
    """True only if SHE wrote an 'applied' marker, after removing VJH's template."""
    for n in notes:
        human = _BOT_NOTE_TEMPLATE.sub(" ", re.sub(r"<[^>]+>", " ", n.get("body") or ""))
        if _APPLIED_MARK.search(human):
            return True
    return False


# ── HER REASONS, NOT JUST HER VERDICTS (added 2026-08-14) ────────────────────
# The loop used to learn the TITLE of a rejected job and nothing else, while the
# actual explanation sat unread in the deal note. Cost, verified in one day's log:
# at 14:32 the judge surfaced "Forward Deployed Engineer @ Blink UX" praising it as
# "hands-on, aligning with Elena's ..." — and she killed it minutes later with
# "manual coding required". The judge had her taste exactly inverted on that axis
# and the correction was already written down.
#
# What survives extraction must be HER voice, not a pasted job posting. Two traps
# seen in production: (1) notes that are just the posting re-pasted (Mercor's
# "Enterprise AI Interface Specialist Save Mercor connects ..."), (2) notes that are
# a bare source URL. Both are stripped or dropped below.
_REASON_MAX = 160
_NAV_NOISE = re.compile(
    r"torre (?:leads? |lead |redirected )?(?:to |here)?\s*(?:linkedin(?: post)?)?"
    r"|look at the image|look -|seems like it is",
    re.IGNORECASE,
)
_POSTING_PASTE = re.compile(
    r"employee count|salary:|per hour|stay tuned|save\b.{0,40}connects",
    re.IGNORECASE,
)


def _rejection_reason(notes, title: str) -> str:
    """Her own words on why a job was a No-fit, or '' when she left none.

    Never raises and never returns a pasted posting — a bad reason in the judge
    prompt is worse than no reason, because it reads as taste when it is noise.
    """
    for n in notes:
        human = re.sub(r"<[^>]+>", " ", n.get("body") or "")
        human = _BOT_NOTE_TEMPLATE.sub(" ", human)
        human = re.sub(r"https?://\S+", " ", human)          # source links carry no taste
        human = re.sub(r"&[a-z]+;", " ", human)              # &amp; etc from HubSpot HTML
        human = _NAV_NOISE.sub(" ", human)
        human = re.sub(r"\s+", " ", human).strip(" -–—.,:;/|")
        # A length check is not enough — it is what let "⚠️ Apply" through. A real
        # reason is a sentence, so demand at least three actual words.
        if len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", human)) < 3:
            continue
        # A note that opens with the job's own title is the posting re-pasted.
        if title and human[:40].lower().startswith(title[:20].lower()):
            continue
        if _POSTING_PASTE.search(human[:120]):
            continue
        return human[:_REASON_MAX].strip()
    return ""


# ── THE SCREENSHOT SHE ATTACHES (added 2026-08-14) ───────────────────────────
# When Elena rejects a job she often writes a pointer, not the reason itself —
# "Require experienced engineering - look at the image", "Not a fit. Look at
# requirements" — and attaches a screenshot of the posting's requirements. The
# reason is in the PIXELS. Verified live: 3 of this week's No-fit notes carry an
# attachment (WWT, AlphaLife Sciences, LevelUp Labs).
#
# ⚠️ DORMANT UNTIL A SCOPE IS GRANTED. The private-app token (pat-na1-ccf57) is
# refused by every file endpoint:
#     403 requiredGranularScopes: ["files", "files.read", "files.ui_hidden.read"]
# Until Elena ticks `files` on the private app, _read_screenshot returns "" and
# the loop behaves exactly as if the feature did not exist. Nothing breaks; the
# text reason is used instead. The moment the scope exists this lights up on its
# own with no code change.
#
# Cost control: vision is billed per image, and the same screenshot would be
# re-read on every run forever. Results are cached by HubSpot file id, so each
# screenshot is paid for exactly once.
SHOT_CACHE = REPO / "autonomous_data" / "screenshot_reasons.json"
_VISION_MODEL = "gpt-4o-mini"
_VISION_PROMPT = (
    "This screenshot is from a job posting that Elena looked at and then REJECTED. "
    "In ONE short sentence (max 20 words), state the concrete requirement visible here "
    "that would disqualify her — e.g. a degree, years of hands-on coding, a specific "
    "stack, an on-site/country restriction, seniority. Answer with the requirement only, "
    "no preamble. If the image shows no such requirement, answer exactly: NONE"
)
_scope_warned = []


def _load_shot_cache() -> dict:
    try:
        return json.loads(SHOT_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_shot_cache(cache: dict) -> None:
    try:
        SHOT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SHOT_CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(SHOT_CACHE)
    except Exception:
        pass


def _file_bytes(key: str, file_id: str):
    """(bytes, mime) for a HubSpot note attachment, or (None, '') if unavailable.

    A 403 here is the missing `files` scope, not a bug — say it once, then stay quiet.
    """
    try:
        req = urllib.request.Request(
            f"https://api.hubapi.com/files/v3/files/{file_id}",
            headers={"Authorization": "Bearer " + key},
        )
        meta = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        if "403" in str(e) and not _scope_warned:
            _scope_warned.append(1)
            print("  screenshots SKIPPED — HubSpot token lacks the `files` scope "
                  "(grant `files.read` on the private app to switch this on)")
        return None, ""
    url, ext = meta.get("url"), (meta.get("extension") or "").lower()
    if not url or ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        return None, ""
    try:
        raw = urllib.request.urlopen(url, timeout=30).read()
    except Exception:
        return None, ""
    if len(raw) > 6_000_000:          # don't post a huge upload to the vision API
        return None, ""
    return raw, "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


def _read_screenshot(key: str, file_ids, cache: dict) -> str:
    """What the attached screenshot says disqualifies her. '' when unavailable."""
    import base64
    ok = _read_env_file(REPO / ".env", "OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    for fid in file_ids[:2]:
        if fid in cache:                       # already paid for — never re-read
            if cache[fid]:
                return cache[fid]
            continue
        if not ok:
            return ""
        raw, mime = _file_bytes(key, fid)
        if not raw:
            return ""
        payload = json.dumps({
            "model": _VISION_MODEL,
            "max_tokens": 60,
            "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": _VISION_PROMPT},
                {"type": "image_url", "image_url": {"url":
                    f"data:{mime};base64," + base64.b64encode(raw).decode()}},
            ]}],
        }).encode()
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=payload, method="POST",
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + ok})
            out = json.loads(urllib.request.urlopen(req, timeout=60).read())
            txt = (out["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            print(f"  screenshot {fid}: vision call failed ({str(e)[:90]})")
            return ""
        txt = "" if txt.upper().startswith("NONE") else txt[:_REASON_MAX]
        cache[fid] = txt
        if txt:
            return txt
    return ""


# 6 was starving the judge: 13 deals all-time carry a confirmed applied-by-Elena
# note and 68 sit in No-fit, so five sixths of her demonstrated taste never
# reached the prompt. The prompt is small (~2.8 KB) — there is room.
MAX_EXAMPLES = 12
NOISE = re.compile(r"smoke|delete me|\btest\b", re.IGNORECASE)

# ── TITLE QUALITY FILTERS (added 2026-07-30) ─────────────────────────────────
# Verified defect: the "contractsent" (They replied) stage is fed by the response
# detector, whose deal names are EMAIL SUBJECTS, not job titles. So the judge was
# being taught that these are roles Elena wants:
#     "Invitación actualizada: Meeting mar 20 de ene de 2026 10am"
#     "Action Required: Step 2 of your 10x Application @ 10x-hire"
#     "[AIdeazz] Inquiry — Velena Adam @ Aideazz"
# Few-shot examples like that are pure noise. Two filters now apply to BOTH lists:
#   1. drop anything shaped like an email subject / calendar invite
#   2. keep only titles containing an actual ROLE noun
EMAIL_SUBJECT = re.compile(
    r"^(re|fwd|fw)\b|invitation|invitaci|updated invite|meeting|calendar|"
    r"next steps?|step \d|action required|additional info|your application|"
    r"application (for|received|update)|you'?re invited|thank you for|"
    r"complete your|reminder|follow[- ]?up|zoom|interview with|inquiry",
    re.IGNORECASE,
)
# `coder` and `residence` were added 2026-08-14: "Vibe Coder in Residence — Full
# Time @ Zagged" carried her own "Applied manually" note and was still discarded
# here, purely because no word in this list appeared in the title.
ROLE_NOUN = re.compile(
    r"\b(engineer|developer|architect|specialist|scientist|analyst|designer|"
    r"manager|lead|head|director|consultant|builder|strategist|marketer|"
    r"operations|ops|automation|技術|programmer|administrator|coordinator|"
    r"technician|advisor|officer|founder|cto|pm|product owner|"
    r"coder|residence|generalist|technologist)\b",
    re.IGNORECASE,
)


# A POSITIVE example must not contradict the hard filter. The response detector
# names deals after email subjects, so surviving titles included "1st Interview –
# Full Stack Python Developer" and "Event Confirmation For Senior Full-Stack
# Engineer" — both are titles fit_gate EXCLUDES as heavy hand-coding. Feeding them
# to the judge as "roles she wants" would actively erode the filter it enforces.
# Mirrors src/core/fit_gate.py (kept as a literal list because this script is
# stdlib-only and must run under system python3 with no repo imports).
OFF_LANE_TITLE = re.compile(
    r"full[- ]?stack|backend engineer|front[- ]?end engineer|senior software engineer|"
    r"staff engineer|staff software|principal engineer|"
    r"qa automation|automation qa|test automation|sdet|quality assurance|"
    r"it automation|infrastructure automation|network automation|"
    r"industrial automation|rpa developer|marketing automation|sales automation",
    re.IGNORECASE,
)


def _is_usable_title(title: str, positive: bool = False) -> bool:
    """A few-shot example is only useful if it reads like a real job title.

    `positive=True` additionally requires the title to be on-lane — a bad positive
    is far more damaging than a missing one, since it teaches the judge to approve
    what the gate is built to reject.
    """
    if not title or NOISE.search(title):
        return False
    if EMAIL_SUBJECT.search(title):
        return False
    if not ROLE_NOUN.search(title):
        return False
    if positive and OFF_LANE_TITLE.search(title):
        return False
    return True


def _read_env_file(path: Path, name: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _hubspot_key() -> str:
    return (
        os.environ.get("HUBSPOT_API_KEY", "").strip()
        or _read_env_file(REPO / ".env", "HUBSPOT_API_KEY")
        or _read_env_file(Path("/home/ubuntu/cto-aipa/.env"), "HUBSPOT_API_KEY")
    )


def _search_deals(key: str) -> list:
    deals, after = [], None
    while True:
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "dealname", "operator": "CONTAINS_TOKEN", "value": "HIRING"},
            ]}],
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            "properties": ["dealname", "dealstage", "hs_lastmodifieddate"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        req = urllib.request.Request(
            "https://api.hubapi.com/crm/v3/objects/deals/search",
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            method="POST",
        )
        data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        deals.extend(data.get("results", []))
        after = (data.get("paging") or {}).get("next", {}).get("after")
        if not after or len(deals) >= 400:
            break
    return deals


def _fetch_notes(key: str, deal_id: str) -> list:
    """Notes on a deal as [{"body": str, "attachments": [file_id, ...]}, ...].

    Returns [] on any failure — this loop must never break the sync just because
    one deal's notes are unreachable."""
    bodies = []
    try:
        req = urllib.request.Request(
            f"https://api.hubapi.com/crm/v4/objects/deals/{deal_id}/associations/notes",
            headers={"Authorization": "Bearer " + key},
        )
        assoc = json.loads(urllib.request.urlopen(req, timeout=20).read()).get("results", [])
    except Exception:
        return []
    for a in assoc[:6]:
        nid = a.get("toObjectId")
        if not nid:
            continue
        try:
            nreq = urllib.request.Request(
                f"https://api.hubapi.com/crm/v3/objects/notes/{nid}"
                "?properties=hs_note_body,hs_attachment_ids",
                headers={"Authorization": "Bearer " + key},
            )
            props = json.loads(urllib.request.urlopen(nreq, timeout=20).read()) \
                .get("properties", {}) or {}
            body = props.get("hs_note_body") or ""
            atts = [a.strip() for a in (props.get("hs_attachment_ids") or "").split(";") if a.strip()]
            if body or atts:
                bodies.append({"body": body, "attachments": atts})
        except Exception:
            continue
    return bodies


def _clean_title(dealname: str) -> str:
    t = re.sub(r"^\[[A-Za-z0-9_-]+\]\s*", "", dealname or "")  # strip [PREFIX]
    return t.strip()[:90]


def main() -> int:
    key = _hubspot_key()
    if not key:
        print("no HUBSPOT_API_KEY found — leaving existing feedback file untouched")
        return 1

    deals = _search_deals(key)
    positives, negatives, seen = [], [], set()
    shot_cache, shots_read = _load_shot_cache(), 0

    # PASS 1 — jobs Elena APPLIED TO herself. Strongest signal available, so it
    # fills the positives list first and the weaker stages only top it up.
    applied_checked = 0
    for d in deals:
        if len(positives) >= MAX_EXAMPLES:
            break
        p = d.get("properties", {})
        if p.get("dealstage") != MANUAL_APPLY_STAGE:
            continue
        title = _clean_title(p.get("dealname", ""))
        if not _is_usable_title(title, positive=True) or title.lower() in seen:
            continue
        applied_checked += 1
        if _elena_said_applied(_fetch_notes(key, d.get("id", ""))):
            positives.append(title)
            seen.add(title.lower())
    print(f"manual-apply stage: inspected {applied_checked}, "
          f"confirmed applied-by-Elena {len(positives)}")

    # PASS 2 — the outcome stages, as before.
    for d in deals:  # already newest-first
        p = d.get("properties", {})
        name, stage = p.get("dealname", ""), p.get("dealstage", "")
        title = _clean_title(name)
        # _is_usable_title also covers the old NOISE check (see its definition).
        # Positives are held to the stricter on-lane bar.
        if not _is_usable_title(title, positive=(stage in POSITIVE_STAGES)) or title.lower() in seen:
            continue
        if stage in POSITIVE_STAGES and len(positives) < MAX_EXAMPLES:
            positives.append(title)
            seen.add(title.lower())
        elif stage in NEGATIVE_STAGES and len(negatives) < MAX_EXAMPLES:
            # A rejected TITLE teaches the judge almost nothing; her REASON teaches it
            # the rule. Prefer what she typed; fall back to the screenshot she attached.
            notes = _fetch_notes(key, d.get("id", ""))
            why = _rejection_reason(notes, title)
            # Her text is often a POINTER, not the reason — "Require experienced
            # engineering - look at the image", "Not a fit. Look at requirements".
            # The disqualifying detail lives in the screenshot she attached, so read
            # it whenever one exists and keep BOTH: her verdict plus the evidence.
            shots = [f for n in notes for f in n.get("attachments", [])]
            if shots:
                shot = _read_screenshot(key, shots, shot_cache)
                if shot:
                    shots_read += 1
                    why = f"{why} — from her screenshot: {shot}" if why else shot
            negatives.append(f"{title} — her reason: {why}" if why else title)
            seen.add(title.lower())
        if len(positives) >= MAX_EXAMPLES and len(negatives) >= MAX_EXAMPLES:
            break

    _save_shot_cache(shot_cache)
    with_reason = sum(1 for n in negatives if " — her reason: " in n)

    if not positives and not negatives:
        print(f"scanned {len(deals)} deals — no qualifying outcomes; existing file untouched")
        return 0

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "judge_feedback_sync.py (weekly cron)",
        "positives": positives,
        "negatives": negatives,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT)  # atomic — never leaves a half-written file
    print(f"scanned {len(deals)} deals -> {len(positives)} positives, {len(negatives)} negatives "
          f"({with_reason} carrying her reason, {shots_read} read from screenshots) -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
