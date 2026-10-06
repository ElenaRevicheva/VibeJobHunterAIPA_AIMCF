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
    # 2026-10-06: no lane may read as secondary (the Shortical "not her primary lanes" veto).
    assert "ALL of these lanes are EQUAL targets" in rendered
    assert "are her CORE lanes, not exceptions" not in rendered
    # 2026-10-06 (review): the executive-support lane Elena kept was still vetoed under
    # criterion 4 as "primarily administrative". Both halves of the fix must stay in the prompt.
    assert ("AI-qualified executive support is NOT generic administration: an\n"
            "   executive assistant or chief of staff whose listing asks for AI tools or automation "
            "(ChatGPT,\n   Claude, Zapier, Make, n8n, agents) is lane g, even when the role also "
            "covers inbox, calendar\n   and board materials. Never reject it as \"administrative\"."
            ) in llm_judge._PROMPT
    assert ("An executive or personal assistant whose listing asks the assistant to use or build "
            "AI tools or automations IS this lane, even when the role also covers inbox, calendar "
            "and travel.") in rendered


def test_criterion_4_lane_letter_points_at_executive_support():
    # Criterion 4 names the executive-support lane by LETTER ("is lane g"). A lane inserted
    # before it would silently point the judge at another lane; this fails first instead.
    assert "is lane g," in llm_judge._PROMPT
    assert "g) AI-QUALIFIED EXECUTIVE SUPPORT" in target_lanes.render_lane_names_for_prompt()
    assert "   g) AI-QUALIFIED EXECUTIVE SUPPORT — " in llm_judge._PROMPT


def test_scoring_prompt_uses_shared_lanes():
    from src.agents.job_matcher import JobMatcher
    src = inspect.getsource(JobMatcher._ai_deep_analysis)
    assert "render_lanes_for_prompt" in src
    assert "Staff/Principal/Lead engineer role" not in src
    # 2026-10-06: the +20 lane bullet hand-wrote the names and kept the dropped evaluation lane
    # while omitting creative AI. It now renders them from target_lanes, like the judge.
    assert "render_lane_names_for_prompt" in src
    assert "{lane_names}" in src
    assert "expert AI evaluation" not in src


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


# 2026-10-06 Professional Outlook p.7 ("Where I fit") — the 17 titles she publishes, copied as
# written and grouped as she groups them. Kept HERE, not imported from target_lanes, so deleting a
# title from the registry fails this test instead of silently agreeing with itself. Every title in
# the registry already runs through the career gate, iron_clad_fit and title_on_lane above.
OUTLOOK_TITLES = {
    "AI operations & implementation": (
        "AI Operations Lead", "AI Implementation Lead", "AI Automation Lead",
        "AI Workflow Architect", "AI Systems Operator", "Agentic Workflow Designer"),
    "AI product & transformation": (
        "AI Product & Automation Lead", "AI Transformation Lead", "AI Innovation Lead",
        "AI Adoption Lead", "Generative AI Product Lead", "AI Prototyping Lead"),
    "Creative technology": (
        "Creative Technologist — GenAI", "Generative AI Producer", "Creative AI Pipeline Builder",
        "GenAI Production Lead", "AI Innovation Producer"),
}
ALL_OUTLOOK_TITLES = [t for ts in OUTLOOK_TITLES.values() for t in ts]


def test_outlook_list_is_complete():
    assert len(ALL_OUTLOOK_TITLES) == 17


@pytest.mark.parametrize("title", ALL_OUTLOOK_TITLES)
def test_every_outlook_title_is_a_lane_title(title):
    assert title in TITLES, f"Professional Outlook title missing from target_lanes: {title}"


@pytest.mark.parametrize("title", OUTLOOK_TITLES["Creative technology"])
def test_outlook_creative_titles_sit_in_the_creative_lane(title):
    assert title in CREATIVE_TITLES, title


def test_expert_evaluation_lane_is_dropped():
    # Elena, 6 Oct 2026: dropped. The judge renders LANES, so gone here means gone there.
    assert not any("EVALUATION" in lane["name"] for lane in target_lanes.LANES)
    assert "EXPERT AI EVALUATION" not in llm_judge._PROMPT
    for gone in ("LLM Evaluator", "AI Red Team Specialist", "AI Tutor, Business & Product"):
        assert gone not in TITLES, gone
        assert gone not in llm_judge._PROMPT, gone
    # 2026-10-06 (review): removing the lane alone left the judge approving a $4,000/month eval
    # gig 3/3 without the feedback block. Criterion 4 now names those gigs.
    assert ("AI-model evaluation, rating, red-teaming, AI-training or AI-tutoring gigs whose core\n"
            "   work is grading or teaching a model (Elena dropped that lane)") in llm_judge._PROMPT


def test_creative_lane_letter_after_the_drop():
    # The judge cites lanes by letter ("3h - ..."); dropping the evaluation lane moved creative
    # from i to h. Nothing parses the letter — this pins what the log lines will now say.
    assert "   h) CREATIVE AI & GENERATIVE MEDIA SYSTEMS — " in llm_judge._PROMPT
    assert "i) " not in target_lanes.render_lane_names_for_prompt()


def test_outlook_fit_lines_are_her_words():
    assert target_lanes.OUTLOOK_NOT_MY_FIT == (
        "Roles whose core value is unaided coding, algorithm drills or live coding — "
        "or proving the work can be done without AI.")
    for step in ("business problem", "system design", "deployment", "metrics", "iteration"):
        assert step in target_lanes.OUTLOOK_GOOD_FIT


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
