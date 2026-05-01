"""
backfill_milestones.py
Run ONCE on any machine to inject the 5 missed CTO milestones into CMO AIPA.

Usage:
    python backfill_milestones.py --url http://<oracle-vm-ip>:8080
    python backfill_milestones.py --url http://127.0.0.1:8080   # from Oracle VM itself

Each POST hits /api/tech-update — same endpoint CTO AIPA now calls automatically.
After this runs, CMO AIPA will pick them up on the next LinkedIn/X posting cycle.
"""

import json, sys, time, argparse
from urllib.request import urlopen, Request
from urllib.error import URLError

MILESTONES = [
    {
        "repo": "EspaLuz",
        "title": "pgvector RAG 2-layer memory in EspaLuz",
        "description": (
            "Implemented a 2-layer retrieval-augmented generation memory system using pgvector "
            "on Oracle Autonomous Database. Layer 1 does semantic search over lesson history; "
            "Layer 2 applies a re-ranking pass with context window. Enables truly personalised "
            "Spanish tutoring that remembers every student's weak spots across sessions."
        ),
        "type": "feature",
        "security_issues": 0,
        "complexity_issues": 0,
    },
    {
        "repo": "VibeJobHunterAIPA_AIMCF",
        "title": "LangGraph 7-node pipeline in VibeJobHunter",
        "description": (
            "Rebuilt the job-matching core as a LangGraph 7-node stateful pipeline: "
            "scrape → parse → score → filter → personalise → apply → track. "
            "Each node is independently testable. Added conditional edges so low-score "
            "jobs exit early, cutting Claude API cost by ~40%."
        ),
        "type": "architecture",
        "security_issues": 0,
        "complexity_issues": 2,
    },
    {
        "repo": "cto-aipa",
        "title": "AWS Lambda Sprint Briefing Agent (Sprinter)",
        "description": (
            "Shipped the Sprint Briefing Agent as a serverless AWS Lambda function triggered "
            "by EventBridge Scheduler. Fetches real GitHub commits (26h window), voice notes "
            "from Oracle, clusters signals with Groq Llama 3.3 70B, writes a spoken narrative "
            "with Claude Sonnet, and delivers via Telegram TTS. Deduplication guard ensures "
            "exactly one briefing per day. Total infra cost ~$3/month."
        ),
        "type": "feature",
        "security_issues": 0,
        "complexity_issues": 1,
    },
    {
        "repo": "VibeJobHunterAIPA_AIMCF",
        "title": "131-test 4-layer eval harness",
        "description": (
            "Built a 4-layer evaluation harness with 131 automated tests: "
            "L1 unit (schema, parsing), L2 integration (pipeline flow), "
            "L3 LLM-judge (Claude grades output quality), L4 regression (golden-set comparisons). "
            "CI runs all 4 layers on every push. Caught 3 silent regressions in the first week."
        ),
        "type": "testing",
        "security_issues": 0,
        "complexity_issues": 1,
    },
    {
        "repo": "cto-aipa",
        "title": "Sprint Briefing dedup + real commit signal",
        "description": (
            "Fixed Sprinter to fetch actual GitHub commits via listCommits API (not just PRs/issues), "
            "giving a true daily-activity signal. Added Oracle-backed deduplication so the briefing "
            "fires exactly once per Panama day regardless of Lambda retries. Narrative prompt hardened "
            "with HARD RULES: voice notes first, commits named specifically, zero invention, zero padding."
        ),
        "type": "fix",
        "security_issues": 0,
        "complexity_issues": 0,
    },
]


def post_milestone(base_url: str, milestone: dict) -> bool:
    url = f"{base_url.rstrip('/')}/api/tech-update"
    body = json.dumps(milestone).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"  ✅ {milestone['title'][:60]}  → pending_linkedin={result.get('pending_linkedin')}, pending_x={result.get('pending_x')}")
            return True
    except URLError as e:
        print(f"  ❌ FAILED {milestone['title'][:60]}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Backfill missed CTO milestones into CMO AIPA")
    parser.add_argument("--url", default="http://127.0.0.1:8080",
                        help="Base URL of CMO AIPA (default: http://127.0.0.1:8080)")
    args = parser.parse_args()

    print(f"\n🚀 Backfilling {len(MILESTONES)} milestones → {args.url}\n")
    ok = 0
    for i, m in enumerate(MILESTONES):
        print(f"[{i+1}/{len(MILESTONES)}] Posting: {m['title']}")
        if post_milestone(args.url, m):
            ok += 1
        if i < len(MILESTONES) - 1:
            time.sleep(0.5)

    print(f"\n{'✅' if ok == len(MILESTONES) else '⚠️'} Done: {ok}/{len(MILESTONES)} milestones queued.")
    print("CMO AIPA will pick these up on the next posting cycle.")
    if ok < len(MILESTONES):
        sys.exit(1)


if __name__ == "__main__":
    main()
