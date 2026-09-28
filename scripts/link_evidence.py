#!/usr/bin/env python3
"""
link_evidence.py — give every one of Elena's decisions the posting it was made on.

    python scripts/link_evidence.py            → link, then print coverage
    python scripts/link_evidence.py --report   → coverage only, writes nothing

WHY (28 Sep 2026). The judge replay (scripts/replay_learning.py) re-judged her past decisions on an
EMPTY listing: the ledger kept her words, not the posting, and job_listings — built for exactly this
in Dec 2025 — had 0 rows. Three OpenAI models then "approved" 1-3 of her 20 applications, which
measured the empty input, not the judge.

The posting was never lost. LangGraph checkpoints every pipeline run (autonomous_data/
vjh_checkpoint.db: title, company, location, url, description per job). This reads them READ-ONLY
and copies the ones her decisions point at into job_listings via record_judged_posting(). The
Bright Data door records its own postings at decision time (serpapi_jobs_ingest.py).

Join key: the "Job URL:" cto-aipa writes into every hiring deal → ledger["url"] → checkpoint url.
The text stored is the RAW text the pipeline handed the judge, so the replay sees what it saw.
"""
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

LEDGER = REPO / "autonomous_data" / "judge_decisions.json"
CHECKPOINTS = REPO / "autonomous_data" / "vjh_checkpoint.db"
_CHANNELS = ("title", "company", "location", "description", "url")


def _checkpoint_postings(urls: set, db_path: Path = CHECKPOINTS) -> dict:
    """{url: {title, company, location, description, thread}} for the wanted urls. Read-only."""
    if not urls or not db_path.exists():
        return {}
    from langgraph.checkpoint.sqlite import SqliteSaver
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        serde = SqliteSaver(con).serde
        thread_of = {}
        for tid, typ, val in con.execute("SELECT thread_id, type, value FROM writes WHERE channel='url'"):
            try:
                u = serde.loads_typed((typ, val))
            except Exception:
                continue
            if u in urls:
                thread_of[u] = tid
        out = {}
        marks = ",".join("?" * len(_CHANNELS))
        for u, tid in thread_of.items():
            vals = {}
            for ch, typ, val in con.execute(
                    f"SELECT channel, type, value FROM writes WHERE thread_id=? AND channel IN ({marks}) "
                    f"ORDER BY rowid", (tid, *_CHANNELS)):
                try:
                    vals[ch] = serde.loads_typed((typ, val))    # later writes win, as in the state
                except Exception:
                    pass
            if vals.get("title") and vals.get("company"):
                out[u] = {**vals, "thread": tid}
        return out
    finally:
        con.close()


def link_evidence(ledger: dict, write: bool = True, db_url: str = None,
                  checkpoints: Path = CHECKPOINTS) -> dict:
    """Link ledger decisions to their postings. Returns coverage counts; never raises."""
    from src.database.database_models import find_posting, record_judged_posting
    stats = {"decisions": len(ledger), "with_url": 0, "had_evidence": 0, "linked_now": 0, "no_evidence": 0}
    missing = set()
    for e in ledger.values():
        url = e.get("url")
        if not url:
            continue
        stats["with_url"] += 1
        if find_posting(url=url, db_url=db_url):
            stats["had_evidence"] += 1
        else:
            missing.add(url)
    try:
        found = _checkpoint_postings(missing, checkpoints) if missing else {}
    except Exception as ex:
        print(f"  checkpoints unreadable ({str(ex)[:80]}) — nothing linked")
        found = {}
    for url, p in found.items():
        if write and record_judged_posting(p["title"], p["company"], url, p.get("location", ""),
                                           p.get("description", ""), f"langgraph:{p['thread']}"[:80],
                                           db_url=db_url):
            stats["linked_now"] += 1
    stats["no_evidence"] = stats["with_url"] - stats["had_evidence"] - stats["linked_now"]
    return stats


def main() -> None:
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["deals"]
    except Exception as e:
        print(f"no ledger ({e}) — run scripts/judge_feedback_sync.py first")
        return
    s = link_evidence(ledger, write="--report" not in sys.argv)
    print(f"evidence: {s['decisions']} decisions · {s['with_url']} carry a job URL · "
          f"{s['had_evidence']} already had the posting · {s['linked_now']} linked now · "
          f"{s['no_evidence']} with no posting on record")


if __name__ == "__main__":
    main()
