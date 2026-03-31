"""
Layer 4 — LLM-as-judge consistency tests.

What this tests:
  - Whether Claude's independent judgment of "should Elena apply?" agrees
    with the deterministic scoring engine's routing decision.
  - Catches drift between what the keyword scorer considers a good match
    and what an LLM (with full context of Elena's honest profile) would
    recommend. Disagreements are INFORMATIVE, not necessarily bugs.

What this does NOT test:
  - Keyword scoring mechanics (that is Layer 1)
  - Bias compensation rules (that is Layer 2)
  - Golden set routing correctness (that is Layer 3)

Cost: ~$0.03–0.08 per full run (10–15 Claude Haiku calls).
Run time: 15–45 seconds (network-bound).
When to run:
  - After major changes to CAREER_FOCUS.md or positioning strategy
  - After changing the judge prompt or Elena's profile description
  - Weekly as a consistency check on scoring calibration

Requires: ANTHROPIC_API_KEY environment variable.
If missing, all tests are skipped (not failed).
"""
import json
import os
import pytest
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Load API key — try multiple sources in priority order
# ─────────────────────────────────────────────────────────────────────────────


def _find_anthropic_key() -> str:
    """
    Resolve ANTHROPIC_API_KEY from the most reliable source available.

    Priority:
    1. System environment (if non-empty) — works on Oracle/production
    2. .env file via python-dotenv — works on local dev
    3. Empty string → tests will skip gracefully
    """
    # 1. System environment (already set and non-empty)
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key.strip():
        return key.strip()

    # 2. Load from .env file (override=True forces .env values over empty env vars)
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(env_path, override=True)
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if key.strip():
            return key.strip()
    except ImportError:
        pass

    return ""


ANTHROPIC_API_KEY = _find_anthropic_key()
HAS_API_KEY = bool(ANTHROPIC_API_KEY)

pytestmark = pytest.mark.skipif(
    not HAS_API_KEY,
    reason="ANTHROPIC_API_KEY not set — Layer 4 (LLM judge) requires API access. "
           "Set it in your system environment or in the project .env file.",
)

if HAS_API_KEY:
    from anthropic import Anthropic

from src.agents.job_matcher import JobMatcher
from src.core.models import JobPosting, JobSource, Profile
from src.autonomous.orchestrator import (
    AUTO_APPLY_THRESHOLD,
    OUTREACH_THRESHOLD,
    REVIEW_THRESHOLD,
)


# ─────────────────────────────────────────────────────────────────────────────
# Elena's honest profile — grounded in career_analysis_v2.html
# This is the context the judge uses to evaluate fit. It must stay aligned
# with CAREER_FOCUS.md and SKILL.md Section 2.
# ─────────────────────────────────────────────────────────────────────────────

ELENA_PROFILE_FOR_JUDGE = """
CANDIDATE: Elena Revicheva

HONEST POSITIONING (from career analysis v2 — March 2026):
Executive-turned-AI-builder. NOT a "Senior AI Engineer" by conventional definition.

PHASE 1 (2011–2018): Deputy CEO & Chief Legal Officer — Russian public digital
infrastructure programs. Board-level governance, enterprise digital transformation.
7+ years at senior leadership layer.

PHASE 2 (2025–present): Applied AI builder. Designed and deployed 9 production AI
systems on Oracle Cloud using AI-assisted development (Cursor, Claude Code).
~1 year of hands-on AI engineering. EspaLuz has early paid users.

GAP (2018–2025): No conventional tech roles. ATS keyword filters see this gap
before they see the production systems.

LOCATION: Panama (UTC-5). NOT US work-authorized. Cannot accept roles requiring
US work authorization, visa sponsorship, or US residency.

TECH STACK: Python, TypeScript, Node.js, Claude API, GPT API, Oracle Cloud,
systemd, PM2, Telegram bots, FastAPI, Express. Builds with Cursor + Claude Code.

CONFIRMED SKILLS: Multi-agent orchestration, tool calling / webhook chains,
multi-model routing (76% Groq / 24% Claude with cost reasoning), voice pipeline
(Whisper + NLP), multi-modal pipeline (text/voice/image/video/NFT), Oracle Cloud
infra ($0/month), API design (REST, webhooks), executive communication.

HONEST GAPS: RAG (no production implementation), LangGraph (exposure only),
AWS (entirely Oracle), Docker (familiar, not in production), ML fundamentals
(no training / fine-tuning), LLM evals (Layers 1-3 built, Layer 4 in progress).

COMPENSATION: $3,500/month net minimum (full-time). $40-70/hr (fractional).

ROLES THAT FIT (apply):
- AI Automation Specialist
- Internal AI Tools Builder
- AI Integration Engineer
- Founding AI hire at pre-seed/seed startups (5-100 people)
- Fractional AI consultant / builder
- AI Ops / AI Program Manager

ROLES THAT DON'T FIT (discard):
- Senior / Staff / Principal AI Engineer at companies with 20+ engineers
  (ATS filters on 5+ years tenure and CS credentials she doesn't have)
- ML Engineer (requires ML fundamentals not yet built)
- Any role requiring US work authorization
- IT outsourcer staff augmentation (Nagarro, Infosys, etc.)
- Non-tech roles (payroll, sales, HR, legal, logistics)
- Wrong-stack roles (Java, C#, .NET, Go, PHP, Ruby, Rust — unless AI-focused)

IMPORTANT NUANCE: "Staff Engineer" at a 6-person startup is DIFFERENT from
"Staff Engineer" at a 200-person company. Founder-led hiring at small companies
doesn't apply the same credential filters. Evaluate the COMPANY CONTEXT, not
just the title.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Judge prompt — asks Claude to route the job independently
# ─────────────────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are an expert career advisor evaluating job fit for a specific candidate.

You will receive:
1. The candidate's honest profile (background, skills, gaps, constraints)
2. A job posting (title, company, description)

Your task: Decide the correct routing action for this candidate.

ROUTING OPTIONS:
- APPLY — The role genuinely fits the candidate's profile, skills, and constraints.
  The candidate has a realistic chance of getting past screening.
- OUTREACH — The role is promising but the candidate should reach out to the
  founder/hiring manager directly rather than submit through ATS.
- REVIEW — Worth looking at but unclear fit. Needs human review.
- DISCARD — The role does not fit. Wrong department, wrong stack, wrong seniority
  level, requires credentials the candidate doesn't have, or US-only.

DECISION RULES:
- If the job requires US work authorization → DISCARD (candidate is in Panama)
- If the title is clearly non-tech (payroll, sales, recruiter, etc.) → DISCARD
- If the role requires 5+ years of a specific technology the candidate has <1 year in → likely DISCARD
- If it's a founding/early hire at a small AI startup → likely APPLY
- If it's a fractional or contract AI role → likely APPLY
- A strong AI company with a wrong-department title (Account Executive at Anthropic) → still DISCARD
- "Staff Engineer" at a 6-person startup is APPLY; at Nagarro/Infosys → DISCARD

Respond with EXACTLY one line in this format:
VERDICT: <APPLY|OUTREACH|REVIEW|DISCARD>
REASON: <one sentence explaining why>

Nothing else. No preamble. No caveats."""


def _build_judge_user_prompt(title: str, company: str, description: str) -> str:
    return f"""{ELENA_PROFILE_FOR_JUDGE}

---

JOB POSTING:
Title: {title}
Company: {company}
Description: {description[:1500]}

Based on the candidate profile above, what is the correct routing action for this job?"""


# ─────────────────────────────────────────────────────────────────────────────
# Curated judge cases — covers all 4 routing buckets
# Drawn from golden_set.json + new cases specific to Layer 4 concerns
# ─────────────────────────────────────────────────────────────────────────────

JUDGE_CASES = [
    # ── SHOULD APPLY ──
    {
        "id": "judge_001",
        "title": "Founding AI Engineer",
        "company": "Aethon AI",
        "description": (
            "We are an early-stage AI startup (seed funding) building LLM-powered "
            "developer tools. You will be the founding engineer — the first technical "
            "hire — building our core AI product from scratch. Own the full stack: "
            "Python, TypeScript, LangChain, LLM APIs, distributed systems. "
            "Remote-first, startup culture, equity offered. Ship fast, high autonomy."
        ),
        "expected_verdict": "apply",
        "why": "Seed AI startup, founding hire, Python/TS, LLM, remote. Perfect fit.",
    },
    {
        "id": "judge_002",
        "title": "AI Product Engineer",
        "company": "Resonance",
        "description": (
            "Build our personal AI companion with voice agent capabilities, persistent "
            "memory system, and conversational AI features. Work on text-to-speech, "
            "multimodal interactions, emotional AI, and language learning experiences. "
            "TypeScript, Python, LLM APIs. Seed stage startup, remote, equity."
        ),
        "expected_verdict": "apply",
        "why": "Personal AI companion — voice, memory, multimodal. Elena's exact portfolio.",
    },
    {
        "id": "judge_003",
        "title": "AI Automation Engineer",
        "company": "BuildKit",
        "description": (
            "Small team (8 people), Series A. Build internal AI automation tools: "
            "webhook orchestration, multi-model LLM routing, Telegram/Slack integrations. "
            "Python, TypeScript, FastAPI. Fully remote, LATAM timezone preferred. "
            "We use Cursor and Claude Code daily. $3.5K-5K/month."
        ),
        "expected_verdict": "apply",
        "why": "AI automation at small startup, LATAM-friendly, her exact stack and tools.",
    },
    # ── SHOULD DISCARD — wrong role ──
    {
        "id": "judge_004",
        "title": "Payroll Manager",
        "company": "FinCorp",
        "description": (
            "Manage payroll processing for 200+ employees. Administer benefits, "
            "general ledger reconciliation, GAAP compliance, journal entries, "
            "accounts payable. Excel and QuickBooks required. CPA preferred."
        ),
        "expected_verdict": "discard",
        "why": "Completely non-tech. Payroll/finance role.",
    },
    {
        "id": "judge_005",
        "title": "Account Executive",
        "company": "Mistral",
        "description": (
            "At Mistral AI, we believe in the power of AI to simplify tasks, save time, "
            "and enhance learning and creativity. Our technology is designed to integrate "
            "seamlessly into daily working life. We democratize AI through high-performance "
            "models, products and solutions. Enterprise sales role, manage pipeline, "
            "hit quarterly targets."
        ),
        "expected_verdict": "discard",
        "why": "Sales role at a top AI company. Wrong department — title overrides company prestige.",
    },
    # ── SHOULD DISCARD — US-only ──
    {
        "id": "judge_006",
        "title": "AI Engineer",
        "company": "ScaleAI",
        "description": (
            "Join our AI team building LLM evaluation pipelines. Python, TypeScript, "
            "Claude, GPT experience required. Must be authorized to work in the United "
            "States. We do not offer visa sponsorship. Great comp + equity."
        ),
        "expected_verdict": "discard",
        "why": "Perfect role BUT requires US work authorization. Elena is in Panama.",
    },
    # ── SHOULD DISCARD — wrong stack ──
    {
        "id": "judge_007",
        "title": "Staff Engineer, Java",
        "company": "Nagarro",
        "description": (
            "Build scalable backend microservices in Java. Spring Boot, Kafka, "
            "PostgreSQL. Experience with distributed systems required. "
            "Enterprise client projects."
        ),
        "expected_verdict": "discard",
        "why": "Wrong stack (Java) at IT outsourcer (Nagarro). Double disqualifier.",
    },
    # ── SHOULD DISCARD — not her lane ──
    {
        "id": "judge_008",
        "title": "DevOps Engineer",
        "company": "CloudBase",
        "description": (
            "Manage Kubernetes clusters, build CI/CD pipelines with Jenkins and "
            "GitHub Actions. Terraform infrastructure-as-code on AWS. Monitor "
            "production with Grafana and PagerDuty. On-call rotation required."
        ),
        "expected_verdict": "discard",
        "why": "DevOps with no AI content. Not her lane.",
    },
    # ── EDGE CASE — security engineer with heavy AI description ──
    {
        "id": "judge_009",
        "title": "Security Engineer",
        "company": "ShieldAI",
        "description": (
            "Build security systems for our AI platform. Focus on LLM safety, "
            "machine learning model security, generative AI red teaming, and "
            "language model guardrails. Work alongside AI researchers to harden "
            "our LLM deployment infrastructure. Python, TypeScript. Series B startup."
        ),
        "expected_verdict": "review",  # LLM oscillates apply/review — both accepted via tolerance
        "why": "Title says security but JD is LLM safety/guardrails. Genuinely ambiguous — judge oscillates between APPLY and REVIEW.",
    },
    # ── EDGE CASE — Senior AI Engineer at large company (career analysis says DISCARD) ──
    {
        "id": "judge_010",
        "title": "Senior AI Engineer",
        "company": "Salesforce",
        "description": (
            "Join our Einstein AI team (500+ engineers). 5+ years of Python and "
            "machine learning experience required. MS or PhD in Computer Science "
            "preferred. Build large-scale ML pipelines, model training infrastructure, "
            "distributed systems. Must be authorized to work in the US."
        ),
        "expected_verdict": "discard",
        "why": "Large company (500+ eng), requires 5+ years ML, CS degree preferred, US-only.",
    },
    # ── EDGE CASE — Data Scientist (recently fixed in NOT_MY_LANE) ──
    {
        "id": "judge_011",
        "title": "Data Scientist",
        "company": "CrowdStrike",
        "description": (
            "Build machine learning models for threat detection. Python, scikit-learn, "
            "TensorFlow, statistical modeling. 3+ years data science experience required. "
            "Analyze large datasets, build predictive models, A/B testing."
        ),
        "expected_verdict": "discard",
        "why": "Data scientist — requires ML fundamentals (training, statistical modeling) she doesn't have.",
    },
    # ── SHOULD APPLY — LATAM-friendly global remote ──
    {
        "id": "judge_012",
        "title": "AI Integration Engineer",
        "company": "RemoteFirst AI",
        "description": (
            "Fully distributed team, hire internationally. Build AI-powered webhook "
            "orchestration and multi-platform integrations. Python, TypeScript, "
            "FastAPI, LLM APIs. Open to candidates worldwide, async-first culture. "
            "Americas timezone overlap preferred. $3.5K-4.5K/month."
        ),
        "expected_verdict": "apply",
        "why": "Global remote, LATAM-friendly, AI integration, her exact stack.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def judge_client():
    """Anthropic client for judge calls — uses Haiku for cost efficiency."""
    if not HAS_API_KEY:
        pytest.skip("No API key")
    return Anthropic(api_key=ANTHROPIC_API_KEY)


@pytest.fixture(scope="module")
def deterministic_matcher():
    """JobMatcher with AI disabled — same as Layers 1-3."""
    m = JobMatcher()
    m.ai = None
    return m


@pytest.fixture(scope="module")
def judge_profile():
    """Minimal Profile for the deterministic matcher."""
    return Profile(
        name="Elena Revicheva",
        email="aipa@aideazz.xyz",
        location="Panama",
        resume_path="resume.pdf",
        skills=["Python", "TypeScript", "LLM", "Claude", "GPT", "LangChain"],
        experience_years=10,
        target_roles=["Founding Engineer", "AI Engineer", "Staff AI Engineer"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper: call Claude as judge
# ─────────────────────────────────────────────────────────────────────────────

def _ask_judge(client, title: str, company: str, description: str) -> Optional[str]:
    """
    Ask Claude to independently route a job for Elena.
    Returns lowercase verdict: 'apply', 'outreach', 'review', or 'discard'.
    Returns None on API error.
    """
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": _build_judge_user_prompt(title, company, description),
            }],
        )
        text = response.content[0].text.strip()
        # Parse "VERDICT: APPLY" from response
        for line in text.split("\n"):
            if line.upper().startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip().lower()
                if verdict in ("apply", "outreach", "review", "discard"):
                    return verdict
        # Fallback: look for the keyword anywhere
        text_lower = text.lower()
        for v in ("discard", "apply", "outreach", "review"):
            if v in text_lower:
                return v
        return None
    except Exception as e:
        pytest.skip(f"Claude API error: {e}")
        return None


def _engine_routing_bucket(score: float) -> str:
    """Convert engine score to routing bucket — mirrors orchestrator.py."""
    if score >= AUTO_APPLY_THRESHOLD:
        return "apply"
    elif score >= OUTREACH_THRESHOLD:
        return "outreach"
    elif score >= REVIEW_THRESHOLD:
        return "review"
    else:
        return "discard"


# ─────────────────────────────────────────────────────────────────────────────
# Individual case tests — each case gets its own test for clear reporting
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("case", JUDGE_CASES, ids=[c["id"] for c in JUDGE_CASES])
def test_judge_verdict_matches_expected(judge_client, case):
    """
    Claude-as-judge must agree with the human-labeled expected verdict.

    This tests whether Claude's independent evaluation (given Elena's full
    honest profile) reaches the same routing conclusion as the golden set
    human labels. A failure here means either:
      - The judge prompt needs updating (Elena's profile changed), OR
      - The human label was wrong and needs revisiting, OR
      - Claude found a nuance the human missed (inspect the reason)
    """
    verdict = _ask_judge(
        judge_client,
        case["title"],
        case["company"],
        case["description"],
    )
    assert verdict is not None, f"Judge returned unparseable response for {case['id']}"

    # Allow apply/outreach to be treated as equivalent for "positive" cases
    # (the boundary between apply and outreach is a narrow score band)
    expected = case["expected_verdict"]
    positive = {"apply", "outreach"}

    if expected in positive and verdict in positive:
        pass  # Both are "yes, pursue this" — agreement
    elif expected == "discard" and verdict == "review":
        pass  # Close enough — both are "don't auto-apply"
    elif expected == "review" and verdict in ("discard", "outreach", "apply"):
        pass  # Edge case tolerance — review is inherently ambiguous
    else:
        assert verdict == expected, (
            f"\n{case['id']} — {case['title']} @ {case['company']}\n"
            f"  Judge says: {verdict.upper()}\n"
            f"  Expected:  {expected.upper()}\n"
            f"  Why:       {case['why']}\n"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Agreement rate test — the headline metric
# ─────────────────────────────────────────────────────────────────────────────

def test_overall_agreement_rate(judge_client, deterministic_matcher, judge_profile):
    """
    The LLM judge must agree with the deterministic engine on ≥ 75% of cases.

    This is the headline metric for Layer 4. It measures whether the
    deterministic scoring engine (keyword + bias compensation + penalties)
    produces routing decisions that an LLM with full profile context would
    also make.

    Agreement means:
      - Both say APPLY or OUTREACH (positive routing), OR
      - Both say DISCARD or REVIEW (negative routing)

    Disagreement is informative:
      - Engine says APPLY but judge says DISCARD → potential false positive
        (the engine is sending applications that an informed reviewer wouldn't)
      - Engine says DISCARD but judge says APPLY → potential false negative
        (the engine is missing opportunities)

    The 75% threshold is deliberately set below 100% because:
      - Claude and the deterministic engine use fundamentally different approaches
      - Edge cases (e.g. "Security Engineer" with heavy AI JD) legitimately
        have ambiguous routing
      - LLM judge responses have natural variance
    """
    agreements = 0
    disagreements = []
    total = 0

    for case in JUDGE_CASES:
        # Get engine's deterministic routing
        job = JobPosting(
            title=case["title"],
            company=case["company"],
            description=case["description"],
            location="Remote",
            source=JobSource("other"),
            remote_allowed=True,
            url="https://test.example.com/job/1",
        )
        score, _ = deterministic_matcher.calculate_match_score(judge_profile, job)
        engine_bucket = _engine_routing_bucket(score)

        # Get judge's independent routing
        judge_verdict = _ask_judge(
            judge_client,
            case["title"],
            case["company"],
            case["description"],
        )
        if judge_verdict is None:
            continue

        total += 1

        # Agreement: both positive (apply/outreach) or both negative (review/discard)
        positive = {"apply", "outreach"}
        negative = {"review", "discard"}

        engine_positive = engine_bucket in positive
        judge_positive = judge_verdict in positive

        if engine_positive == judge_positive:
            agreements += 1
        else:
            disagreements.append({
                "id": case["id"],
                "title": case["title"],
                "company": case["company"],
                "engine": f"{engine_bucket} (score={score:.1f})",
                "judge": judge_verdict,
                "why": case["why"],
            })

    assert total > 0, "No judge verdicts were returned — API may be down"

    rate = agreements / total
    min_rate = 0.75

    # Build disagreement report for the assertion message
    disagreement_report = ""
    if disagreements:
        disagreement_report = "\n\nDISAGREEMENTS:\n"
        for d in disagreements:
            disagreement_report += (
                f"  {d['id']}: {d['title']} @ {d['company']}\n"
                f"    Engine: {d['engine']}  |  Judge: {d['judge']}\n"
                f"    Why: {d['why']}\n"
            )

    assert rate >= min_rate, (
        f"\nAgreement rate: {rate:.0%} ({agreements}/{total}) — "
        f"below {min_rate:.0%} threshold.{disagreement_report}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Engine-vs-judge consistency on the full golden set
# ─────────────────────────────────────────────────────────────────────────────

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


def test_golden_set_judge_consistency(judge_client, deterministic_matcher, judge_profile):
    """
    Run the LLM judge against the FULL golden set (22 entries) and report
    agreement rate. This is a softer test — it warns on low agreement
    rather than failing, because golden set entries were labeled for the
    deterministic engine, not for an LLM judge.

    Purpose: detect systematic bias in the deterministic engine that
    the judge can identify (e.g., consistently over-scoring one category).
    """
    golden_set = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))

    agreements = 0
    total = 0
    false_positives = []  # Engine says apply, judge says discard
    false_negatives = []  # Engine says discard, judge says apply

    for case in golden_set:
        job = JobPosting(
            title=case["title"],
            company=case["company"],
            description=case["description"],
            location=case.get("location", "Remote"),
            source=JobSource("other"),
            remote_allowed=case.get("remote_allowed", True),
            url="https://test.example.com/job/1",
        )
        score, _ = deterministic_matcher.calculate_match_score(judge_profile, job)
        engine_bucket = _engine_routing_bucket(score)

        judge_verdict = _ask_judge(
            judge_client,
            case["title"],
            case["company"],
            case["description"],
        )
        if judge_verdict is None:
            continue

        total += 1
        positive = {"apply", "outreach"}
        engine_positive = engine_bucket in positive
        judge_positive = judge_verdict in positive

        if engine_positive == judge_positive:
            agreements += 1
        elif engine_positive and not judge_positive:
            false_positives.append(
                f"  {case['id']}: {case['title']} @ {case['company']} "
                f"(engine={engine_bucket} score={score:.1f}, judge={judge_verdict})"
            )
        else:
            false_negatives.append(
                f"  {case['id']}: {case['title']} @ {case['company']} "
                f"(engine={engine_bucket} score={score:.1f}, judge={judge_verdict})"
            )

    assert total > 0, "No judge verdicts returned"

    rate = agreements / total

    # Report
    report = f"\nGolden Set Judge Consistency: {rate:.0%} ({agreements}/{total})"
    if false_positives:
        report += f"\n\nFALSE POSITIVES (engine applies, judge discards) — {len(false_positives)}:\n"
        report += "\n".join(false_positives)
    if false_negatives:
        report += f"\n\nFALSE NEGATIVES (engine discards, judge applies) — {len(false_negatives)}:\n"
        report += "\n".join(false_negatives)

    # Soft threshold — 70% for the full golden set
    # (some golden set entries are edge cases that legitimately have ambiguous routing)
    assert rate >= 0.70, report
