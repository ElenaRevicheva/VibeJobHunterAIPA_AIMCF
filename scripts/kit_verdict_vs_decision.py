#!/usr/bin/env python3
"""
kit_verdict_vs_decision.py — does CTO AIPA's apply-kit verdict predict which VJH jobs Elena rejects? (1 Nov 2026)

READ ONLY. Writes nothing to HubSpot or to any file; prints a table.

Elena's decision: the judge's own ledger (autonomous_data/judge_decisions.json) and its own rules, imported from
judge_feedback_sync — so "applied" and "rejected" mean exactly what the weekly precision line means.
The kit's verdict: what hs-fill-apply-kit.cjs already writes into the deal's notes —
  - "Its reviewer's note:"          the independent reviewer's fit_note (posting far from her evidence)
  - "Not shaped to this posting:"   no honest CV could be shaped to the duties
  - a 🎯 ROLE DEFENSE note without "Why you, in one line"   the reviewer dropped the pitch
A deal whose notes carry the kit but none of these = kit says clean. No kit notes = kit never ran.

  python3 scripts/kit_verdict_vs_decision.py [--since=2026-09-01] [--all-prefixes]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_feedback_sync as j  # noqa: E402  (its _hubspot_key, _fetch_notes_batch, LEDGER, stage sets)

SINCE = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--since=")), "2026-09-01")
ALL = "--all-prefixes" in sys.argv

KIT = ("🛡️ TECHNICAL DEFENSE", "🎯 ROLE DEFENSE")
FLAGS = {
    "fit_note": "Its reviewer's note",
    "not_shaped": "Not shaped to this posting",
}


def decision(e: dict):
    """Same rule as judge_feedback_sync._weekly_metrics."""
    if e["stage"] in j.NEGATIVE_STAGES:
        return "rejected"
    if e.get("applied") or e["stage"] in ("presentationscheduled", "closedwon"):
        return "applied"
    return None  # ⏳ Sent without her 'applied' marker, or 'They replied': not a verdict on fit


def verdict(notes: list):
    bodies = [n.get("body") or "" for n in notes]
    if not any(k in b for b in bodies for k in KIT):
        return "no kit", []
    why = [name for name, mark in FLAGS.items() if any(mark in b for b in bodies)]
    roles = [b for b in bodies if "🎯 ROLE DEFENSE" in b]
    if roles and not any("Why you, in one line" in b for b in roles):
        why.append("pitch_dropped")
    return ("flagged" if why else "clean"), why


def main() -> int:
    ledger = json.loads(j.LEDGER.read_text(encoding="utf-8"))
    deals = ledger.get("deals", ledger)
    picked = {}
    for did, e in deals.items():
        if not isinstance(e, dict) or (e.get("first_decided") or "") < SINCE:
            continue
        if not ALL and not e.get("prefix", "").startswith("HIRING-VJH"):
            continue
        d = decision(e)
        if d:
            picked[str(did)] = (e, d)
    if not picked:
        print(f"no decided deals since {SINCE}")
        return 0
    notes = j._fetch_notes_batch(j._hubspot_key(), list(picked))

    table, signals, examples = {}, {}, []
    for did, (e, d) in picked.items():
        v, why = verdict(notes.get(did, []))
        table[(v, d)] = table.get((v, d), 0) + 1
        for w in why:
            signals[(w, d)] = signals.get((w, d), 0) + 1
        if v == "flagged" and d == "applied":
            examples.append(f"  flagged but she APPLIED: {e.get('title', '')[:70]} ({', '.join(why)})")

    scope = "all hiring prefixes" if ALL else "VJH-found only"
    print(f"Decided deals since {SINCE} ({scope}): {len(picked)}")
    print(f"{'kit verdict':<12} {'applied':>8} {'rejected':>9} {'reject rate':>12}")
    for v in ("flagged", "clean", "no kit"):
        a, r = table.get((v, "applied"), 0), table.get((v, "rejected"), 0)
        rate = f"{100 * r / (a + r):.0f}%" if a + r else "—"
        print(f"{v:<12} {a:>8} {r:>9} {rate:>12}")
    print("signals:", ", ".join(f"{w}/{d}={n}" for (w, d), n in sorted(signals.items())) or "none")
    for x in examples[:10]:
        print(x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
