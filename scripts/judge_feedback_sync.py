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
MAX_EXAMPLES = 6
NOISE = re.compile(r"smoke|delete me|\btest\b", re.IGNORECASE)


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
    for d in deals:  # already newest-first
        p = d.get("properties", {})
        name, stage = p.get("dealname", ""), p.get("dealstage", "")
        title = _clean_title(name)
        if not title or NOISE.search(title) or title.lower() in seen:
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
