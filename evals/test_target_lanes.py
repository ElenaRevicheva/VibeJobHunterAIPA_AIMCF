"""
Every layer must agree on Elena's target lanes (2026-09-16).

Why this file exists: "AI Product Manager" was opened in the career gate, the fit
gate, the searches and the config on 2026-08-05, and never reached the LLM judge or
the AI scoring prompt. Those jobs scored 85-100 and were then vetoed as "not a
hands-on builder". A lane defined in seven places drifts; this suite pushes every
title in src/core/target_lanes.py through every layer, so a missed layer fails here
instead of silently in production.

Deterministic: no network, no LLM calls.
"""

import importlib.util
import inspect
from pathlib import Path

import pytest

from src.core import target_lanes
from src.core import llm_judge
from src.core.fit_gate import iron_clad_fit, title_on_lane
from src.autonomous.job_gate import JobGate

ROOT = Path(__file__).resolve().parents[1]

LOCATION = "Remote — Worldwide / LATAM"
# Carries AI-augmented signals (Claude, Cursor, GPT, no-code) but none of the gate's
# include phrases, so a title passes only on its own merits.
NEUTRAL_DESC = (
    "Fully remote role, open to candidates anywhere in Latin America. You will work "
    "with Claude, Cursor and GPT and no-code automation to deliver outcomes for founders."
)

TITLES = list(target_lanes.all_titles())


def test_registry_is_rich_and_unique():
    # Floor lowered 100 -> 95 on 2026-09-20. The builder lane lost 8 generic engineer titles
    # on Elena's instruction (they were 62% of the ACT-TODAY queue but 58% of her rejections
    # and 17% of her positives); 4 titles traceable to actual positives were added back, so
    # the registry sits at 96. The guard still catches a real gutting - it is not there to
    # stop a deliberate, measured cut, and padding it with invented titles to clear 100 would
    # defeat the point of the registry.
    assert len(TITLES) >= 95
    lowered = [t.lower() for t in TITLES]
    assert len(lowered) == len(set(lowered)), "duplicate lane titles"
    for must in ("Chief AI Officer", "AI Product Manager", "AI Solutions Architect",
                 "AI Systems Consultant", "AI-Proficient Executive Assistant"):
        assert must in TITLES


@pytest.mark.parametrize("title", TITLES)
def test_career_gate_passes_lane_title(title):
    job = {"title": title, "company": "Quetzal Studio",
           "location": LOCATION, "description": NEUTRAL_DESC}
    assert JobGate.passes(job), f"career gate drops lane title: {title}"


@pytest.mark.parametrize("title", TITLES)
def test_iron_clad_passes_lane_title(title):
    assert iron_clad_fit(title, LOCATION, NEUTRAL_DESC), f"iron_clad_fit drops: {title}"


@pytest.mark.parametrize("title", TITLES)
def test_title_on_lane(title):
    assert title_on_lane(title), f"title_on_lane drops: {title}"


@pytest.mark.parametrize("title", TITLES)
def test_judge_prompt_names_lane_title(title):
    assert title in llm_judge._PROMPT


def test_judge_prompt_formats_and_carries_guards():
    rendered = llm_judge._PROMPT.format(feedback="", title="x", company="y",
                                        location="z", desc="d")
    for guard in ("UTC-5", "EMPLOYEES only", "NEVER use reputation", "NO GUESSES",
                  "AI LEADERSHIP IS A LANE", "$3,000", "YEARS OF EXPERIENCE",
                  "whatever N is"):
        assert guard in rendered, guard
    assert "__LANES__" not in rendered
    assert "hands-on\n   BUILDER" not in rendered


def test_scoring_prompt_uses_shared_lanes():
    from src.agents.job_matcher import JobMatcher
    src = inspect.getsource(JobMatcher._ai_deep_analysis)
    assert "render_lanes_for_prompt" in src
    assert "Staff/Principal/Lead engineer role" not in src


@pytest.mark.parametrize("title", ["Senior Software Engineer (Java)", "VP Sales",
                                   "Executive Assistant", "Account Manager"])
def test_gate_still_rejects_off_lane(title):
    job = {"title": title, "company": "Quetzal Studio", "location": LOCATION,
           "description": "Fully remote role, open to Latin America."}
    assert not JobGate.passes(job), title


# NEUTRAL_DESC names Claude/Cursor/GPT, so it proves nothing about the AI-work check for a
# lane whose postings name video models instead. A real creative posting, shaped like the
# one that failed the live probe on 2026-09-28 ("AI Video Producer" parked by iron_clad_fit).
CREATIVE_DESC = (
    "Produce short-form films end to end with generative video models. Own concept, shot "
    "generation, edit, sound and publishing. Experience orchestrating multiple AI video "
    "tools required. Fully remote, open to candidates anywhere in Latin America."
)


CREATIVE_TITLES = [t for lane in target_lanes.LANES
                   if lane["name"] == "CREATIVE AI & GENERATIVE MEDIA SYSTEMS"
                   for t in lane["titles"]]


def test_creative_lane_exists():
    assert len(CREATIVE_TITLES) >= 10


@pytest.mark.parametrize("title", CREATIVE_TITLES)
def test_iron_clad_passes_creative_title_on_a_real_creative_posting(title):
    assert iron_clad_fit(title, LOCATION, CREATIVE_DESC), f"iron_clad_fit drops: {title}"


@pytest.mark.parametrize("title", ["Video Editor", "Video Producer", "Motion Graphics Artist",
                                   "Social Media Content Creator"])
def test_plain_media_roles_stay_off_lane(title):
    # The creative lane is generative-AI production, not every media job.
    assert not title_on_lane(title), title


def test_iron_clad_still_rejects_us_only():
    assert not iron_clad_fit("AI Product Manager", "Remote — United States", NEUTRAL_DESC)


def test_research_scientist_not_on_lane():
    assert not title_on_lane("Machine Learning Research Scientist")


@pytest.mark.parametrize("rel", ["src/autonomous/job_monitor.py",
                                 "src/scrapers/getonbrd_jobs.py",
                                 "src/search/serpapi_jobs_ingest.py"])
def test_sources_search_for_new_lanes(rel):
    text = (ROOT / rel).read_text(encoding="utf-8").lower()
    assert "chief ai officer" in text
    assert "ai product manager" in text


def _load_feedback_sync():
    path = ROOT / "scripts" / "judge_feedback_sync.py"
    spec = importlib.util.spec_from_file_location("judge_feedback_sync_t", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_feedback_strips_cover_letter_template():
    mod = _load_feedback_sync()
    # Verbatim shape of the bot note that polluted 10 of 12 negatives in production.
    bot_only = ("COVER LETTER — drafted against this posting (openai). Read it, then paste. "
                "--- I am applying for the AI Solutions Architect position at HireHawk. "
                "I have extensive experience shipping live AI systems.")
    assert mod._rejection_reason([{"body": bot_only}], "AI Solutions Architect") == ""
    hers = "Not a fit: they want a Java engineer who writes code by hand all day."
    assert mod._rejection_reason([{"body": hers}], "AI Engineer").startswith("her reason")
