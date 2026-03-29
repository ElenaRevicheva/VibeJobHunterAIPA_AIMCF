# VibeJobHunter Eval Framework

Eval harness for the job scoring pipeline. Tests the deterministic layers
without API calls or production data.

---

## What's in here

```
evals/
├── conftest.py               # pytest fixtures: matcher (AI disabled), make_job, elena_profile
├── golden_set.json           # 10 human-labeled jobs — the regression baseline
├── test_keyword_scoring.py   # Layer 1: _dimensional_score + _wrong_role_penalty
├── test_bias_compensation.py # Layer 2: apply_bias_compensation bonuses + penalties
├── test_full_pipeline.py     # Layer 3: end-to-end routing bucket via golden set
└── README.md                 # this file
```

---

## Install

```bash
pip install -r requirements-dev.txt
```

---

## Run

```bash
# Layer 1 + 2 only — fast, $0 cost, no network
# Run before ANY edit to keyword lists or bonus/penalty rules
pytest evals/test_keyword_scoring.py evals/test_bias_compensation.py -v

# Full suite including golden-set routing (still no API calls — AI is disabled)
# Run before any threshold change in orchestrator.py
pytest evals/ -v

# Single test class
pytest evals/test_keyword_scoring.py::TestWrongRolePenaltyLevel2 -v

# Single test
pytest evals/test_bias_compensation.py::TestPersonalAIFitBoost::test_three_high_keywords_gives_plus_15 -v
```

---

## When to run what

| You are about to change... | Run this |
|---|---|
| `DIMENSION_KEYWORDS` in job_matcher.py | Layer 1 |
| `WRONG_ROLE_TITLE_KEYWORDS` | Layer 1 |
| `NOT_MY_LANE_TITLE_KEYWORDS` | Layer 1 |
| `MY_DOMAIN_TITLE_KEYWORDS` | Layer 1 |
| `apply_bias_compensation()` | Layer 2 |
| `AUTO_APPLY_THRESHOLD`, `OUTREACH_THRESHOLD`, `REVIEW_THRESHOLD` | Layer 3 |
| Claude prompt in `_ai_deep_analysis()` | Layer 3 + Layer 4 (TODO) |
| Claude model version | Layer 4 (TODO) |

---

## Routing buckets (from orchestrator.py)

```
Score ≥ 60  →  apply    (ATS form submission)
Score 58–59 →  outreach (founder email/LinkedIn)
Score 55–57 →  review   (human decision queue)
Score < 55  →  discard  (silent drop)
```

---

## Expanding the golden set

The golden set currently has 10 jobs.  The target is 30–50.

**Best source:** real jobs Elena has already seen in Telegram.

1. Open Telegram, scroll through the last 30 job notifications
2. For each one, decide: was this right to apply to / discard?
3. Add an entry to `golden_set.json` following the existing format:

```json
{
  "id": "golden_011",
  "title": "...",
  "company": "...",
  "location": "...",
  "description": "paste the job description here",
  "source": "other",
  "remote_allowed": true,
  "expected_action": "apply",
  "expected_score_min": 62,
  "expected_score_max": 100,
  "label_reason": "why you labeled it this way",
  "edge_case_type": null
}
```

**Valuable edge cases to add:**
- A DevOps role Elena thought was relevant (AI-heavy company)
- A job she applied to that turned out to be a bad fit
- A borderline score (landed in review/outreach, not apply/discard)
- A role with a misleading title but good description

---

## How the tests work (concept — not code)

**Layer 1** calls `_dimensional_score(job)` directly. This is pure keyword
math — no LLM, no randomness. The test constructs a minimal job that
should trigger exactly one signal and asserts the score moved the right direction.

**Layer 2** calls `apply_bias_compensation(base_score, job)` directly.
It tests each bonus/penalty rule in isolation by constructing a job that
contains exactly the trigger condition.  The test asserts the correct label
string appears in the `adjustments` list.

**Layer 3** calls the full `calculate_match_score(profile, job)` with
`matcher.ai = None` (Claude disabled). This runs the complete deterministic
path: dimensional → founding scorer → blending → bias compensation.
The test asserts each golden-set job routes to its labeled bucket.

---

## Layer 4 (not built yet — Future)

For 10 golden-set jobs, run `_ai_deep_analysis()` three times each.
Assert score variance < 10 points across runs.
Catches prompt drift when the Claude model is updated.
Cost: ~$0.30 per run (10 jobs × 3 calls × Sonnet pricing).
