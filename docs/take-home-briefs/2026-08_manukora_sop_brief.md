# Manukora — AI Automation Engineer: practical brief analysis & roadmap

**Stage reached:** practical brief (post-application), August 2026
**Role:** AI Automation Engineer · Manukora · remote LATAM · USD 4,000–4,850/mo · contractor via Deel
**Sourced by:** VibeJobHunter → Get on Board connector (`src/scrapers/getonbrd_jobs.py`, added 2026-08-04)

> **Scope of this document.** These are my own working notes — analysis, architecture decisions
> and build roadmap. The brief itself is Manukora's material and is deliberately **not reproduced
> here**: no verbatim text, no raw mock dataset. Only derived figures I computed appear below.
> The deliverable lives in its own repository, per their instructions.

---

## 1. Why this one mattered

The first genuine advance produced by the retargeting work, and worth recording as evidence for
whether that work paid off:

| | |
|---|---|
| Source | Get on Board — the second LATAM-first board, live **4 days** before this reply |
| Competition | **3 applications** at time of applying (compare: 274 on a PaperStreet role) |
| Pay | **USD 4,000–4,850/mo** — 33–60% above the $3,000 floor |
| Eligibility | LATAM explicitly in scope; **Panama qualifies** |

The source-conversion thesis — *add sources of the shape that converts, don't loosen filters* —
produced a real interview stage within a week. Recorded in `CAREER_FOCUS.md` under the Aug 4 entry.

---

## 2. What the brief is really assessing

Read the submission requirements as a rubric and the pattern is unmistakable — it is the job
description restated as a test:

| Brief asks for | Job description says |
|---|---|
| clear commits, README, setup notes, documented assumptions | *"Version work in GitHub with clear commits, useful README files, setup notes, and documented assumptions"* |
| the prompt/instruction stack used | *"Contribute reusable prompts, skills, runbooks and patterns to our shared AI & Systems library"* |
| tests / validation / how you verified the math | *"Ability to connect APIs, structure data, write lightweight scripts, and debug broken workflows"* |
| turn a rough business problem into a workflow | *"Business judgment. You ask what outcome the workflow should create before choosing tools"* |

**Conclusion: the automation is table stakes; the process artifacts are the differentiator.**
A polished narrative with no working system fails. A working system with unclear reasoning is
"hard to assess" — their words. Both halves have to land.

---

## 3. Data analysis — the five traps

The mock dataset is deliberately seeded. Each trap punishes a naive reading:

1. **Phase-out SKU is *above* its threshold.** The SKU being discontinued sits at **41 days**
   of cover against a stated 30-day trigger — under target cover, but explicitly *not* a reorder.
   A stock-risk-only model recommends buying it. The correct answer is to leave it alone.
2. **One SKU carries a different target.** A premium, long-lead-time line uses a **3-month**
   target, not the default 2. Applying the default understates its gap by a full month.
3. **A launch mid-window makes M1 meaningless for three SKUs.** Measuring their trend from M1
   overstates growth by **+13 to +19 percentage points** (e.g. +46.8% vs the correct +28.2%).
   The M1 figures exist in the data, which is what makes it a trap rather than an omission.
4. **Inventory is pooled; demand is not.** Channel demand must be summed before any cover
   calculation. Per-channel cover is silently wrong.
5. **"Arrival in 0 months" means no order exists** — not an immediate arrival. Treating it as
   incoming inventory inflates cover on every SKU without a purchase order.

**A sixth, unflagged and worth the marks:** the brief defines revenue opportunity against
***projected*** monthly demand, not the most recent month's. Every SKU here is growing 12–34%,
so using the latest month flat understates risk across the board. I project forward explicitly
and document the method rather than quietly substituting the easier number.

### Derived priority (my computation)

Ranked by revenue opportunity, which is what the brief asks for — not by stock risk:

| # | SKU class | Cover vs target | Revenue/mo | Call |
|---|---|---|---|---|
| 1 | 514+ 500g | 1.99 / 2 | **$31,356** | reorder |
| 2 | 850+ 500g | 1.80 / 2 | **$26,838** | reorder |
| 3 | 1700+ 100g | 2.80 / **3** | **$17,997** | reorder — note the 3-month target |
| 4–5 | two Bioactive lines | 1.91, 1.68 / 2 | $15,516, $14,556 | reorder, second tier |
| — | phase-out SKU | 1.37 / 2 (**41 days**) | $5,878 | **do not reorder** |

**The tension case:** the highest-volume SKU (~$25,790/mo) has one channel declining ~4% while
the other grows — and it is already sitting on **6.2 months of cover with more inventory inbound**.
Correct answer: don't reorder, investigate the soft channel. This is the case that separates
"ranked by revenue" from "thought about the business."

---

## 4. Architecture decision

**All arithmetic in deterministic Python. The LLM only turns a computed decision object into
executive narrative, and is forbidden from doing maths.**

Reasoning: the reviewers will check the numbers. An LLM dividing stock by demand across twelve
SKUs will eventually get one wrong, and one wrong number discredits the whole briefing. This also
produces an honest, concrete answer to their explicit question *"where did the AI help, where was
it wrong?"* — instead of the generic answer most submissions will give.

It is the same principle already load-bearing in this repo: `job_matcher.py` computes, the LLM
judges, and the two are never allowed to swap jobs.

### Repository layout (deliverable repo)

```
manukora-sop-brief/
├── README.md              approach · setup · assumptions · prompt stack · verification
├── ASSUMPTIONS.md         every judgment call + how I would verify it with a stakeholder
├── data/                  provided mock dataset
├── src/                   load · metrics · rules · narrate · main
├── prompts/               v1_first_attempt · v2_final · CHANGELOG
├── tests/                 one named test per trap
├── output/                the generated briefing
└── docs/                  Part 2 architecture · screenshots
```

### Tests as the verification story

Each trap becomes a named test, so *"I verified the math"* stops being a claim:

- `test_phaseout_sku_not_reordered_above_threshold`
- `test_premium_sku_uses_three_month_target`
- `test_launch_sku_trend_excludes_partial_month`
- `test_demand_is_pooled_across_channels`
- `test_zero_arrival_months_means_no_order`
- `test_priority_ranks_by_revenue_not_stock_risk`

### Prompt stack, documented honestly

- **v1** — hand the model the raw dataset and ask for a briefing. Hallucinates figures, misses
  every business rule, produces a summary rather than a decision.
- **v2** — the model receives a *pre-computed* decision object with explicit reasoning fields and
  is instructed to write narrative only.

The delta between them is the answer to their question, and it is true rather than constructed.

---

## 5. Part 2 — Morning Intelligence Brief (architecture only, 500–800 words)

Shopify + one more source (Klaviyo for engagement, or Cin7 for inventory truth).

**The interesting constraint is send timing** — the executive may be in New Zealand, Los Angeles,
or travelling, and a fixed 6am NZ send misses them. Approach: **compose on a fixed schedule,
deliver on first engagement signal** within a defined window, with a guaranteed fixed-time
fallback. Uses signals already available (email open, Slack activity) rather than location
tracking — the brief explicitly warns against "creepy," and inferring location from device data
is exactly that. State the boundary in the writeup.

Must also cover: rough operating cost at their scale, failure modes, and noise control — the
signal-to-noise rule being that a brief which cries wolf twice is never read again.

**Signature element:** alert on the *absence* of a brief, not only on errors. "Ran fine, found
nothing to report" is indistinguishable from "the pipeline is dead," and it is the failure mode
that survives longest in production. Same lesson as the Make trigger that went blind for three
days while every dashboard stayed green.

---

## 6. Build order

| Step | Work |
|---|---|
| 1 | `ASSUMPTIONS.md` **before** code — record what is ambiguous and what I chose |
| 2 | `metrics.py` + tests — prove the math before any narrative exists |
| 3 | `rules.py` — the business rules, one function per trap, each individually testable |
| 4 | `narrate.py` — LLM turns the decision object into prose; no arithmetic reaches it |
| 5 | Generate output, screenshot the run |
| 6 | README with the full prompt-stack story |
| 7 | Part 2 writeup |
| 8 | Reply ahead of the deadline, not on it |

**Scope discipline:** say plainly what was deliberately left out and why. On a time-boxed brief
that reads as senior, and it is the honest description of any 48-hour build.

---

## 7. Open item

The recruiter message said **5 business days**; the brief text says **48 calendar hours**.
These conflict. The brief invites a reply if the window is awkward — so confirm which applies
rather than silently assuming the generous one.
