# Eval Design: VibeJobHunter Scoring System

**Written:** 2026-03-27
**Author:** CTO AIPA (with Elena Revicheva)
**Status:** Design — not yet implemented
**Priority:** #1 tech debt

---

## Context

`src/agents/job_matcher.py` is the core decision engine of VibeJobHunter.
It produces a score for every scraped job. That score determines whether
the system sends a real application (≥ 60), founder outreach (58–59),
queues for human review (55–57), or silently discards the job (< 55).

There is currently **no eval framework**. Score quality can degrade without
any alert, log spike, or visible signal.

This document captures the risk analysis and the recommended eval design.

---

## The 5-Phase Scoring Pipeline

Every job passes through five phases in sequence:

| Phase | Type | What happens |
|-------|------|-------------|
| 1. Dimensional scoring | **Deterministic** | Keyword matching across 6 weighted dimensions. Base = 40, max bonus = 60. |
| 2. Founding engineer scorer | **Deterministic** | Specialist keyword scorer for role/stage/equity fit. Contributes 20% to preliminary score. |
| 3. Claude deep analysis | **LLM (subjective)** | Fires only if preliminary score ≥ 50. Claude Sonnet returns JSON score + reasons. Weighted 25–35% of final blend. |
| 4. Bias compensation | **Deterministic** | Wrong-role penalties (−10 to −40) and fit bonuses (+2 to +15). All keyword-based. |
| 5. Orchestrator boosts | **Deterministic** | YC source boost (+15), premium source (+5), priority company (+15). Applied after matcher returns. |

Routing thresholds (defined in `orchestrator.py`):

```
AUTO_APPLY_THRESHOLD  = 60   → real ATS application submitted
OUTREACH_THRESHOLD    = 58   → founder/CEO outreach email sent
REVIEW_THRESHOLD      = 55   → saved to human review queue
< 55                         → silently discarded
```

---

## 5 Silent Failure Risks

### Risk 1 — The LLM phase can fail completely without anyone noticing

**Where:** `job_matcher.py` line 493 and lines 496–501

The AI score has a forced floor: `ai_score_adjusted = max(ai_score, 50)`.
If Claude correctly identifies a bad job and returns 20, the system overrides
it to 50. Then Claude's weight in the blend is only 25–35%.

**Consequence:** If Claude starts returning garbage — due to a model change,
prompt drift, API error, or rate limiting — the final score shifts by ≤ 5
points. Jobs route to the same buckets. The LLM phase could be completely
broken and production would look normal.

**Detection gap:** No test. No alert. No log signal if Claude returns invalid
JSON (silent `except` swallows it and falls back to keyword-only).

---

### Risk 2 — Keyword list gaps cause systematic misclassification

**Where:** `DIMENSION_KEYWORDS` dictionaries, `WRONG_ROLE_TITLE_KEYWORDS`,
`MY_DOMAIN_TITLE_KEYWORDS`

The keyword lists are manually curated. A single missing "high" keyword
means a dimension scores at "medium" (40% of weight vs 60%) — a 4–5 point
swing per dimension, compounding across all six.

The `WRONG_ROLE_TITLE_KEYWORDS` blocklist applies a −40 penalty. One
overly broad entry (e.g. "security" blocking "AI Security Engineer") silently
rejects good jobs. Those jobs disappear below threshold — no Telegram
notification, no log, no audit trail.

New job-market terms ("agentic AI", "AI infra", "LLM ops") that aren't in
the lists yet will systematically undervalue roles that use that language.

---

### Risk 3 — Bonus stacking can push weak jobs over the auto-apply threshold

**Where:** `apply_bias_compensation()` + orchestrator source/priority boosts

Maximum possible bonus accumulation on a single job:
```
+4   senior role
+5   AI productivity
+3   small company
+3   quality source
+3   infra
+2   YC company
+15  personal AI fit
+15  YC source boost      (orchestrator)
+15  priority company     (orchestrator)
─────────────────────────
+65  total possible bonus
```

A job that scores 40 from dimensional matching alone can reach 100 through
bonus stacking. There is no minimum dimensional score required before bonuses
apply, and no "suspicious score" alert when the bonus sum exceeds the
dimensional score.

---

### Risk 4 — The Claude prompt has a hardcoded upward bias

**Where:** `_ai_deep_analysis()` prompt, line 606

```
IMPORTANT: Elena has 11 AI products shipped.
Be generous with AI/startup roles.
```

This instruction creates a systematic positive bias. Additionally, the prompt
instructs Claude to start AI roles at base 60 (not 50). Any future prompt
recalibration breaks all historical comparisons — but there are no historical
comparisons anyway.

---

### Risk 5 — No outcome feedback loop

**Where:** system-wide

The system applies to jobs and tracks application volume in daily summaries.
It does **not** track which scored jobs received interview callbacks, which
got rejections, and which were ghosted.

Without outcome data:
- The scoring system cannot validate or improve itself
- Threshold tuning (60/58/55) is based on intuition, not evidence
- Bias compensation bonuses cannot be measured for effectiveness

---

## Recommended Eval Design

### Ground Truth: Human-Labeled Golden Set

Build a set of **30–50 real job postings** with human labels.

**Sources:**
1. Jobs already applied to via the system → implicit label: `apply`
2. Jobs Elena saw in Telegram and manually dismissed → implicit label: `discard`
3. 10–15 edge cases constructed to probe specific risks:
   - DevOps role that mentions AI/LLM heavily (should domain penalty apply?)
   - Generic "Senior Engineer" at an AI startup (does title penalty fire?)
   - "Payroll AI Engineer" (does blocklist correctly spare or incorrectly kill?)
   - Personal AI company with no AI keywords in job text (does company name save it?)

**Label format per job:**

```json
{
  "id": "golden_001",
  "title": "Staff AI Engineer",
  "company": "Hume AI",
  "description": "...",
  "expected_action": "apply",
  "expected_score_min": 62,
  "expected_score_max": 80,
  "label_reason": "Personal AI company, staff role, voice/emotion AI core to Elena's work",
  "edge_case_type": null
}
```

---

### Layer 1 — Unit: Keyword Scoring (Deterministic)

**File:** `evals/test_keyword_scoring.py`

Tests `_dimensional_score()` in isolation on golden-set jobs.

- For each labeled job: assert final score is within ±5 of expected
- For each dimension: assert the correct tier (high/medium/low) fired
- For wrong-role blocklist: assert penalty amount matches expected
- For MY_DOMAIN keywords: assert domain signal detection is correct

**Expected runtime:** < 5 seconds (no API calls)

---

### Layer 2 — Unit: Bias Compensation (Deterministic)

**File:** `evals/test_bias_compensation.py`

Tests `apply_bias_compensation()` in isolation with synthetic `JobPosting`
objects constructed to trigger each bonus/penalty exactly once.

For every bonus and penalty rule, verify:
- The correct delta is applied (e.g. `+5_ai_productivity` appears in adjustments)
- The 0–100 floor/ceiling holds
- The wrong-role penalty runs first (before any bonus accumulation)
- Bonus stacking: construct a job with 5+ bonuses, assert final score ≤ 100

**Expected runtime:** < 5 seconds (no API calls)

---

### Layer 3 — Integration: Full Pipeline → Routing Bucket

**File:** `evals/test_full_pipeline.py`

Calls `calculate_match_score()` end-to-end on the full golden set.

For each labeled job, assert the final score lands in the correct
routing bucket:

```python
ROUTING_BUCKETS = {
    "apply":   (60, 100),
    "outreach": (58, 59),
    "review":  (55, 57),
    "discard": (0,  54),
}
```

This test catches:
- Threshold drift when bonuses are added
- Cases where bonus stacking moves a job from "discard" to "apply"
- Regression when keyword lists are edited

**Expected runtime:** 2–5 minutes (Claude API calls for jobs with preliminary ≥ 50)

---

### Layer 4 (Future) — LLM Consistency Check

**File:** `evals/test_llm_consistency.py`

For 10 golden-set jobs, run `_ai_deep_analysis()` three times each.

Assert:
- Score variance across 3 runs is < 10 points (Claude is consistent)
- Recommendation (`apply`/`maybe`/`skip`) is stable across runs
- Claude-as-judge: a second Claude call evaluates whether the reasons
  returned are accurate given the job description

This layer is optional for the MVP eval harness but important for catching
prompt drift when the model is updated.

---

### File Structure

```
evals/
├── golden_set.json           # 30–50 labeled jobs (human-curated)
├── conftest.py               # Shared fixtures (JobPosting builder, etc.)
├── test_keyword_scoring.py   # Layer 1: dimensional + wrong-role keywords
├── test_bias_compensation.py # Layer 2: bonuses + penalties
├── test_full_pipeline.py     # Layer 3: end-to-end routing bucket
├── test_llm_consistency.py   # Layer 4: Claude consistency (optional MVP)
└── README.md                 # How to run evals, how to add to golden set
```

Run command:

```bash
# Deterministic only (fast, no API cost) — run before any keyword edit
pytest evals/test_keyword_scoring.py evals/test_bias_compensation.py -v

# Full integration (includes Claude calls) — run before any threshold change
pytest evals/ -v
```

---

## Rule: When to Run Evals

| Trigger | Minimum eval layer |
|---------|-------------------|
| Editing any `DIMENSION_KEYWORDS` list | Layer 1 |
| Editing `WRONG_ROLE_TITLE_KEYWORDS` or `MY_DOMAIN_TITLE_KEYWORDS` | Layer 1 |
| Editing `apply_bias_compensation()` | Layer 2 |
| Changing `AUTO_APPLY_THRESHOLD`, `OUTREACH_THRESHOLD`, `REVIEW_THRESHOLD` | Layer 3 |
| Changing the Claude prompt in `_ai_deep_analysis()` | Layer 3 + Layer 4 |
| Claude model version change | Layer 4 |

---

## Interview Answer

> *"The scoring system has four deterministic layers and one LLM layer.
> The LLM layer does deep analysis but only for jobs that already passed
> keyword screening — I don't want to spend API calls on obviously wrong
> roles. I built an eval framework because I realized scoring quality could
> degrade silently: the LLM output is clamped and blended at 25–35% weight,
> so even if Claude returned garbage the final number barely shifts. Jobs
> route to the same buckets and nothing in the logs would alert you.*
>
> *My eval design uses a human-labeled golden set of 30+ real jobs drawn
> from the system's own history — jobs already applied to and jobs Elena
> manually rejected. I structured it in three layers: unit tests for the
> keyword scoring engine, unit tests for the bias compensation bonuses and
> penalties, and integration tests that assert the final score lands in the
> correct routing bucket — apply, outreach, review, or discard. The unit
> layers run in under five seconds with no API cost, so I run them before
> any keyword list edit. The integration layer runs before any threshold
> change. That way I can tune the system without introducing regressions I
> can't see."*

---

## Next Step

Build `evals/golden_set.json` first. Everything else depends on having
labeled ground truth. Suggested first session: Elena reviews the last
30 Telegram job notifications and labels each one — 30 minutes of work
that unlocks the entire eval framework.
