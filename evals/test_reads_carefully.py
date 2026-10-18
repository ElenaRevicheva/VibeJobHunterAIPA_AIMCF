"""VJH reads postings carefully and keeps her full notes — 18 Oct 2026. Offline: no network, no model, $0.

Elena, 17 Oct: "Most important is that VJH reads carefully and thoughtfully job descriptions themselves
because manual coding requirements may be wired practically everywhere."

Replayed on the 12-17 Oct production logs: of 27 BORDERLINE Telegram alerts, 13 came from code overruling
the judge's own "no" and 15 were judged on Google's ~150-char snippet (19 had one or both). Niuro Forward
Deployed Engineer ("5+ years in software or integration engineering", "travel to the US") passed the gate,
the judge vetoed it correctly, and code overruled the veto. Her two notes that day were cut at 160 chars,
before the evidence she wrote down.

F1  an overruled verdict is never "the judge says yes" — no alert
F2  only a posting that was READ is judged for the alert
F3  a travel / on-site veto stands when the posting states it (and only then)
F4  "N+ years in software (or X) engineering" is a coding demand for the gate
    her full note is kept, her lessons read her verdict only, and the judge prompt stays bounded
"""
import importlib.util
import logging
from pathlib import Path

import pytest

import src.search.serpapi_jobs_ingest as door
from src.core import llm_judge
from src.core.fit_gate import iron_clad_fit

ROOT = Path(__file__).resolve().parents[1]


def _load_sync(name="judge_feedback_sync_rc"):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "judge_feedback_sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── F1 — the alert never counts code's "yes" as the judge's ─────────────────────────────────────────
@pytest.mark.parametrize("why", [
    "criterion-2 veto overruled — LATAM-open listing (2 The listing does not explicitly state that it is op)",
    "criterion-2 veto overruled — US time-zone overlap fits UTC-5 (2 Requires Pacific hours overlap)",
    "criterion-6 veto overruled — listing states no pay (6 Pay below her floor.)",
])
def test_an_overruled_veto_is_not_a_borderline(monkeypatch, why):
    monkeypatch.setattr(llm_judge, "judge_fit", lambda *a, **k: (True, why))
    assert door._borderline_check("Senior AI-Native Engineering Lead", "", "Remote - LATAM", "x" * 900) == (False, "")


def test_the_judges_own_yes_is_still_a_borderline(monkeypatch):
    # Scale Army / WON: posting read, the judge approved on its own — the case the alert was built for.
    monkeypatch.setattr(llm_judge, "judge_fit", lambda *a, **k: (True, "All criteria met; LATAM-open AI workflow role."))
    assert door._borderline_check("AI Workflow Specialist", "Scale Army", "Remote", "x" * 900) == \
        (True, "All criteria met; LATAM-open AI workflow role.")
    monkeypatch.setattr(llm_judge, "judge_fit", lambda *a, **k: (True, "JUDGE UNAVAILABLE: no provider"))
    assert door._borderline_check("AI Workflow Specialist", "Scale Army", "Remote", "x" * 900) == (False, "")
    monkeypatch.setattr(llm_judge, "judge_fit", lambda *a, **k: (False, "3 Not in her lanes."))
    assert door._borderline_check("AI Workflow Specialist", "Scale Army", "Remote", "x" * 900) == (False, "")


# ── F1 + F2 end to end through ingest_once (the real _borderline_check, the judge stubbed) ──────────
@pytest.fixture
def door_run(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(door, "STATE_FILE", tmp_path / "seen.json")
    monkeypatch.setattr(door, "JOBS_QUERIES", ["q"])
    monkeypatch.setattr(door, "_GATE_AVAILABLE", False)
    monkeypatch.setattr(door, "_read_full_posting", lambda t, u, d: (d, False))
    monkeypatch.setattr(door, "_salary_verdict", lambda *a, **k: ("unknown", None, ""))
    monkeypatch.setattr(door, "record_judged_posting", lambda *a, **k: False)
    monkeypatch.setattr(door, "iron_clad_fit", lambda t, l, d: False)          # the gate said NO
    monkeypatch.setattr(door, "push_crm_event", lambda payload: (200, {"ok": True, "hubspot": {"dealId": "1"}}))
    monkeypatch.setattr(door.time, "sleep", lambda s: None)
    caplog.set_level(logging.INFO, logger=door.log.name)
    calls, alerts = [], []
    monkeypatch.setattr(door, "_borderline_alert", lambda *a, **k: alerts.append(a[0]))

    def run(desc, judge_says):
        def judge(*a, **k):
            calls.append(a[0])
            return judge_says
        monkeypatch.setattr(llm_judge, "judge_fit", judge)
        monkeypatch.setattr(door, "fetch_google_jobs", lambda q: [{
            "title": "Mission.dev hiring AI Solutions Engineer in Latin America", "company_name": "Mission",
            "location": "", "description": desc, "related_links": [{"link": "https://jobs.example/1"}]}])
        door.ingest_once()
        return caplog.text
    return run, calls, alerts


def test_a_snippet_is_never_judged_or_alerted(door_run):
    run, calls, alerts = door_run
    snippet = "Mission.dev is hiring an AI Solutions Engineer in Latin America. Remote. Apply now."   # ~85 chars
    text = run(snippet, (True, "All criteria met."))
    assert calls == [] and alerts == []                                  # no judge call, no Telegram
    assert f"no BORDERLINE check — posting not read ({len(snippet)} chars)" in text


def test_a_read_posting_with_an_overruled_veto_is_judged_but_not_alerted(door_run):
    run, calls, alerts = door_run
    text = run("Full posting. " * 60, (True, "criterion-2 veto overruled — LATAM-open listing (2 not open to Panama)"))
    assert len(calls) == 1 and alerts == []
    assert "no BORDERLINE alert — the judge said no, code overruled it" in text
    assert "BORDERLINE (gate NO / judge YES)" not in text


def test_a_read_posting_the_judge_itself_approves_is_alerted(door_run):
    run, calls, alerts = door_run
    text = run("Full posting. " * 60, (True, "All criteria met."))
    assert len(calls) == 1 and alerts == ["Mission.dev hiring AI Solutions Engineer in Latin America"]
    assert "BORDERLINE (gate NO / judge YES) -> alerting" in text


# ── F3 — the judge's travel / on-site veto stands when the posting says so ──────────────────────────
NIURO_FDE = ("Remote from any country in Latin America. Lead platform integrations inside customer environments "
             "and build production agentic AI systems. You bring 5+ years in software or integration engineering. "
             "Able to travel to the US for up to two weeks (B1/B2 visa).")
TRAVEL_VETO = "2. The listing requires travel to the US, which is incompatible with her remote work."


def test_travel_veto_stands_only_with_posting_evidence():
    title, loc = "Senior Forward Deployed Engineer", "Remote - LATAM"
    assert llm_judge.latam_veto_is_wrong(title, loc, NIURO_FDE)                       # old call: overruled
    assert not llm_judge.latam_veto_is_wrong(title, loc, NIURO_FDE, TRAVEL_VETO)      # reason + posting: stands
    no_travel = NIURO_FDE.replace(" Able to travel to the US for up to two weeks (B1/B2 visa).", "")
    assert llm_judge.latam_veto_is_wrong(title, loc, no_travel, TRAVEL_VETO)          # posting silent: overruled
    # A reason that is not about travel/office is untouched even when the posting mentions travel.
    assert llm_judge.latam_veto_is_wrong(title, loc, NIURO_FDE, "2 The listing does not explicitly state Panama.")
    # Word starts only: "comparison site" / "within office hours" are not on-site / in-office.
    assert llm_judge.latam_veto_is_wrong(title, loc, no_travel + " Build a comparison site within office hours.",
                                         "2 The role is on-site, in-office.")


def test_judge_fit_keeps_the_veto_with_a_stubbed_model(monkeypatch):
    monkeypatch.setattr(llm_judge, "_key", lambda name: "")
    monkeypatch.setattr(llm_judge, "_feedback_block", lambda: "")
    monkeypatch.setattr(llm_judge, "_call_llm", lambda p: ('{"fit": false, "reason": "%s"}' % TRAVEL_VETO, []))
    assert llm_judge.judge_fit("Senior Forward Deployed Engineer", "Niuro", "Remote - LATAM", NIURO_FDE) == \
        (False, TRAVEL_VETO)


# ── F4 — "5+ years in software or integration engineering" is a hand-coding demand ──────────────────
def test_years_in_software_engineering_is_heavy_coding():
    title, loc = "Senior Forward Deployed Engineer", "Remote - LATAM"
    base = ("Fully remote from anywhere in Latin America. Build agentic AI systems and automation with LLM tools "
            "inside customer environments.")
    assert iron_clad_fit(title, loc, base)                                               # control: passes
    for demand in ("You bring 5+ years in software or integration engineering.",
                   "5 years of experience in software engineering.",
                   "3+ years in software development."):
        assert not iron_clad_fit(title, loc, f"{base} {demand}"), demand
    # Not a coding demand: business years in a software company.
    assert iron_clad_fit(title, loc, f"{base} 5 years in software sales and business development.")
    assert iron_clad_fit(title, loc, f"{base} 7 years in software product management.")


def test_f4_is_broader_than_the_niuro_wording_pending_elenas_yes():
    """Pinned so a change is a decision, not an accident (review, 18 Oct): the pattern parks ANY "N years (of
    experience) in software development", even 2+ and even with "or technical consulting" after it — in-lane
    titles included. Both passed at HEAD. If Elena says no, narrow fit_gate to "in software or <word> engineering"
    and flip these two asserts."""
    base = ("Fully remote from anywhere in Latin America. Build agentic AI systems and automation with LLM tools "
            "inside customer environments.")
    assert iron_clad_fit("AI Solutions Architect", "Remote - LATAM", base)
    assert not iron_clad_fit("AI Solutions Architect", "Remote - LATAM",
                             f"{base} 5+ years of experience in software development or technical consulting.")
    assert not iron_clad_fit("AI Automation Specialist", "Remote - LATAM",
                             f"{base} 2+ years in software development or no-code automation.")


def test_a_niuro_fde_shaped_posting_is_parked_for_the_years_line():
    title = "Senior Forward Deployed Engineer at Niuro • Santiago"
    years = " You bring 5+ years in software or integration engineering."
    assert years in NIURO_FDE
    assert iron_clad_fit(title, "", NIURO_FDE.replace(years, ""))       # without the line: the gate passed it
    assert not iron_clad_fit(title, "", NIURO_FDE)                      # with it: parked


# ── her full note is kept; her lessons read her verdict; the judge prompt stays bounded ─────────────
NOTE = ("look at the requirements - Niuro is hiring a Senior Forward Deployed Engineer for an enterprise AI platform "
        "company. " + "You will map customer workflows into platform configurations and integrations. " * 10
        + "You bring 5+ years in software or integration engineering. "
        + "You will guide deployments and data migrations. " * 6
        + "Able to travel to the US for up to two weeks (B1/B2 visa).")


def test_a_long_note_is_kept_whole():
    s = _load_sync()
    assert 1100 < len(NOTE) < s._REASON_MAX
    why = s._rejection_reason([{"body": NOTE}], "AI Experience Engineer")
    assert why.startswith("her reason: look at the requirements")
    assert "5+ years in software or integration engineering" in why and "travel to the US" in why
    s._REASON_MAX = 160                                  # what 17 Oct stored: the evidence was cut off
    cut = s._rejection_reason([{"body": NOTE}], "AI Experience Engineer")
    assert "years in software" not in cut and "travel" not in cut


def test_the_judge_prompt_shows_a_bounded_slice_and_old_reasons_unchanged():
    s = _load_sync()
    why = s._rejection_reason([{"body": NOTE}], "AI Experience Engineer")
    shown = s._prompt_why(why)
    assert len(shown) <= s._PROMPT_REASON_MAX + 1 and shown.endswith("…")
    # The screenshot reading is never cut, only her words are.
    shot = "Remote (US, CA, UK); the post is closed."
    with_shot = s._prompt_why(f"{why}; her screenshot shows: {shot}")
    assert with_shot.endswith(f"…; her screenshot shows: {shot}")
    # A reason read at the old limit — every line the judge saw before today — is byte-identical.
    for old in ("her reason: remote other locations, not LATAM",
                "her reason: " + "x" * 160 + "; her screenshot shows: " + "y" * 240,
                "her screenshot shows: " + "z" * 900):
        assert s._prompt_why(old) == old
    base = {"company": "c", "prefix": "HIRING-VJH-LEAD", "stage": "closedlost",
            "first_decided": "2026-10-17T11:41:00Z", "applied": None}
    ledger = {str(i): dict(base, title=f"AI Automation Manager {i}", modified=f"2026-10-{17 - i:02d}T00:00:00Z",
                           why=why) for i in range(12)}
    _, negatives = s._pick_examples(ledger)
    assert len(negatives) == 12
    assert sum(len(n) for n in negatives) <= 12 * (len("AI Automation Manager 11 — ") + s._PROMPT_REASON_MAX + 1)


def test_lessons_and_rules_read_only_her_verdict():
    """Measured on the real ledger: the full pasted text added a false 'closed' and 'pay' lesson."""
    s = _load_sync()
    L = lambda why: {"t": {"title": "AI Solution Architect @ Addepto", "company": "Addepto", "prefix": "HIRING-VJH-LEAD",
                           "stage": "closedlost", "modified": "2026-10-08T15:52:08Z",
                           "first_decided": "2026-10-08T15:52:08Z", "why": why, "applied": None}}
    verdict = "her reason: look This is Addepto — AI Solution Architect, posted October 5, 2026. It's closer to "
    pasted = ("your technical AI systems experience. " * 4 + "Full-time; no salary disclosed. Applications closed "
              "for the first round. I am not an expert in kubernetes.")
    short_lessons, short_rules = s._build_lessons_and_rules(L(verdict.strip()))
    long_lessons, long_rules = s._build_lessons_and_rules(L(verdict + pasted))
    assert long_rules == short_rules and "tools_not_hers" not in long_rules
    assert long_lessons == short_lessons
    # Proof the cap is what protects her rules: read in full, the pasted text would teach a tool veto
    # ("kubernetes") and a "closed" and a "pay" lesson she never gave.
    s._LESSON_REASON_MAX = 10 ** 6
    raw_lessons, raw_rules = s._build_lessons_and_rules(L(verdict + pasted))
    assert raw_rules["tools_not_hers"]["tools"] == ["kubernetes"]
    assert {"closed", "pay"} <= set(raw_lessons["kinds"])


def test_a_reason_cut_at_160_is_read_again_once(monkeypatch):
    s = _load_sync()
    fetched = []

    def notes(key, ids):
        fetched.append(list(ids))
        return {d: [{"body": NOTE, "attachments": []}] for d in ids}
    monkeypatch.setattr(s, "_fetch_notes_batch", notes)
    cut_why = "the posting says: " + NOTE[:160].strip()                  # what the 17 Oct sync stored
    old = {"9": {"title": "Senior Forward Deployed Engineer @ Niuro", "company": "Niuro", "prefix": "HIRING-VJH-LEAD",
                 "stage": "closedlost", "modified": "2026-10-17T11:41:57Z", "first_decided": "2026-10-17T11:41:57Z",
                 "why": cut_why, "applied": None, "url": ""},
           "8": {"title": "HQ AI Enablement Lead @ Everfield", "company": "Everfield", "prefix": "HIRING-VJH-LEAD",
                 "stage": "closedlost", "modified": "2026-10-01T00:00:00Z", "first_decided": "2026-10-01T00:00:00Z",
                 "why": "her reason: remote other locations, not LATAM", "applied": None, "url": ""}}
    deals = [{"id": d, "properties": {"dealname": f"[HIRING-VJH-LEAD] {e['title']}", "dealstage": "closedlost",
                                      "hs_lastmodifieddate": e["modified"], "description": ""}} for d, e in old.items()]
    ledger, refreshed, _ = s._update_ledger("key", deals, old, {})
    assert fetched == [["9"]] and refreshed == 1                     # only the cut one, not the short one
    assert "travel to the US" in ledger["9"]["why"] and ledger["9"]["reason_max"] == s._REASON_MAX
    assert ledger["8"]["why"] == "her reason: remote other locations, not LATAM"
    ledger2, refreshed2, _ = s._update_ledger("key", deals, ledger, {})
    assert refreshed2 == 0 and fetched == [["9"]]                    # one-time: the stamp stops a re-read


def test_a_failed_notes_fetch_keeps_the_cached_reason(monkeypatch):
    """_fetch_notes_batch returns [] for every deal on a HubSpot error. A cached reason came from a note, so an empty
    list is a failed fetch: the reason is kept, no stamp is written, and the next run reads it again."""
    s = _load_sync()
    cut_why = "her reason: " + NOTE[:160].strip()
    old = {"9": {"title": "Senior Forward Deployed Engineer @ Niuro", "company": "Niuro", "prefix": "HIRING-VJH-LEAD",
                 "stage": "closedlost", "modified": "2026-09-01T00:00:00Z", "first_decided": "2026-09-01T00:00:00Z",
                 "why": cut_why, "applied": None, "url": ""}}
    deals = [{"id": "9", "properties": {"dealname": "[HIRING-VJH-LEAD] Senior Forward Deployed Engineer @ Niuro",
                                        "dealstage": "closedlost", "hs_lastmodifieddate": "2026-09-01T00:00:00Z",
                                        "description": ""}}]
    monkeypatch.setattr(s, "_fetch_notes_batch", lambda key, ids: {d: [] for d in ids})        # HubSpot down
    ledger, _, _ = s._update_ledger("key", deals, old, {})
    assert ledger["9"]["why"] == cut_why and "reason_max" not in ledger["9"]
    monkeypatch.setattr(s, "_fetch_notes_batch", lambda key, ids: {d: [{"body": NOTE, "attachments": []}] for d in ids})
    ledger, refreshed, _ = s._update_ledger("key", deals, ledger, {})                          # HubSpot back
    assert refreshed == 1 and "travel to the US" in ledger["9"]["why"] and ledger["9"]["reason_max"] == s._REASON_MAX
    # A NEW rejection with no notes is unchanged: it is recorded with no reason, as before.
    new = [dict(deals[0], id="7")]
    monkeypatch.setattr(s, "_fetch_notes_batch", lambda key, ids: {d: [] for d in ids})
    ledger, _, _ = s._update_ledger("key", new, {}, {})
    assert ledger["7"]["why"] == ""


def test_a_pasted_posting_line_keeps_the_old_160_in_the_prompt():
    """'the posting says:' is pasted text, not her words; cto-aipa queue-feedback.ts matches that line whole."""
    s = _load_sync()
    pasted = s._rejection_reason([{"body": "Senior Forward Deployed Engineer at Niuro. " + NOTE}],
                                 "Senior Forward Deployed Engineer at Niuro")
    assert pasted.startswith("the posting says: ") and len(pasted) > 600
    shown = s._prompt_why(pasted)
    assert shown == pasted[:len("the posting says: ") + 160].rstrip(" ;") + "…"
    shot = "Remote (US, CA, UK)."
    assert s._prompt_why(f"{pasted}; her screenshot shows: {shot}") == f"{shown}; her screenshot shows: {shot}"
    # Every pasted line stored at the old limit (with or without a screenshot reading) is byte-identical.
    for old in ("the posting says: " + "p" * 160, "the posting says: " + "p" * 160 + "; her screenshot shows: x"):
        assert s._prompt_why(old) == old
