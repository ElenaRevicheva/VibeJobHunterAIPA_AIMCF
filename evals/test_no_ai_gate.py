"""Elena's qualification test, enforced (2026-09-28).

"Could I perform this job exceptionally well with AIPA / Claude / Cursor as my operating
environment? If the employer says it must be done WITHOUT AI → reject immediately."

Every veto case below is otherwise a clean pass — a lane title, LATAM-open, AI work — so the
ONLY thing that can reject it is the stated ban. The keep cases are the false positives a
careless regex would make: "no AI experience required", "businesses without AI", and a request
to write the APPLICATION without AI (the form, not the job).
"""
import pytest

from src.core.fit_gate import iron_clad_fit, no_ai_allowed
from src.core import llm_judge

TITLE = "AI Automation Lead"
LOCATION = "Remote — Worldwide / LATAM"
BASE = ("Fully remote role, open to candidates anywhere in Latin America. You will design "
        "AI automation and agent workflows for founders. ")

BANS = [
    "All candidates complete a take-home coding assessment without the use of AI tools.",
    "AI tools are not permitted during the technical interview.",
    "Use of ChatGPT or Copilot is strictly prohibited in this role.",
    "You must be able to do this work without AI assistance.",
    "No AI coding assistants are allowed on the job.",
]

KEEPS = [
    "We are an AI-native team: you will use Claude and Cursor every day.",
    "No AI experience required — we will train you.",
    "Businesses without AI strategy come to us for help.",
    "Please write your application answers yourself, without the use of AI.",
    "AI tools are not prohibited; we encourage them.",
]


@pytest.mark.parametrize("sentence", BANS)
def test_stated_ban_on_ai_is_detected(sentence):
    assert no_ai_allowed(BASE + sentence), sentence


@pytest.mark.parametrize("sentence", BANS)
def test_stated_ban_on_ai_parks_an_otherwise_perfect_job(sentence):
    assert iron_clad_fit(TITLE, LOCATION, BASE), "control case must pass without the ban"
    assert not iron_clad_fit(TITLE, LOCATION, BASE + sentence), sentence


@pytest.mark.parametrize("sentence", KEEPS)
def test_not_a_ban(sentence):
    assert not no_ai_allowed(BASE + sentence), sentence
    assert iron_clad_fit(TITLE, LOCATION, BASE + sentence), sentence


def test_ai_native_counts_as_ai_work():
    # No other AI keyword in this text: "AI-native" alone must satisfy the AI-work check.
    desc = ("Fully remote, open to candidates anywhere in Latin America. We are an AI-native "
            "company and this lead owns our internal operations.")
    assert iron_clad_fit("Operations Lead, AI", LOCATION, desc)


def test_judge_prompt_carries_the_test():
    rendered = llm_judge._PROMPT.format(feedback="", title="x", company="y", location="z", desc="d")
    assert "ONLY these five" in rendered
    assert "AI tools may NOT be used in the work or in the hiring test" in rendered
    assert "ONE operating unit" in rendered
    assert "eighteen months" not in rendered      # a relative duration ages; the date does not
