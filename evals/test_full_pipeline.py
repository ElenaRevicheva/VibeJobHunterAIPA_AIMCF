"""
Layer 3 — Integration tests: full scoring pipeline → routing bucket.

What this tests:
  - calculate_match_score() end-to-end on the human-labeled golden set
  - That every golden-set job routes to the correct bucket (apply/outreach/review/discard)
  - Regressions when keyword lists, thresholds, or bias compensation is edited

What this does NOT test:
  - Claude AI deep analysis (matcher.ai is None — see conftest.py)
  - LLM consistency across runs (that is Layer 4)

Run time: 2–10 seconds (no API calls, founding scorer is CPU-only).
When to run:
  - Before any change to AUTO_APPLY_THRESHOLD, OUTREACH_THRESHOLD, REVIEW_THRESHOLD
  - After any Layer 1 or Layer 2 regression to confirm routing is still correct
  - Before merging any keyword or bonus/penalty change

Golden set lives in evals/golden_set.json.
To add new cases: review real job notifications in Telegram and label them.
"""
import json
import pytest
from pathlib import Path

from src.autonomous.orchestrator import (
    AUTO_APPLY_THRESHOLD,
    OUTREACH_THRESHOLD,
    REVIEW_THRESHOLD,
)

# ─────────────────────────────────────────────────────────────────────────────
# Load golden set
# ─────────────────────────────────────────────────────────────────────────────

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
GOLDEN_SET = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Routing helper — mirrors the logic in orchestrator.py
# ─────────────────────────────────────────────────────────────────────────────

def routing_bucket(score: float) -> str:
    """Convert a numeric score to a routing bucket name."""
    if score >= AUTO_APPLY_THRESHOLD:
        return "apply"
    elif score >= OUTREACH_THRESHOLD:
        return "outreach"
    elif score >= REVIEW_THRESHOLD:
        return "review"
    else:
        return "discard"


# ─────────────────────────────────────────────────────────────────────────────
# Parametrized test — one test case per golden-set entry
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("case", GOLDEN_SET, ids=[c["id"] for c in GOLDEN_SET])
def test_routing_bucket_matches_label(matcher, make_job, elena_profile, case):
    """
    Each golden-set job must route to the labeled bucket (AI scoring disabled).

    A failure here means:
      - A keyword list edit changed a score across a threshold boundary, OR
      - A bonus/penalty rule was added, removed, or re-ordered, OR
      - A routing threshold constant was changed in orchestrator.py

    The error message prints the score and the label_reason so you can
    quickly determine whether the golden set needs updating or the
    code change introduced a regression.
    """
    job = make_job(
        title=case["title"],
        company=case["company"],
        description=case["description"],
        location=case.get("location", "Remote"),
        remote_allowed=case.get("remote_allowed", True),
    )

    score, _ = matcher.calculate_match_score(elena_profile, job)
    actual_bucket = routing_bucket(score)
    expected_bucket = case["expected_action"]

    assert actual_bucket == expected_bucket, (
        f"\n{case['id']} — {case['title']} @ {case['company']}\n"
        f"  Score:    {score:.1f}\n"
        f"  Bucket:   '{actual_bucket}' (expected '{expected_bucket}')\n"
        f"  Reason:   {case['label_reason']}\n"
        f"  Edge:     {case.get('edge_case_type', 'none')}\n"
    )


@pytest.mark.parametrize("case", GOLDEN_SET, ids=[c["id"] for c in GOLDEN_SET])
def test_score_within_expected_range(matcher, make_job, elena_profile, case):
    """
    Score must fall within the [expected_score_min, expected_score_max] range
    defined in the golden set.

    This is a tighter check than routing bucket — it catches cases where a
    score drifts across the range boundary without changing the bucket (which
    the previous test would miss).  For example: a founding engineer role
    slipping from 90 → 65 still routes to 'apply' but signals model drift.
    """
    job = make_job(
        title=case["title"],
        company=case["company"],
        description=case["description"],
        location=case.get("location", "Remote"),
        remote_allowed=case.get("remote_allowed", True),
    )

    score, _ = matcher.calculate_match_score(elena_profile, job)
    lo = case["expected_score_min"]
    hi = case["expected_score_max"]

    assert lo <= score <= hi, (
        f"\n{case['id']} — {case['title']}\n"
        f"  Score {score:.1f} is outside expected range [{lo}, {hi}].\n"
        f"  This signals drift in keyword scoring or bias compensation.\n"
        f"  Reason: {case['label_reason']}\n"
    )
