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

Runs weekly via cron on Oracle (ubuntu crontab). Stdlib-only — no venv dependencies.

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
    r"|---\s*cover\s*/\s*outreach letter.*",
    re.IGNORECASE | re.DOTALL,
)
_APPLIED_MARK = re.compile(r"\bapplied\b", re.IGNORECASE)


def _elena_said_applied(note_bodies) -> bool:
    """True only if SHE wrote an 'applied' marker, after removing VJH's template."""
    for body in note_bodies:
        human = _BOT_NOTE_TEMPLATE.sub(" ", re.sub(r"<[^>]+>", " ", body or ""))
        if _APPLIED_MARK.search(human):
            return True
    return False
MAX_EXAMPLES = 6
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
ROLE_NOUN = re.compile(
    r"\b(engineer|developer|architect|specialist|scientist|analyst|designer|"
    r"manager|lead|head|director|consultant|builder|strategist|marketer|"
    r"operations|ops|automation|技術|programmer|administrator|coordinator|"
    r"technician|advisor|officer|founder|cto|pm|product owner)\b",
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
    """Note bodies attached to a deal. Returns [] on any failure — this loop must
    never break the weekly sync just because one deal's notes are unreachable."""
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
                f"https://api.hubapi.com/crm/v3/objects/notes/{nid}?properties=hs_note_body",
                headers={"Authorization": "Bearer " + key},
            )
            body = json.loads(urllib.request.urlopen(nreq, timeout=20).read()) \
                .get("properties", {}).get("hs_note_body") or ""
            if body:
                bodies.append(body)
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
            negatives.append(title)
            seen.add(title.lower())
        if len(positives) >= MAX_EXAMPLES and len(negatives) >= MAX_EXAMPLES:
            break

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
    print(f"scanned {len(deals)} deals -> {len(positives)} positives, {len(negatives)} negatives -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
