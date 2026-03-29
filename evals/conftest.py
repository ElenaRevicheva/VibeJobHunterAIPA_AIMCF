"""
Shared fixtures for VibeJobHunter eval suite.

Design principles:
- `matcher` fixture disables the AI client so all tests are deterministic,
  fast (<5s), and cost $0 in API tokens.
- `make_job` is a factory — tests describe exactly which signals they want
  present, keeping tests minimal and readable.
- `elena_profile` is the minimal Profile required by the founding scorer.
"""
import pytest

from src.core.models import JobPosting, JobSource, Profile
from src.agents.job_matcher import JobMatcher


@pytest.fixture(scope="session")
def matcher():
    """
    JobMatcher with the Anthropic client forcibly disabled.

    Why: `calculate_match_score` fires Claude for any job scoring ≥ 50
    in the preliminary phase.  Setting `self.ai = None` short-circuits that
    branch so every test in this file runs deterministically without network
    access or API cost.

    This is intentional, not a hack — we are testing the deterministic
    layers (keyword scoring + bias compensation).  Layer 4 (LLM consistency)
    is a separate file that explicitly re-enables the client.
    """
    m = JobMatcher()
    m.ai = None
    return m


@pytest.fixture
def make_job():
    """
    Factory fixture — builds a minimal valid JobPosting from keyword args.

    Usage:
        job = make_job(title="AI Engineer", description="llm python remote")
        job = make_job(title="Payroll Manager", description="payroll general ledger")

    Defaults are chosen so that unspecified fields never accidentally
    trigger bonuses or penalties in the scoring pipeline.
    """
    def _factory(
        title: str = "Software Engineer",
        company: str = "TestCo",
        description: str = "",
        location: str = "Remote",
        source: str = "other",
        remote_allowed: bool = True,
        url: str = "https://test.example.com/job/1",
        **kwargs,
    ) -> JobPosting:
        return JobPosting(
            title=title,
            company=company,
            description=description,
            location=location,
            source=JobSource(source),
            remote_allowed=remote_allowed,
            url=url,
            **kwargs,
        )
    return _factory


@pytest.fixture(scope="session")
def elena_profile():
    """
    Minimal Profile representing Elena — required by FoundingEngineerScorer.
    Fields beyond the required minimum are omitted intentionally.
    """
    return Profile(
        name="Elena Revicheva",
        email="aipa@aideazz.xyz",
        location="Panama",
        resume_path="resume.pdf",
        skills=["Python", "TypeScript", "LLM", "Claude", "GPT", "LangChain"],
        experience_years=10,
        target_roles=["Founding Engineer", "AI Engineer", "Staff AI Engineer"],
    )
