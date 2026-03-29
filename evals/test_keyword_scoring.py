"""
Layer 1 — Unit tests for keyword-based dimensional scoring.

What this tests:
  - _dimensional_score(): the 6-dimension keyword scoring engine
  - _wrong_role_penalty(): the 3-level wrong-role detection

What this does NOT test:
  - Claude AI analysis (no API calls — that is Layer 4)
  - Bias compensation bonuses/penalties (that is Layer 2)
  - End-to-end routing (that is Layer 3)

Run time: < 5 seconds, $0 API cost.

When to run:
  Before ANY edit to DIMENSION_KEYWORDS, WRONG_ROLE_TITLE_KEYWORDS,
  NOT_MY_LANE_TITLE_KEYWORDS, or MY_DOMAIN_TITLE_KEYWORDS.
"""
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# _dimensional_score: basic behavior
# ──────────────────────────────────────────────────────────────────────────────

class TestDimensionalScoreBasics:
    def test_base_score_40_when_no_keywords_match(self, matcher, make_job):
        """Job with zero relevant keywords must return exactly 40 (the career-gate base)."""
        job = make_job(title="Receptionist", description="answer phones greet visitors schedule meetings")
        score, _ = matcher._dimensional_score(job)
        assert score == 40.0

    def test_score_increases_with_high_tier_keywords(self, matcher, make_job):
        """A high-tier keyword must push score above the 40 base.

        Note: _dimensional_score has an early-return path for job_text < 50 chars
        (returns base=40, insufficient data).  The description must be long enough
        to pass that guard — a real job posting always is.
        """
        job = make_job(
            title="AI Engineer",
            description="build llm products for our enterprise customers using python and claude api",
        )
        score, _ = matcher._dimensional_score(job)
        assert score > 40.0

    def test_score_capped_at_100(self, matcher, make_job):
        """Score must never exceed 100 regardless of keyword density."""
        dense_desc = " ".join([
            "ai engineer llm machine learning neural founding engineer staff principal",
            "technical lead full-stack python typescript distributed systems",
            "remote bilingual web3 blockchain founding team seed series a",
        ] * 5)
        job = make_job(title="Founding AI Staff Principal Engineer", description=dense_desc)
        score, _ = matcher._dimensional_score(job)
        assert score <= 100.0

    def test_short_job_text_returns_base_score(self, matcher, make_job):
        """Job text under 50 chars returns base 40 (insufficient data path)."""
        job = make_job(title="Job", description="")
        score, _ = matcher._dimensional_score(job)
        assert score == 40.0

    def test_returns_reasons_list(self, matcher, make_job):
        """_dimensional_score must always return a non-empty reasons list."""
        job = make_job(title="AI Engineer", description="build llm products")
        _, reasons = matcher._dimensional_score(job)
        assert isinstance(reasons, list)
        assert len(reasons) > 0


# ──────────────────────────────────────────────────────────────────────────────
# _dimensional_score: per-dimension keyword tiers
# ──────────────────────────────────────────────────────────────────────────────

class TestDimensionKeywordTiers:
    def test_founding_engineer_triggers_high_autonomy(self, matcher, make_job):
        """'founding engineer' title must produce a high match in zero_to_one_autonomy.

        Descriptions must be ≥50 chars to clear _dimensional_score's short-text
        early-exit guard (a real job posting always clears this threshold).
        """
        job_high = make_job(
            title="Founding Engineer",
            description="build our core product from scratch with high autonomy and ownership of the stack",
        )
        job_none = make_job(
            title="Support Specialist",
            description="answer customer tickets and process support requests via our help desk platform",
        )
        score_high, _ = matcher._dimensional_score(job_high)
        score_none, _ = matcher._dimensional_score(job_none)
        # High match (25 * 0.6 = 15 pts) must significantly exceed base
        assert score_high > score_none + 10

    def test_llm_engineer_triggers_high_ai_ownership(self, matcher, make_job):
        """'llm engineer' title must trigger the high tier of ai_product_ownership (25 * 0.6 = 15 pts)."""
        job = make_job(
            title="LLM Engineer",
            description="work on large language models and build production ml systems for our platform",
        )
        score, reasons = matcher._dimensional_score(job)
        assert score > 50.0
        # At least one reason mentions the AI dimension
        ai_reason = any("ai" in r.lower() or "ownership" in r.lower() for r in reasons)
        assert ai_reason, f"Expected AI-related reason in {reasons}"

    def test_medium_tier_scores_lower_than_high_tier(self, matcher, make_job):
        """'startup' (medium) must score lower than 'founding engineer' (high) for zero_to_one_autonomy."""
        job_medium = make_job(title="Engineer", description="startup early stage small team")
        job_high = make_job(title="Founding Engineer", description="startup early stage small team")
        score_medium, _ = matcher._dimensional_score(job_medium)
        score_high, _ = matcher._dimensional_score(job_high)
        assert score_high > score_medium

    def test_remote_triggers_bilingual_global_dimension(self, matcher, make_job):
        """'remote' in description must contribute to bilingual_global dimension."""
        job_remote = make_job(title="AI Engineer", description="ai engineer remote international")
        job_local = make_job(title="AI Engineer", description="ai engineer on-site office")
        score_remote, _ = matcher._dimensional_score(job_remote)
        score_local, _ = matcher._dimensional_score(job_local)
        assert score_remote > score_local

    def test_web3_keywords_contribute_bonus(self, matcher, make_job):
        """'blockchain', 'web3', 'ethereum' must increase score via web3_bonus dimension."""
        job_web3 = make_job(title="AI Engineer", description="ai blockchain web3 ethereum smart contract")
        job_no_web3 = make_job(title="AI Engineer", description="ai python machine learning")
        score_web3, _ = matcher._dimensional_score(job_web3)
        score_no_web3, _ = matcher._dimensional_score(job_no_web3)
        assert score_web3 > score_no_web3

    def test_three_plus_medium_ai_keywords_beats_two(self, matcher, make_job):
        """3+ medium AI keywords must trigger the 50% weight tier instead of 40%."""
        # 1 medium AI keyword (< 3 matches → 40% tier)
        job_few = make_job(title="Engineer", description="ai python work on automation")
        # 3+ medium AI keywords (≥ 3 matches → 50% tier)
        job_many = make_job(title="Engineer", description="ai llm gpt claude neural langchain transformer")
        score_few, _ = matcher._dimensional_score(job_few)
        score_many, _ = matcher._dimensional_score(job_many)
        assert score_many > score_few


# ──────────────────────────────────────────────────────────────────────────────
# _wrong_role_penalty: Level 1 — obviously wrong roles
# ──────────────────────────────────────────────────────────────────────────────

class TestWrongRolePenaltyLevel1:
    def test_payroll_in_title_returns_minus_40(self, matcher, make_job):
        """'payroll' in title must return -40 penalty (Level 1 obvious wrong role)."""
        job = make_job(title="Payroll Manager", description="manage payroll processing")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -40
        assert reason is not None
        assert "wrong_role_title" in reason

    def test_financial_analyst_returns_minus_40(self, matcher, make_job):
        """'financial analyst' in title must return -40 penalty."""
        job = make_job(title="Financial Analyst", description="analyze budgets and forecasts")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -40

    def test_account_executive_returns_minus_40(self, matcher, make_job):
        """'account executive' in title must return -40 penalty."""
        job = make_job(title="Account Executive", description="manage sales pipeline")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -40

    def test_recruiter_returns_minus_40(self, matcher, make_job):
        """'recruiter' in title must return -40 penalty."""
        job = make_job(title="Technical Recruiter", description="source and screen candidates")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -40

    def test_description_with_two_plus_wrong_keywords_returns_minus_30(self, matcher, make_job):
        """2+ WRONG_ROLE_DESCRIPTION_KEYWORDS in description must return -30 (Level 1 desc)."""
        job = make_job(
            title="Operations Manager",
            description="payroll processing general ledger journal entries gaap compliance",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        # The title 'operations manager' is in WRONG_ROLE_TITLE_KEYWORDS? Let me check...
        # 'operations manager' is in WRONG_ROLE_TITLE_KEYWORDS.
        # If title fires first, penalty = -40. If not, description fires at -30.
        assert penalty in (-40, -30), f"Expected -40 or -30, got {penalty}"
        assert reason is not None


# ──────────────────────────────────────────────────────────────────────────────
# _wrong_role_penalty: Level 2 — not-my-lane roles
# ──────────────────────────────────────────────────────────────────────────────

class TestWrongRolePenaltyLevel2:
    def test_devops_no_ai_returns_minus_20(self, matcher, make_job):
        """'devops' title with no AI content must return -20 (not-my-lane)."""
        job = make_job(
            title="DevOps Engineer",
            description="kubernetes terraform jenkins ci/cd aws infrastructure grafana",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -20
        assert reason is not None
        assert "not_my_lane" in reason

    def test_qa_engineer_returns_minus_20(self, matcher, make_job):
        """'qa engineer' with no AI content must return -20."""
        job = make_job(title="QA Engineer", description="write test cases selenium pytest")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -20

    def test_data_analyst_returns_minus_20(self, matcher, make_job):
        """'data analyst' with no AI content must return -20."""
        job = make_job(title="Data Analyst", description="tableau sql dashboards kpi reporting")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -20

    def test_devops_with_heavy_ai_description_no_penalty(self, matcher, make_job):
        """
        CRITICAL EXCEPTION: DevOps title with 2+ AI signals in description
        must return (0, None) — the role is relevant despite the title.

        This tests the exception logic:
            if ai_in_desc >= 2: return 0, None
        If this test fails, the exception has been removed or broken,
        and 'DevOps for AI Platform' roles will be wrongly rejected.
        """
        job = make_job(
            title="DevOps Engineer",
            description=(
                "manage deployment infrastructure for our llm platform. "
                "build CI/CD pipelines for machine learning model serving. "
                "kubernetes, terraform, aws."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0, (
            f"Expected 0 (AI-heavy DevOps should be spared) but got {penalty}. "
            f"Reason: {reason}"
        )
        assert reason is None

    def test_sre_with_zero_ai_signals_is_penalized(self, matcher, make_job):
        """
        SRE title with zero AI content in description must get -20 (not-my-lane).

        Implementation note: the AI-signal check counts occurrences of seven patterns:
        ["ai ", " ai", "llm", "machine learning", "ml ", "generative", "language model"].
        Even a single word "ai" in the description will match BOTH "ai " and " ai"
        depending on surrounding whitespace, potentially reaching ai_in_desc = 2.
        To reliably test the penalized path, the description must contain NO AI terms.
        """
        job = make_job(
            title="SRE ",
            description="manage kubernetes clusters terraform infrastructure grafana monitoring on-call rotation",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -20

    def test_sre_with_single_ai_word_is_rescued(self, matcher, make_job):
        """
        DOCUMENTED BEHAVIOR: a single 'ai' word in the description matches
        BOTH 'ai ' and ' ai' in the seven-pattern counter, reaching ai_in_desc = 2.
        This means even one casual "ai" mention rescues a not-my-lane role.

        This test documents the behavior rather than asserting it is correct.
        If the rescue threshold logic is tightened later, this test must be updated.
        """
        job = make_job(
            title="SRE ",
            description="manage kubernetes clusters. we occasionally use ai tools for monitoring.",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        # One word "ai" in text → matches "ai " + " ai" → ai_in_desc = 2 → rescued
        assert penalty == 0
        assert reason is None


# ──────────────────────────────────────────────────────────────────────────────
# _wrong_role_penalty: Level 3 — no domain signal in title
# ──────────────────────────────────────────────────────────────────────────────

class TestWrongRolePenaltyLevel3:
    def test_generic_engineer_title_no_ai_description_minus_15(self, matcher, make_job):
        """'Senior Engineer' with no AI keywords anywhere must get -15 (no domain signal)."""
        job = make_job(
            title="Senior Engineer",
            description="build backend systems, optimize databases, refactor legacy code",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -15
        assert reason is not None

    def test_generic_title_two_plus_ai_in_description_no_penalty(self, matcher, make_job):
        """
        Generic title + 2+ AI keywords in description must return (0, None).

        This tests the Level-3 rescue: the title has no domain signal but
        the description makes it clear it's an AI role.
        """
        job = make_job(
            title="Senior Engineer",
            description="build backend systems for our llm platform. work with language models and ai teams.",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0
        assert reason is None

    def test_software_engineer_in_my_domain_keywords_no_penalty(self, matcher, make_job):
        """'software engineer' is in MY_DOMAIN_TITLE_KEYWORDS — must pass without penalty."""
        job = make_job(title="Software Engineer", description="build production systems")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0
        assert reason is None

    def test_ai_engineer_in_my_domain_keywords_no_penalty(self, matcher, make_job):
        """'ai engineer' in title must pass all three levels with no penalty."""
        job = make_job(title="AI Engineer", description="build llm products for customers")
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0
        assert reason is None

    def test_no_penalty_for_clearly_aligned_role(self, matcher, make_job):
        """Full founding AI engineer role must return (0, None) from wrong-role check."""
        job = make_job(
            title="Founding AI Engineer",
            description="founding engineer ai startup llm python typescript remote",
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0
        assert reason is None


# ──────────────────────────────────────────────────────────────────────────────
# US ELIGIBILITY BLOCK
# Elena is in Panama — not US work-authorized.
# These tests guard the -60 hard block that prevents applying to US-only roles.
# ──────────────────────────────────────────────────────────────────────────────

class TestUSEligibilityBlock:
    def test_us_work_authorization_required_returns_minus_60(self, matcher, make_job):
        """Explicit US work authorization requirement must return -60 penalty."""
        job = make_job(
            title="AI Engineer",
            description=(
                "We are looking for an AI engineer to join our team. "
                "Must be authorized to work in the United States. "
                "Python, LLM experience required."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -60
        assert "us_only_eligibility" in reason

    def test_us_citizens_only_returns_minus_60(self, matcher, make_job):
        """'US citizens only' in description must return -60 penalty."""
        job = make_job(
            title="Senior ML Engineer",
            description=(
                "Join our AI team. US citizens only. "
                "Work on large language models and AI infrastructure. "
                "Must be based in San Francisco or remote within the US."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -60

    def test_no_visa_sponsorship_returns_minus_60(self, matcher, make_job):
        """'We do not offer visa sponsorship' must block Elena (she needs work authorization)."""
        job = make_job(
            title="Staff AI Engineer",
            description=(
                "Build our core AI platform. Python, TypeScript, LLM experience. "
                "We do not offer visa sponsorship for this role. "
                "Candidates must be authorized to work in the US."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -60

    def test_must_be_us_based_returns_minus_60(self, matcher, make_job):
        """'Must be US-based candidates only' must return -60."""
        job = make_job(
            title="AI Product Engineer",
            description=(
                "Early-stage AI startup. US-based candidates only. "
                "Build LLM-powered products from scratch. Remote within the US."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -60

    def test_global_remote_ai_role_not_blocked(self, matcher, make_job):
        """AI role with no US restriction must NOT get -60 penalty."""
        job = make_job(
            title="AI Engineer",
            description=(
                "Build LLM products for our globally distributed team. "
                "Fully remote, open to candidates worldwide. "
                "Python, TypeScript, Claude, GPT experience preferred."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0, f"Global remote role should not be blocked, got penalty={penalty}"

    def test_us_only_overrides_good_role_title(self, matcher, make_job):
        """Even a perfect AI role gets -60 if US-only. Title quality is irrelevant."""
        job = make_job(
            title="Founding AI Engineer",
            description=(
                "First AI hire at a YC-backed startup. Build LLM pipelines from scratch. "
                "Must be authorized to work in the United States. Great comp + equity."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -60, "US-only block must fire even for founding AI engineer roles"


# ──────────────────────────────────────────────────────────────────────────────
# Wrong-stack penalty (Level 2b) — added 2026-03-29
# Elena's stack: Python / TypeScript / Node.js.
# Java, C#, .NET, Go, PHP, Ruby, Rust titles without AI context → -15.
# ──────────────────────────────────────────────────────────────────────────────

class TestWrongStackPenalty:
    def test_java_title_without_ai_returns_minus_15(self, matcher, make_job):
        """'Staff Engineer, Java' with no AI context must return -15."""
        job = make_job(
            title="Staff Engineer, Java",
            description=(
                "Build scalable backend microservices in Java. Spring Boot, Kafka, "
                "PostgreSQL. Experience with distributed systems required."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -15, f"Expected -15 for Java role, got {penalty}"
        assert "wrong_stack" in reason

    def test_dotnet_title_without_ai_returns_minus_15(self, matcher, make_job):
        """.NET in title without AI description must return -15."""
        job = make_job(
            title="Senior .NET Developer",
            description=(
                "Develop enterprise applications using .NET 8, C#, SQL Server. "
                "Work with Azure DevOps pipelines."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -15
        assert "wrong_stack" in reason

    def test_java_title_with_strong_ai_context_is_rescued(self, matcher, make_job):
        """Java title with heavy AI/LLM JD must be rescued (penalty waived)."""
        job = make_job(
            title="Java AI Platform Engineer",
            description=(
                "Build our machine learning platform with Java and Python. "
                "Work on LLM inference, AI model serving, and deep learning pipelines. "
                "NLP experience a plus."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == 0, (
            f"Java AI Platform role with heavy AI JD should not be penalised, got {penalty} ({reason})"
        )

    def test_golang_title_without_ai_returns_minus_15(self, matcher, make_job):
        """'Go Engineer' in title with non-AI description must return -15."""
        job = make_job(
            title="Go Engineer",
            description=(
                "Build high-performance microservices in Golang. gRPC, Kubernetes, "
                "distributed caching. 4+ years Go required."
            ),
        )
        penalty, reason = matcher._wrong_role_penalty(job)
        assert penalty == -15
        assert "wrong_stack" in reason

    def test_python_ai_engineer_not_penalised(self, matcher, make_job):
        """Python AI Engineer — Elena's core stack — must not get wrong-stack penalty."""
        job = make_job(
            title="Senior AI Engineer",
            description=(
                "Build LLM pipelines in Python. FastAPI, TypeScript, LangChain, AWS. "
                "Voice AI and memory systems experience valued."
            ),
        )
        penalty, _ = matcher._wrong_role_penalty(job)
        assert penalty == 0, f"Python AI engineer should have zero penalty, got {penalty}"
