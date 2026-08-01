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
        "properties": ["dealname", "dealstage", "createdate"],
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

keep, reject = [], []
for d in deals:
    name = d["properties"]["dealname"]
    m = DEALNAME.match(name)
    title = (m.group(1) if m else name)[:90]
    company = (m.group(2) if m else "")[:40]
    k = re.sub(r"[^a-z0-9]+", " ", f"{company} {title}".lower()).strip()
    cv = index.get(k, {})
    url = cv.get("url", "")
    location = str(cv.get("location", ""))
    desc = cv.get("description", "") or ""
    verdict = None

    # cheapest test first — title alone
    if OFF_LANE.search(title):
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
            verdict = "DEAD (posting closed)"
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
    (reject if verdict else keep).append((d["id"], name, verdict, d["properties"]["createdate"][:10]))

print("=" * 100)
print(f"KEEP {len(keep)}   |   REJECT {len(reject)}")
print("=" * 100)
for _, name, v, created in sorted(reject, key=lambda x: x[2] or ""):
    print(f"  REJECT  {v:<44} {created}  {name[:62]}")
print()
for _, name, _v, created in keep:
    print(f"  KEEP    {'':<44} {created}  {name[:62]}")

if APPLY and reject:
    UNDO.parent.mkdir(exist_ok=True)
    UNDO.write_text(json.dumps(
        [{"id": i, "dealname": n, "previous_stage": "qualifiedtobuy", "reason": v}
         for i, n, v, _ in reject], indent=1))
    for i in range(0, len(reject), 100):
        chunk = reject[i:i + 100]
        api("POST", "https://api.hubapi.com/crm/v3/objects/deals/batch/update",
            {"inputs": [{"id": r[0], "properties": {"dealstage": "closedlost"}} for r in chunk]})
    print(f"\nMOVED {len(reject)} deals to closedlost (No fit)")
    print(f"UNDO FILE: {UNDO}")
elif reject:
    print("\n(dry run — rerun with --apply to move these)")
