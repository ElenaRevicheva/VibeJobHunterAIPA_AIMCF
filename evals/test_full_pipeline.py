"""
Layer 3 — Integration tests: full scoring pipeline -> routing bucket.

What this does NOT test:
  - Gate-only discard cases (edge_case_type=gate_blocks_before_scoring) — tested separately
"""
import json
import pytest
from pathlib import Path

from src.autonomous.orchestrator import (
    AUTO_APPLY_THRESHOLD,
    OUTREACH_THRESHOLD,
    REVIEW_THRESHOLD,
)
from src.autonomous.job_gate import JobGate
_gate = JobGate()

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
GOLDEN_SET = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))

SCORER_GOLDEN_SET = [c for c in GOLDEN_SET if c.get("edge_case_type") != "gate_blocks_before_scoring"]
GATE_ONLY_CASES   = [c for c in GOLDEN_SET if c.get("edge_case_type") == "gate_blocks_before_scoring"]


def routing_bucket(score: float) -> str:
    if score >= AUTO_APPLY_THRESHOLD:
        return "apply"
    elif score >= OUTREACH_THRESHOLD:
        return "outreach"
    elif score >= REVIEW_THRESHOLD:
        return "review"
    else:
        return "discard"


@pytest.mark.parametrize("case", SCORER_GOLDEN_SET, ids=[c["id"] for c in SCORER_GOLDEN_SET])
def test_routing_bucket_matches_label(matcher, make_job, elena_profile, case):
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


@pytest.mark.parametrize("case", SCORER_GOLDEN_SET, ids=[c["id"] for c in SCORER_GOLDEN_SET])
def test_score_within_expected_range(matcher, make_job, elena_profile, case):
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


@pytest.mark.parametrize("case", GATE_ONLY_CASES, ids=[c["id"] for c in GATE_ONLY_CASES])
def test_gate_blocks_excluded_title(make_job, case):
    """Jobs with edge_case_type=gate_blocks_before_scoring must be rejected by passes_gate()."""
    job = make_job(
        title=case["title"],
        company=case["company"],
        description=case["description"],
        location=case.get("location", "Remote"),
        remote_allowed=case.get("remote_allowed", True),
    )
    blocked = not _gate.passes(job.dict() if hasattr(job, "dict") else job)
    assert blocked, (
        f"\n{case['id']} — {case['title']} @ {case['company']}\n"
        f"  Expected gate to BLOCK this title but it PASSED.\n"
        f"  Reason: {case['label_reason']}\n"
    )
