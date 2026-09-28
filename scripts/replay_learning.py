"""
replay_learning.py — does VJH actually learn from Elena? Proof by replay, not by assertion.

    python scripts/replay_learning.py                 # learned rules over EVERY decision ($0)
    python scripts/replay_learning.py --judge 25      # + judge before/after on a sample (~$0.02)

Reads autonomous_data/judge_decisions.json (her decisions, written by judge_feedback_sync.py)
and autonomous_data/learned_rules.json. Writes nothing.

1. RULES — every rejection and every application replayed through learned_veto(). Evidence per
   job is only what a posting would show: title, company and the text her screenshot was read
   as. Her own words are never used as posting text. Reported: rejections caught, and jobs she
   APPLIED to that would be wrongly blocked (must be 0).
2. JUDGE (--judge N) — N recent rejections WITH a reason and N applications, judged twice: with
   the pre-27-Sep prompt block (12 recent examples, "do NOT override criteria 1-7") and with the
   new one (lessons from ALL rejections, allowed to reject). The 12 examples quoted in the
   prompt are excluded from the sample so the test does not mark its own homework.

EVIDENCE (28 Sep 2026). Until now every application was judged on an EMPTY listing — the ledger
kept her words, not the posting — so "applications approved 1-4/20" measured the empty input, not
the judge. Each decision is now judged on the posting it was made on (job_listings, linked by
scripts/link_evidence.py from the deal's Job URL), plus her screenshot reading. The judge sample
takes ONLY decisions with a posting on record and says how many it skipped; --since limits it to
decisions made under the current targeting (e.g. --since 2026-09-20).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.core.learned_rules import learned_veto, load_rules  # noqa: E402

try:
    from src.database.database_models import find_posting  # noqa: E402
except Exception:                                            # no DB layer → screenshot text only
    def find_posting(**_k):
        return None

LEDGER = REPO / "autonomous_data" / "judge_decisions.json"
FEEDBACK = REPO / "autonomous_data" / "judge_feedback.json"
POSITIVE_STAGES = {"presentationscheduled", "contractsent", "closedwon"}


_POSTINGS: dict = {}


def _posting(e: dict):
    """The posting this decision was made on (job_listings), or None."""
    key = e.get("url") or e["title"]
    if key not in _POSTINGS:
        title, _, company = e["title"].rpartition(" @ ")
        _POSTINGS[key] = find_posting(url=e.get("url"), title=title or e["title"], company=company)
    return _POSTINGS[key]


def _evidence(e: dict) -> str:
    """What the POSTING said — the posting on record plus her screenshot reading, never her words."""
    shot = (e.get("why") or "").partition("her screenshot shows:")[2].strip()
    p = _posting(e)
    return "\n".join(x for x in ((p or {}).get("description", ""), shot) if x)


def _location(e: dict) -> str:
    return ((_posting(e) or {}).get("location") or "")


def _is_applied(e: dict) -> bool:
    return bool(e.get("applied")) or e["stage"] in ("presentationscheduled", "closedwon")


def replay_rules(ledger: dict, rules: dict) -> None:
    negs = [e for e in ledger.values() if e["stage"] == "closedlost"]
    pos = [e for e in ledger.values() if _is_applied(e)]
    caught, by_rule, wrong = 0, {}, []
    for e in negs:
        v, why = learned_veto(e["title"].rsplit(" @ ", 1)[0], e.get("company", ""), _evidence(e), rules=rules)
        if v:
            caught += 1
            code = why.split(":")[0].replace("LEARNED ", "")
            by_rule[code] = by_rule.get(code, 0) + 1
    for e in pos:
        v, why = learned_veto(e["title"].rsplit(" @ ", 1)[0], e.get("company", ""), _evidence(e), rules=rules)
        if v:
            wrong.append(f"{e['title'][:60]} — {why[:90]}")
    print(f"RULES   rejections caught {caught}/{len(negs)} · by rule {by_rule}")
    print(f"RULES   applications wrongly blocked {len(wrong)}/{len(pos)}")
    for w in wrong:
        print(f"        ✖ {w}")


def replay_judge(ledger: dict, n: int, since: str = "", show: bool = False) -> None:
    from src.core import llm_judge
    data = json.loads(FEEDBACK.read_text(encoding="utf-8"))
    quoted = {t.split(" — ")[0].lower() for t in data.get("negatives", []) + data.get("positives", [])}

    def old_block() -> str:
        pos, neg = data.get("positives", [])[:12], data.get("negatives", [])[:12]
        lines = ["REAL RECENT OUTCOMES from Elena's own pipeline (taste calibration refreshed daily —",
                 "these refine your judgment but do NOT override criteria 1-7 above):"]
        if pos:
            lines += ["She APPLIED to these (fit):"] + ["  - " + t for t in pos]
        if neg:
            lines += ["She REJECTED these (not fit) — pay attention to WHY:"] + ["  - " + t for t in neg]
        return "\n".join(lines) + "\n\n"

    new_block = llm_judge._feedback_block
    rows = sorted(ledger.values(), key=lambda e: e.get("modified", ""), reverse=True)
    if since:
        rows = [e for e in rows if (e.get("first_decided") or e.get("modified") or "")[:10] >= since]
    all_negs = [e for e in rows if e["stage"] == "closedlost" and e.get("why") and e["title"].lower() not in quoted]
    all_poss = [e for e in rows if _is_applied(e) and e["title"].lower() not in quoted]
    # Only decisions whose posting is on record: judging an empty listing measures nothing.
    negs = [e for e in all_negs if _posting(e)][:n]
    poss = [e for e in all_poss if _posting(e)][:n]
    print(f"JUDGE sample{' since ' + since if since else ''}: rejections {len(negs)} "
          f"(of {len(all_negs)}; {sum(1 for e in all_negs if not _posting(e))} have no posting on record) · "
          f"applications {len(poss)} (of {len(all_poss)}; "
          f"{sum(1 for e in all_poss if not _posting(e))} have no posting on record)")
    if not negs or not poss:
        print("JUDGE not measured — too few decisions with a posting on record")
        return

    def verdicts(block, sample):
        llm_judge._feedback_block = block
        out = []
        for e in sample:
            title, _, company = e["title"].rpartition(" @ ")
            # url= makes the RAG mode leave-one-out: a job never retrieves its own decision.
            fit, why = llm_judge.judge_fit(title or e["title"], company, _location(e), _evidence(e),
                                           url=e.get("url"))
            out.append((fit, why))
        return out

    try:
        for name, block in (("before", old_block), ("after", new_block)):
            vn, vp = verdicts(block, negs), verdicts(block, poss)
            unav = sum(1 for _, w in vn + vp if str(w).startswith("JUDGE UNAVAILABLE"))
            print(f"JUDGE {name:6} rejections it also rejects {sum(1 for f, _ in vn if not f)}/{len(vn)} · "
                  f"applications it approves {sum(1 for f, _ in vp if f)}/{len(vp)}"
                  + (f" · unavailable {unav}" if unav else ""))
            if show and name == "after":
                # Every disagreement, her side next to the judge's — the input for fixing the judge.
                for e, (f, w) in zip(poss, vp):
                    if not f:
                        print(f"  ✖ she APPLIED, judge rejected: {e['title'][:70]}\n      judge: {w[:150]}")
                for e, (f, w) in zip(negs, vn):
                    if f:
                        print(f"  ✖ she REJECTED, judge approved: {e['title'][:70]}\n"
                              f"      her reason: {(e.get('why') or '')[:150]}\n      judge: {w[:120]}")
    finally:
        llm_judge._feedback_block = new_block


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", type=int, default=0, help="also replay the judge on N + N decisions")
    ap.add_argument("--since", default="", help="judge only decisions first made on/after YYYY-MM-DD")
    ap.add_argument("--show", action="store_true", help="print every disagreement with her decision")
    a = ap.parse_args()
    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))["deals"]
    except Exception as e:
        print(f"no ledger yet ({e}) — run scripts/judge_feedback_sync.py first")
        return 1
    rules = load_rules()
    print(f"ledger {len(ledger)} decisions · learned rules {sorted(rules)}")
    replay_rules(ledger, rules)
    if a.judge:
        replay_judge(ledger, a.judge, a.since, a.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
