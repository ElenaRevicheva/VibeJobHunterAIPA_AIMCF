#!/usr/bin/env python3
"""
Sweep HubSpot "I Act TODAY" (qualifiedtobuy) hiring deals against the CURRENT gate.

Rejects, in order of confidence:
  1. DEAD      — the posting page says the opening is closed
  2. INELIGIBLE— residency roster excludes Panama / not remote-LATAM / US-only
  3. OFF-LANE  — QA-automation, heavy hand-coding, CS-degree demands
  4. UNDERPAID — stated pay below the floor

Never rejects on absence of evidence: a deal whose posting cannot be fetched and
whose title looks fine is KEPT. Writes an undo file with every previous stage.

Usage:  python3 sweep_i_act_today.py            # dry run, prints verdicts
        python3 sweep_i_act_today.py --apply    # also moves rejects to closedlost
        python3 sweep_i_act_today.py --apply --dead-only   # the DAILY cron: closed postings only

28 Sep 2026 (Elena: "we need to regularly automatically clean up stale or closed jobs"):
  · Every move writes Closed Lost Reason = "AUTO-SWEEP <date>: <verdict>". judge_feedback_sync
    keeps AUTO-SWEEP deals OUT of her ledger — a posting that closed is not Elena saying no, and
    without the label it would mute the company (3 in 90 days) and become a "she rejected" example.
  · She wins: a deal she moved BACK to I Act TODAY after a sweep is never swept again.
  · Evidence, not age: a job is DEAD only when the page, the Ashby board API (job no longer
    listed) or the Greenhouse job API (404) says so. Age alone never removes a job.
  · No stored link in the checkpoints → the deal's own apply link (the note VJH wrote).
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/VibeJobHunterAIPA_AIMCF")
from src.core.fit_gate import iron_clad_fit, roster_excludes_home          # noqa: E402
from src.scrapers.job_enricher import enrich_with_state, looks_closed      # noqa: E402
try:
    from src.core.salary_gate import salary_verdict
except Exception:
    salary_verdict = None

APPLY = "--apply" in sys.argv
DEAD_ONLY = "--dead-only" in sys.argv
AUTO_SWEEP = "AUTO-SWEEP"          # judge_feedback_sync._AUTO_SWEEP reads the same prefix
REPO = Path("/home/ubuntu/VibeJobHunterAIPA_AIMCF")
UNDO = REPO / "autonomous_data" / f"sweep_undo_{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.json"


def key():
    for p in (REPO / ".env", Path("/home/ubuntu/cto-aipa/.env")):
        try:
            for line in p.read_text().splitlines():
                if line.startswith("HUBSPOT_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return ""


K = key()
H = {"Authorization": "Bearer " + K, "Content-Type": "application/json"}


def api(method, url, body=None):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body else None, headers=H, method=method
    )
    return json.loads(urllib.request.urlopen(req, timeout=45).read())


# ── 1. every hiring deal sitting in "I Act TODAY" ────────────────────────────
deals, after = [], None
while True:
    body = {
        "filterGroups": [{"filters": [
            {"propertyName": "dealstage", "operator": "EQ", "value": "qualifiedtobuy"},
            {"propertyName": "dealname", "operator": "CONTAINS_TOKEN", "value": "HIRING"},
        ]}],
        "properties": ["dealname", "dealstage", "createdate", "closed_lost_reason"],
        "limit": 100,
    }
    if after:
        body["after"] = after
    page = api("POST", "https://api.hubapi.com/crm/v3/objects/deals/search", body)
    deals.extend(page.get("results", []))
    after = (page.get("paging") or {}).get("next", {}).get("after")
    if not after:
        break
print(f"I Act TODAY holds {len(deals)} hiring deals\n")

# ── 2. checkpoint index: company+title -> stored url/location/description ────
index = {}
try:
    import sqlite3
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    ser = JsonPlusSerializer()
    con = sqlite3.connect(str(REPO / "autonomous_data" / "vjh_checkpoint.db"))
    for blob, typ in con.execute("SELECT checkpoint, type FROM checkpoints"):
        try:
            cv = ser.loads_typed((typ or "msgpack", blob)).get("channel_values", {})
        except Exception:
            continue
        co, ti = str(cv.get("company", "")), str(cv.get("title", ""))
        if not co or not ti:
            continue
        k = re.sub(r"[^a-z0-9]+", " ", f"{co} {ti}".lower()).strip()
        if cv.get("url") and (k not in index or cv.get("description")):
            index[k] = cv
except Exception as e:
    print(f"(checkpoint index unavailable: {e})")
print(f"checkpoint index: {len(index)} jobs\n")

DEALNAME = re.compile(r"^\[[^\]]+\]\s*(.*?)\s*@\s*([^@]+)$")
# Elena's three lanes (encoded 2026-07-09): AI-augmented product/agent builder,
# GEO/AEO/tech-SEO, AI-automation solutions architect. Explicitly NOT ML
# engineering and NOT research — "AI Engineer" IS a fit, "Machine Learning
# Engineer" is not, and the two are one word apart, so match precisely.
OFF_LANE = re.compile(
    r"qa automation|automation qa|test automation|sdet|quality assurance|"
    r"it automation|infrastructure automation|network automation|industrial automation|"
    r"rpa developer|marketing automation|sales automation|"
    r"full[- ]?stack|backend engineer|back-end (developer|engineer)|"
    r"front[- ]?end engineer|senior software engineer|"
    r"staff engineer|staff software|principal engineer|principal machine|"
    r"machine learning (engineer|scientist|researcher|trainer)|"
    r"\bml (engineer|scientist|researcher)\b|"
    r"research (engineer|scientist)|researcher|"
    r"software development engineer|\bsde\b|"
    r"python developer|java developer|"
    r"account executive|sales representative|recruiter|customer success|"
    r"accounting manager|revenue cycle|data entry", re.I)

def note_url(deal_id):
    """The apply link VJH wrote on the deal — the same one the morning page uses. Never a
    🔎 COMPANY BRIEF note (it carries no link by design) or a kit note."""
    try:
        assoc = api("GET", f"https://api.hubapi.com/crm/v4/objects/deals/{deal_id}/associations/notes")
        ids = [{"id": str(a["toObjectId"])} for a in assoc.get("results", [])]
        if not ids:
            return ""
        notes = api("POST", "https://api.hubapi.com/crm/v3/objects/notes/batch/read",
                    {"properties": ["hs_note_body", "hs_timestamp"], "inputs": ids}).get("results", [])
        for n in sorted(notes, key=lambda n: n["properties"].get("hs_timestamp") or ""):
            body = n["properties"].get("hs_note_body") or ""
            if "COMPANY BRIEF" in body or "TECHNICAL DEFENSE" in body:
                continue
            m = re.search(r"https?://[^\s<>\"')]+", re.sub(r"<[^>]+>", " ", body))
            if m:
                return m.group(0).replace("&amp;", "&")
    except Exception:
        pass
    return ""


def public_get(url):
    """GET a PUBLIC job-board API. Never api(): that helper attaches the HubSpot key, and on 28 Sep
    the first version of board_says_closed() sent it to Ashby and Greenhouse that way."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (VibeJobHunter sweep)",
                                               "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def board_says_closed(url):
    """Ashby and Greenhouse render job pages in the browser, so the page text proves nothing
    server-side. Their PUBLIC job APIs do: verified 28 Sep on jobs checked by hand in Chrome
    (Addi listed = open, Scale Army absent = "Job not found"; Greenhouse open = 200, gone = 404).
    Returns the evidence string, or "" (unknown / open — never closed on absence of evidence)."""
    try:
        m = re.match(r"https?://jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", url, re.I)
        if m:
            board = public_get(f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}")
            ids = {j.get("id") for j in board.get("jobs", [])}
            if ids and m.group(2) not in ids:
                return "Ashby board no longer lists this job"
            return ""
        m = re.match(r"https?://(?:job-)?boards\.greenhouse\.io/([^/?#]+)/jobs/(\d+)", url, re.I)
        if m:
            try:
                public_get(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return "Greenhouse job API returns 404"
    except Exception:
        pass
    return ""


keep, reject, gate_only = [], [], []
for d in deals:
    name = d["properties"]["dealname"]
    m = DEALNAME.match(name)
    title = (m.group(1) if m else name)[:90]
    company = (m.group(2) if m else "")[:40]
    # She wins: swept once and moved back by her → it is hers now, never swept again.
    if str(d["properties"].get("closed_lost_reason") or "").startswith(AUTO_SWEEP):
        keep.append((d["id"], name, None, d["properties"]["createdate"][:10]))
        print(f"  kept (Elena restored it after a sweep): {name[:70]}")
        continue
    k = re.sub(r"[^a-z0-9]+", " ", f"{company} {title}".lower()).strip()
    cv = index.get(k, {})
    url = cv.get("url", "") or note_url(d["id"])
    location = str(cv.get("location", ""))
    desc = cv.get("description", "") or ""
    verdict = None

    board_closed = board_says_closed(url) if url else ""
    # cheapest test first — title alone
    if board_closed:
        verdict = f"DEAD (posting closed: {board_closed})"
    elif OFF_LANE.search(title):
        verdict = "OFF-LANE (title)"
    # residency roster from the stored location
    elif location and roster_excludes_home(location):
        verdict = "INELIGIBLE (roster excludes Panama)"
    elif url:
        try:
            text, closed = enrich_with_state(url, desc)
        except Exception:
            text, closed = desc, False
        if closed:
            verdict = "DEAD (posting closed: the page says so)"
        elif len(text) > 400:
            if not iron_clad_fit(title, location, text):
                verdict = "INELIGIBLE (fails iron-clad on real posting text)"
            elif salary_verdict:
                try:
                    v, amt, _ = salary_verdict(title, text)
                    if v == "below_floor":
                        verdict = f"UNDERPAID (~${amt:,.0f}/mo)"
                except Exception:
                    pass
    if "--verbose" in sys.argv:
        print(f"  · {name[:50]:<50} url={url[:90] or '(none)'} → {verdict or 'keep'}")
    row = (d["id"], name, verdict, d["properties"]["createdate"][:10])
    if verdict and DEAD_ONLY and not verdict.startswith("DEAD"):
        gate_only.append(row)       # the daily run removes closed postings only; the gate is hers to apply
        keep.append(row)
    else:
        (reject if verdict else keep).append(row)

print("=" * 100)
print(f"KEEP {len(keep)}   |   REJECT {len(reject)}" + ("   (--dead-only)" if DEAD_ONLY else ""))
print("=" * 100)
for _, name, v, created in sorted(reject, key=lambda x: x[2] or ""):
    print(f"  REJECT  {v:<44} {created}  {name[:62]}")
print()
for _, name, v, created in keep:
    print(f"  KEEP    {('(gate says ' + v + ')') if v else '':<44} {created}  {name[:62]}")

if APPLY and reject:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    UNDO.parent.mkdir(exist_ok=True)
    UNDO.write_text(json.dumps(
        [{"id": i, "dealname": n, "previous_stage": "qualifiedtobuy", "previous_closed_lost_reason": "",
          "reason": v} for i, n, v, _ in reject], indent=1))
    for i in range(0, len(reject), 100):
        chunk = reject[i:i + 100]
        api("POST", "https://api.hubapi.com/crm/v3/objects/deals/batch/update",
            {"inputs": [{"id": r[0], "properties": {
                "dealstage": "closedlost",
                "closed_lost_reason": f"{AUTO_SWEEP} {today}: {r[2]} — not Elena's decision; move it back to "
                                      f"I Act TODAY and the sweep never touches it again"}} for r in chunk]})
    print(f"\nMOVED {len(reject)} deals to closedlost with Closed Lost Reason = {AUTO_SWEEP} …")
    print(f"UNDO FILE: {UNDO}")
elif reject:
    print("\n(dry run — rerun with --apply to move these)")
else:
    print("\nnothing to sweep")
