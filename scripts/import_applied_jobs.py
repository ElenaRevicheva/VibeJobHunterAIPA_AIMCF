#!/usr/bin/env python3
"""
Teach VJH what Elena has already applied to elsewhere (added 2026-08-05).

THE PROBLEM
VJH's dedup only knows what VJH itself surfaced. Applications Elena sent directly
on Get on Board, LinkedIn or a company site are invisible to it. So on 2026-08-04
the new Get on Board source presented three jobs as fresh finds that she had
already applied to months earlier:

    Rozeta Labs      Applied AI Engineer — Agentic Systems     applied Jun 1  (seen)
    CG Real Estate   AI Automation Architect & Ops Director    applied May 31 (seen)
    Coderslab.io     Líder de GenAI / AI Product Owner         applied May 3  (seen)

Re-surfacing an application she already sent is worse than surfacing nothing: it
burns her attention AND makes the queue untrustworthy.

WHAT THIS DOES
1. Marks each entry in scripts/applied_jobs.tsv in the SAME fingerprint store the
   runner already consults (normalised company+title), so the pipeline treats them
   exactly as it treats anything it surfaced itself — no new dedup mechanism.
2. Optionally moves any matching HubSpot deal out of "🔥 I Act TODAY" into
   "⏳ Sent — passive wait", where an already-sent application belongs.

Fingerprints written here get a far-future TTL: an application she has already
sent should never come back, whatever the normal 60-day window says.

Usage:  venv/bin/python scripts/import_applied_jobs.py            # dry run
        venv/bin/python scripts/import_applied_jobs.py --apply
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.langgraph_pipeline.runner import VJHLangGraphRunner  # noqa: E402

APPLY = "--apply" in sys.argv
TSV = Path(__file__).with_name("applied_jobs.tsv")
SENT_STAGE = "decisionmakerboughtin"   # ⏳ Sent — passive wait
ACT_TODAY = "qualifiedtobuy"           # 🔥 I Act TODAY


def hubspot_key() -> str:
    for p in (REPO / ".env", Path("/home/ubuntu/cto-aipa/.env")):
        try:
            for line in p.read_text().splitlines():
                if line.startswith("HUBSPOT_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return ""


def api(method, url, body=None):
    key = hubspot_key()
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method=method,
    )
    return json.loads(urllib.request.urlopen(req, timeout=45).read())


def load_entries():
    out = []
    for raw in TSV.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) < 2:
            print(f"  ! skipped (needs company<TAB>title): {line[:60]}")
            continue
        out.append((parts[0], parts[1]))
    return out


def main() -> int:
    runner = VJHLangGraphRunner()
    entries = load_entries()
    print(f"{len(entries)} applications in {TSV.name}\n")

    db = runner._load_fingerprints()
    before = len(db)
    # Far future: an application already sent should never resurface.
    forever = (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat()

    new, already = 0, 0
    for company, title in entries:
        fp = runner._fingerprint(company, title)
        if fp in db:
            already += 1
        else:
            new += 1
        if APPLY:
            rec = db.get(fp) or {"first_surfaced": forever, "company": company,
                                 "title": title, "job_ids": []}
            rec.update({"last_surfaced": forever, "company": company, "title": title,
                        "source": "already_applied_elsewhere",
                        "count": int(rec.get("count", 0)) + 1})
            db[fp] = rec
    if APPLY:
        runner._save_fingerprints(db)
        print(f"fingerprints: {before} -> {len(db)}  ({new} new, {already} already known)\n")
    else:
        print(f"would add {new} fingerprints ({already} already known)\n")

    # ── HubSpot: an already-sent application does not belong in "I Act TODAY" ──
    try:
        res = api("POST", "https://api.hubapi.com/crm/v3/objects/deals/search", {
            "filterGroups": [{"filters": [
                {"propertyName": "dealstage", "operator": "EQ", "value": ACT_TODAY},
                {"propertyName": "dealname", "operator": "CONTAINS_TOKEN", "value": "HIRING"},
            ]}],
            "properties": ["dealname"], "limit": 100,
        })
    except Exception as e:
        print(f"HubSpot unavailable ({e}) — fingerprints still written")
        return 0

    want = {runner._fingerprint(c, t): (c, t) for c, t in entries}
    hits = []
    for d in res.get("results", []):
        name = d["properties"]["dealname"]
        body = name.split("] ", 1)[-1]
        if " @ " in body:
            title, company = body.rsplit(" @ ", 1)
            if runner._fingerprint(company, title) in want:
                hits.append((d["id"], name))

    print(f'in "I Act TODAY" but already applied to: {len(hits)}')
    for _, name in hits:
        print(f"   -> {name[:74]}")
    if hits and APPLY:
        api("POST", "https://api.hubapi.com/crm/v3/objects/deals/batch/update",
            {"inputs": [{"id": i, "properties": {"dealstage": SENT_STAGE}} for i, _ in hits]})
        print(f'\nmoved {len(hits)} to "Sent — passive wait" | undo ids: '
              + ",".join(i for i, _ in hits))
    elif not APPLY:
        print("\n(dry run — rerun with --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
