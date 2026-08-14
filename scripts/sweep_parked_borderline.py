"""
sweep_parked_borderline.py — find opportunities already buried in the "ignore" stage.

Companion to the live borderline alert in src/search/serpapi_jobs_ingest.py. That
one catches disagreements from now on; this one goes back over what is ALREADY
parked and asks the same question of each: would the LLM judge take this job that
the iron-clad gate rejected?

Why this exists (Aug 14 2026 — Scale Army):
    VJH found Scale Army on Aug 5. `iron_clad_fit` vetoed on the board's country
    roster (Egypt, Argentina, Ethiopia, South Africa, Nigeria — no Panama) and the
    job was parked in "🤖 AI working — ignore". Nine days later their recruiter
    emailed Elena directly, inviting her to apply to the senior version of the same
    role. Both Scale Army roles are gate-NO / judge-YES. Without that email the
    opportunity would have vanished.

What the numbers said before this was built (40-deal sample, re-fetched live):
    0 of 26 passed BOTH gates      → parking is broadly CORRECT; do not mass-rescue
    1 of 26 was gate-NO/judge-YES  → ~4%, i.e. ~20 across the parked pile

So this is a scalpel, not a rescue. It prints the disagreements and leaves every
deal exactly where it is.

READ-ONLY. It never writes to HubSpot — no stage moves, no notes, no deletions.
The parked deals carry only a title and a Job URL (no description), so each posting
is re-fetched from its board's public API to get text worth judging.

Boards handled: Ashby, Greenhouse, Lever, Torre. Wellfound is the largest slice of
the pile but has no public posting API — those are counted and skipped, honestly,
rather than judged on a title alone.

Usage:
    venv/bin/python scripts/sweep_parked_borderline.py [--limit N] [--json OUT]

Needs the venv (imports src.core.*), unlike judge_feedback_sync.py which is stdlib-only.
"""

import argparse
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import judge_feedback_sync as J          # noqa: E402  — reuse its HubSpot key lookup
from src.core.fit_gate import iron_clad_fit   # noqa: E402
from src.core.llm_judge import judge_fit      # noqa: E402

PARKED_STAGE = "appointmentscheduled"    # "🤖 AI working — ignore"
PORTAL = "51409153"
UA = {"User-Agent": "Mozilla/5.0"}
_board_cache: dict = {}


def _get(url: str):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=30).read())


def _from_ashby(url: str):
    m = re.match(r"https://jobs\.ashbyhq\.com/([^/]+)/([0-9a-f-]+)", url)
    if not m:
        return None
    board, jid = m.group(1), m.group(2)
    if board not in _board_cache:
        try:
            _board_cache[board] = _get(
                f"https://api.ashbyhq.com/posting-api/job-board/{board}").get("jobs", [])
        except Exception:
            _board_cache[board] = []
    for j in _board_cache[board]:
        if j.get("id") == jid:
            locs = [j.get("location")] + [s.get("location") for s in j.get("secondaryLocations", [])]
            return j.get("title", ""), ", ".join(x for x in locs if x), j.get("descriptionPlain") or ""
    return None


def _from_greenhouse(url: str):
    m = re.match(r"https://(?:job-boards(?:\.eu)?|boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if not m:
        return None
    try:
        j = _get(f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}?content=true")
    except Exception:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", j.get("content") or ""))
    return j.get("title", ""), (j.get("location") or {}).get("name", ""), text


def _from_lever(url: str):
    m = re.match(r"https://jobs(?:\.eu)?\.lever\.co/([^/]+)/([0-9a-f-]+)", url)
    if not m:
        return None
    try:
        j = _get(f"https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}")
    except Exception:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", " ", j.get("descriptionPlain") or j.get("description") or ""))
    return j.get("text", ""), (j.get("categories") or {}).get("location", ""), text


def _from_torre(url: str):
    m = re.search(r"torre\.ai/jobs/([A-Za-z0-9]+)", url)
    if not m:
        return None
    try:
        j = _get(f"https://torre.ai/api/opportunities/{m.group(1)}")
    except Exception:
        return None
    locs = ", ".join(j.get("locations") or [])
    text = " ".join(d.get("content", "") for d in (j.get("details") or []) if isinstance(d, dict))
    return (j.get("objective") or ""), locs, text


FETCHERS = (_from_ashby, _from_greenhouse, _from_lever, _from_torre)


def _fetch(url: str):
    for f in FETCHERS:
        try:
            got = f(url)
        except Exception:
            got = None
        if got:
            return got
    return None


def _parked_deals(key: str) -> list:
    out, after = [], None
    while True:
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "dealname", "operator": "CONTAINS_TOKEN", "value": "HIRING"},
                {"propertyName": "dealstage", "operator": "EQ", "value": PARKED_STAGE},
            ]}],
            "properties": ["dealname", "description", "createdate"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        req = urllib.request.Request(
            "https://api.hubapi.com/crm/v3/objects/deals/search",
            data=json.dumps(body).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            method="POST")
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())
        out.extend(data.get("results", []))
        after = (data.get("paging") or {}).get("next", {}).get("after")
        if not after:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="stop after N re-fetched postings")
    ap.add_argument("--json", help="write findings to this file as JSON")
    args = ap.parse_args()

    key = J._hubspot_key()
    if not key:
        print("no HUBSPOT_API_KEY found")
        return 1

    deals = _parked_deals(key)
    print(f"parked in '{PARKED_STAGE}' (AI working — ignore): {len(deals)}")

    findings, fetched, no_url, unfetchable, dead = [], 0, 0, 0, 0
    for d in deals:
        if args.limit and fetched >= args.limit:
            break
        p = d.get("properties", {})
        m = re.search(r"Job URL:\s*(\S+)", p.get("description") or "")
        if not m:
            no_url += 1
            continue
        got = _fetch(m.group(1))
        if not got:
            unfetchable += 1          # no public API (mostly Wellfound), or 404
            continue
        title, loc, desc = got
        if len(desc) < 250:
            dead += 1                 # posting pulled or paywalled — nothing to judge
            continue
        fetched += 1
        if iron_clad_fit(title, loc, desc):
            continue                  # gate agrees it is a fit — not a disagreement
        ok, why = judge_fit(title, "", loc, desc[:1500])
        if not ok or str(why).startswith("JUDGE UNAVAILABLE"):
            continue
        findings.append({
            "deal": f"https://app.hubspot.com/contacts/{PORTAL}/deal/{d['id']}",
            "title": title, "location": loc, "url": m.group(1),
            "judge": why, "created": (p.get("createdate") or "")[:10],
        })

    print(f"re-fetched {fetched} | no URL {no_url} | no public API {unfetchable} | posting gone {dead}")
    print(f"\nBORDERLINE — gate says NO, judge says YES: {len(findings)}")
    for f in findings:
        print(f"\n  {f['title'][:72]}   ({f['created']})")
        print(f"    location : {f['location'][:70]}")
        print(f"    judge    : {f['judge'][:120]}")
        print(f"    deal     : {f['deal']}")
        print(f"    apply    : {f['url']}")

    if args.json:
        Path(args.json).write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwritten -> {args.json}")
    print("\n(read-only — nothing in HubSpot was changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
