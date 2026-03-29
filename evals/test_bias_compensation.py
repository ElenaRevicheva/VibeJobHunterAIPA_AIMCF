"""
Layer 2 — Unit tests for apply_bias_compensation().

What this tests:
  - Every bonus rule fires when its trigger condition is met
  - Every penalty rule fires when its trigger condition is met
  - Wrong-role penalty always runs before bonuses (order matters)
  - Score floor (0) and ceiling (100) hold under all conditions
  - The adjustments list correctly names every adjustment made

What this does NOT test:
  - Dimensional keyword scoring (that is Layer 1)
  - Full pipeline routing (that is Layer 3)
  - Claude AI scoring (that is Layer 4)

Run time: < 5 seconds, $0 API cost.

When to run:
  Before ANY edit to apply_bias_compensation(), _wrong_role_penalty(),
  or any bonus/penalty threshold constant.
"""
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Score bounds — the one invariant that must NEVER break
# ──────────────────────────────────────────────────────────────────────────────

class TestScoreBounds:
    def test_score_never_below_zero(self, matcher, make_job):
        """Score floor is 0 even when penalty exceeds base score."""
        job = make_job(title="Payroll Manager", description="payroll processing accounting")
        adjusted, _ = matcher.apply_bias_compensation(10.0, job)
        assert adjusted >= 0.0

    def test_score_never_above_100(self, matcher, make_job):
        """Score ceiling is 100 even when every bonus stacks on a high base."""
        job = make_job(
            title="Senior Staff Founding AI Engineer",
            description=(
                "founding team seed startup series a remote equity companion ai voice agent "
                "memory system emotional ai llm tooling developer tools ai platform "
                "distributed systems infrastructure langchain agents"
            ),
        )
        adjusted, _ = matcher.apply_bias_compensation(95.0, job)
        assert adjusted <= 100.0

    def test_zero_base_with_bonus_stays_bounded(self, matcher, make_job):
        """Starting from 0, bonuses can increase score but ceiling still holds."""
        job = make_job(
            title="Senior AI Engineer",
            description="llm tooling developer tools distributed systems remote seed startup",
        )
        adjusted, _ = matcher.apply_bias_compensation(0.0, job)
        assert 0.0 <= adjusted <= 100.0


# ──────────────────────────────────────────────────────────────────────────────
# Wrong-role penalty (runs first)
# ──────────────────────────────────────────────────────────────────────────────

class TestWrongRolePenalty:
    def test_payroll_penalty_fires_and_is_labeled(self, matcher, make_job):
        """Payroll in title must add a '-40_wrong_role_title' adjustment label."""
        job = make_job(title="Payroll Manager", description="payroll processing")
        _, adjustments = matcher.apply_bias_compensation(50.0, job)
        penalty_labels = [a for a in adjustments if "wrong_role_title" in a]
        assert len(penalty_labels) == 1, f"Expected exactly 1 wrong_role_title label, got: {adjustments}"

    def test_not_my_lane_penalty_fires_and_is_labeled(self, matcher, make_job):
        """DevOps without AI must add a '-20_not_my_lane' adjustment label."""
        job = make_job(title="DevOps Engineer", description="kubernetes terraform jenkins ci/cd")
        _, adjustments = matcher.apply_bias_compensation(50.0, job)
        penalty_labels = [a for a in adjustments if "not_my_lane" in a]
        assert len(penalty_labels) == 1, f"Expected not_my_lane label, got: {adjustments}"

    def test_wrong_role_penalty_dominates_all_bonuses(self, matcher, make_job):
        """
        Even when EVERY bonus fires alongside a wrong-role, the final score
        must remain far below the auto-apply threshold (60).

        This validates the spec: wrong role should not be rescuable by
        stacking seed/equity/startup/AI bonuses.
        """
        job = make_job(
            title="Payroll Manager",
            description=(
                "payroll processing general ledger. "
                "seed stage startup series a remote equity founding team "
                "ai platform llm tooling developer tools distributed systems "
                "companion ai voice agent memory system emotional ai"
            ),
        )
        adjusted, adjustments = matcher.apply_bias_compensation(40.0, job)
        # Even with every possible bonus, a -40 penalty from a 40 base
        # leaves the score far below threshold
        assert adjusted < 60, (
            f"Wrong-role job reached {adjusted:.1f} — bonuses should not overcome -40 penalty. "
            f"Adjustments: {adjustments}"
        )

    def test_no_penalty_for_aligned_role(self, matcher, make_job):
        """Founding AI engineer must have no wrong-role penalty adjustment."""
        job = make_job(
            title="Founding AI Engineer",
            description="founding engineer ai startup llm python remote",
        )
        base = 70.0
        adjusted, adjustments = matcher.apply_bias_compensation(base, job)
        penalty_labels = [a for a in adjustments if a.startswith("-")]
        assert len(penalty_labels) == 0, f"Unexpected penalties: {penalty_labels}"
        assert adjusted >= base  # Only bonuses, no penalties


# ──────────────────────────────────────────────────────────────────────────────
# Individual bonus rules
# ──────────────────────────────────────────────────────────────────────────────

class TestBonusRules:
    def test_senior_role_bonus_plus_4(self, matcher, make_job):
        """'senior' in title must add +4_senior_role."""
        job = make_job(title="Senior AI Engineer", description="build llm products")
        adjusted, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+4_senior_role" in adjustments
        assert adjusted == pytest.approx(64.0, abs=1.0)

    def test_staff_triggers_senior_bonus(self, matcher, make_job):
        """'staff' also qualifies as a senior-level keyword and must trigger +4."""
        job = make_job(title="Staff Engineer", description="build systems")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+4_senior_role" in adjustments

    def test_principal_triggers_senior_bonus(self, matcher, make_job):
        """'principal' in title must trigger +4_senior_role."""
        job = make_job(title="Principal Engineer", description="architecture")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+4_senior_role" in adjustments

    def test_lead_triggers_senior_bonus(self, matcher, make_job):
        """'lead' in title must trigger +4_senior_role."""
        job = make_job(title="Technical Lead Engineer", description="lead a team")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+4_senior_role" in adjustments

    def test_ai_productivity_bonus_plus_5(self, matcher, make_job):
        """'llm tooling' in description must add +5_ai_productivity."""
        job = make_job(title="AI Engineer", description="build llm tooling for developers")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+5_ai_productivity" in adjustments

    def test_developer_tools_triggers_ai_productivity(self, matcher, make_job):
        """'developer tools' in description must trigger +5_ai_productivity."""
        job = make_job(title="Engineer", description="build developer tools and internal ai systems")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+5_ai_productivity" in adjustments

    def test_agents_keyword_triggers_ai_productivity(self, matcher, make_job):
        """'agents' in description must trigger +5_ai_productivity."""
        job = make_job(title="Engineer", description="build autonomous agents for customers")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+5_ai_productivity" in adjustments

    def test_startup_stage_bonus_for_seed(self, matcher, make_job):
        """'seed' in description (no company_size) must add +3_startup_stage."""
        job = make_job(title="AI Engineer", description="join our seed stage startup team")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+3_startup_stage" in adjustments

    def test_startup_stage_bonus_for_series_a(self, matcher, make_job):
        """'series a' in description must add +3_startup_stage."""
        job = make_job(title="AI Engineer", description="we are a series a startup building ai")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+3_startup_stage" in adjustments

    def test_infra_platform_bonus_for_distributed_systems(self, matcher, make_job):
        """'distributed systems' in description must add +3_infra_platform."""
        job = make_job(title="AI Engineer", description="build distributed systems and infrastructure")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+3_infra_platform" in adjustments

    def test_infra_platform_bonus_for_scalability(self, matcher, make_job):
        """'scalability' in description must add +3_infra_platform."""
        job = make_job(title="Engineer", description="focus on scalability and platform reliability")
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert "+3_infra_platform" in adjustments


# ──────────────────────────────────────────────────────────────────────────────
# Personal AI fit boost — the most nuanced bonus rule
# ──────────────────────────────────────────────────────────────────────────────

class TestPersonalAIFitBoost:
    def test_three_high_keywords_gives_plus_15(self, matcher, make_job):
        """
        3+ high personal AI keywords must produce +15_personal_ai_fit.

        High keywords: companion, voice agent, memory system, emotional ai, etc.
        This is Elena's strongest differentiator — the test protects it.
        """
        job = make_job(
            title="AI Engineer",
            description=(
                "build companion ai with voice agent capabilities, "
                "persistent memory system, and emotional ai interactions"
            ),
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 1
        boost = int(ai_fit_labels[0].split("_")[0].replace("+", ""))
        assert boost == 15, f"Expected +15 for 3+ high keywords, got +{boost}"

    def test_one_high_keyword_gives_plus_10(self, matcher, make_job):
        """1 high personal AI keyword (without company match) must give +10."""
        job = make_job(
            title="AI Engineer",
            description="build companion ai product for users",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 1
        boost = int(ai_fit_labels[0].split("_")[0].replace("+", ""))
        assert boost == 10

    def test_three_medium_keywords_gives_plus_10(self, matcher, make_job):
        """3+ medium personal AI keywords (no high matches) must give +10."""
        job = make_job(
            title="Engineer",
            description="build chatbot with tts speech capabilities and multimodal features",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 1
        boost = int(ai_fit_labels[0].split("_")[0].replace("+", ""))
        assert boost == 10

    def test_one_medium_keyword_gives_plus_5(self, matcher, make_job):
        """1 medium personal AI keyword (no high) must give only +5."""
        job = make_job(
            title="Engineer",
            description="work on our chatbot dialogue system",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 1
        boost = int(ai_fit_labels[0].split("_")[0].replace("+", ""))
        assert boost == 5

    def test_no_personal_ai_keywords_no_boost(self, matcher, make_job):
        """Standard AI job with no personal AI signals must have no personal_ai_fit label."""
        job = make_job(
            title="ML Engineer",
            description="build machine learning pipelines python scikit-learn distributed systems",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 0

    def test_personal_ai_company_alone_gives_plus_5(self, matcher, make_job):
        """Company name in personal_ai_companies list alone must give +5 even without keywords."""
        job = make_job(
            title="AI Engineer",
            company="Hume",
            description="build audio processing systems at hume",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        ai_fit_labels = [a for a in adjustments if "personal_ai_fit" in a]
        assert len(ai_fit_labels) == 1
        boost = int(ai_fit_labels[0].split("_")[0].replace("+", ""))
        assert boost == 5


# ──────────────────────────────────────────────────────────────────────────────
# Bonus stacking behavior
# ──────────────────────────────────────────────────────────────────────────────

class TestBonusStacking:
    def test_multiple_bonuses_accumulate(self, matcher, make_job):
        """When multiple bonus conditions fire, all adjustments appear in the list."""
        job = make_job(
            title="Senior AI Engineer",
            description="build llm tooling for developers in a series a startup with distributed systems",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        # Expect: +4_senior_role, +5_ai_productivity, +3_startup_stage, +3_infra_platform
        assert "+4_senior_role" in adjustments
        assert "+5_ai_productivity" in adjustments
        assert "+3_startup_stage" in adjustments
        assert "+3_infra_platform" in adjustments

    def test_adjustments_list_empty_when_no_conditions_fire(self, matcher, make_job):
        """
        A job with a domain-matched title and no bonus triggers must return empty adjustments.

        Note: the title must be in MY_DOMAIN_TITLE_KEYWORDS (e.g. 'software engineer')
        to avoid the Level-3 -15 penalty.  'Engineer' alone has no domain signal and
        always produces a '-15_no_domain_match_in_title' adjustment.
        """
        job = make_job(
            title="Software Engineer",
            description="build backend services and maintain production apis for the team",
        )
        _, adjustments = matcher.apply_bias_compensation(60.0, job)
        assert adjustments == [], f"Expected empty adjustments, got: {adjustments}"
