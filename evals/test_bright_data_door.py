"""The Bright Data door (src/search/serpapi_jobs_ingest.py) — 29 Sep and 6 Oct 2026 changes. Offline.

Measured before: of 98 jobs this door parked 27-29 Sep, read in full, 77 were off-lane and 17 failed
the gate (mostly US-only); every in-lane one had been judged on a ~180-char Google snippet.

6 Oct (docs/oracle/2026-10-06_vjh_no_delivery_diagnosis.md in cto-aipa): 26 "I Act TODAY" lines since
29 Sep made 2 real deals — 12 died at cto-aipa for a blank company (Lever URLs: DEUNA, Airtm), 12 only
added a note to an existing deal, and the ingest never read the answer.
"""
import json
import logging
import re
import sys
import types
from pathlib import Path

import pytest
import requests

import src.search.serpapi_jobs_ingest as door


def test_every_paid_search_targets_where_she_can_work():
    assert len(door.JOBS_QUERIES) == 18                       # edited in place: same count, same bill
    for q in door.JOBS_QUERIES:
        assert "latin america" in q or "worldwide" in q, q


class _Reader:
    def __init__(self, result=("FULL POSTING TEXT " * 100, False), boom=False):
        self.calls, self.result, self.boom = [], result, boom

    def __call__(self, url, desc):
        self.calls.append(url)
        if self.boom:
            raise RuntimeError("network down")
        return self.result


def test_on_lane_title_reads_the_posting(monkeypatch):
    r = _Reader()
    monkeypatch.setattr(door, "_enrich", r)
    text, closed = door._read_full_posting("AI Automation Specialist", "https://jobs.example.com/1", "snippet")
    assert r.calls and text.startswith("FULL POSTING") and closed is False


def test_off_lane_title_costs_no_fetch(monkeypatch):
    r = _Reader()
    monkeypatch.setattr(door, "_enrich", r)
    assert door._read_full_posting("Senior QA Automation Engineer", "https://x/1", "snippet") == ("snippet", False)
    assert r.calls == []


def test_closed_posting_is_reported(monkeypatch):
    monkeypatch.setattr(door, "_enrich", _Reader(result=("snippet", True)))
    assert door._read_full_posting("AI Automation Specialist", "https://x/1", "snippet")[1] is True


def test_any_failure_keeps_the_old_behaviour(monkeypatch):
    monkeypatch.setattr(door, "_enrich", _Reader(boom=True))
    assert door._read_full_posting("AI Automation Specialist", "https://x/1", "snippet") == ("snippet", False)
    monkeypatch.setattr(door, "_enrich", None)
    assert door._read_full_posting("AI Automation Specialist", "https://x/1", "snippet") == ("snippet", False)
    r = _Reader()
    monkeypatch.setattr(door, "_enrich", r)
    long_desc = "x" * 1600                                    # already a real posting → no fetch
    assert door._read_full_posting("AI Automation Specialist", "https://x/1", long_desc) == (long_desc, False)
    assert r.calls == []


def test_the_posting_is_read_before_the_gate():
    src = Path(door.__file__).read_text(encoding="utf-8")
    body = src[src.index("def ingest_once"):]
    assert body.index("_read_full_posting(title, job_url, desc_full)") < body.index("iron_clad_fit(title, location, desc_full)")


# ─── 6 Oct 2026 — 1. a company name for every job that names one, and never a generic word ───

@pytest.mark.parametrize("title,link,expected", [
    # The two real losses: Lever's jobs.lever.co/<company>/<id>; the subdomain "jobs" was all it read.
    ("DEUNA - Product Head of AI",
     "https://jobs.lever.co/deuna/ec4f69ac-f28e-496e-b925-45d21c53e467", {"Deuna", "DEUNA"}),
    ("Airtm - AI Automation Engineer", "https://jobs.lever.co/airtm/5c1e0a7e-1111-2222-3333-444455556666",
     {"Airtm"}),
    ("AI Lead", "https://jobs.eu.lever.co/acme-co/1", {"Acme Co"}),
    # URL names nothing -> Google's "<Company> - <Title>", "<Title> @ <Company>"
    ("DEUNA - Product Head of AI", "", {"DEUNA"}),
    ("DEUNA - Product Head of AI", "https://www.example.com/jobs/123", {"DEUNA"}),
    ("Ubiminds - AI Solutions Lead (579)", "https://example.com/p/1", {"Ubiminds"}),
    ("Empirical - Fractional CTO (Remote - US or LATAM)", "https://example.com/p/1", {"Empirical"}),
    ("Marketing Operations Manager - AI Collaborator, Inc.", "https://example.com/p/1",
     {"AI Collaborator, Inc."}),
    ("Lead AI Engineer (LLM & Agents) @ Trust Wallet", "https://example.com/p/1", {"Trust Wallet"}),
    # 6 Oct review: the '@' form takes a lowercase name too (a real title from Oracle's log).
    ("Senior Product Manager - Core Experience @ n8n", "https://example.com/p/1", {"n8n"}),
    # Unchanged paths: what already resolved keeps the SAME name (it is in the seen-hash + deal name).
    ("Job Application for AI Engineer at Clara", "https://job-boards.greenhouse.io/clara/jobs/1", {"Clara"}),
    ("Apply to Remote AI Automation Engineer at HireLATAM", "https://recruiterflow.com/hirelatam/jobs/1717",
     {"HireLATAM"}),
    ("Staff Product Manager - Conversational AI @ Addi", "https://jobs.ashbyhq.com/addi/1", {"Addi"}),
    ("AI Engineer", "https://job-boards.greenhouse.io/some-company/jobs/1", {"Some Company"}),
    # Google-truncated "at Robots ..." is not a name -> the URL's slug wins.
    ("Job Application for Senior Cloud Architect at Robots ...",
     "https://job-boards.greenhouse.io/robotsandpencils/jobs/1", {"Robotsandpencils"}),
    ("Business Systems Automation Specialist", "https://jobs.ashbyhq.com/Scale%20Army%20Careers/abc",
     {"Scale Army Careers"}),
    ("AI Lead", "https://boards.greenhouse.io/embed/job_app?for=acme&token=1", {"Acme"}),
    ("AI Lead", "https://wellfound.com/company/acme-ai/jobs/123-ai-lead", {"Acme Ai"}),
])
def test_company_is_found(title, link, expected):
    assert door._extract_company(title, link) in expected


@pytest.mark.parametrize("title,link", [
    ("AI Engineer at Remote", "https://jobs.lever.co/careers/1"),
    ("Product Lead", "https://jobs.lever.co/jobs/"),
    ("Product Lead", "https://jobs.lever.co/apply/1"),
    ("Product Lead", "https://job-boards.greenhouse.io/remote/jobs/1"),
    ("AI Automation Engineer - Remote Work", "https://bebee.com/x/1"),
    ("AI Strategist - Remote, Medellín", "https://example.com/p/1"),
    ("Remote Technical Account Manager Jobs", "https://www.workingnomads.com/x"),
    ("APPLY - Senior Project Manager", ""),
    ("25888 Remote Startup Jobs (October 2026) - Apply with AI", "https://example.com/"),
    # 6 Oct review — real blank-company titles from Oracle's serpapi-jobs log that the first version
    # turned into "companies": a place / term / category after the dash or pipe, a Google-truncated
    # tail, and "Leader" not reading as a role. Each would have become a HubSpot company + a letter.
    ("Remote AI & Automation Account Manager | United States", "https://example.com/p/1"),
    ("Solutions Architect (AI & Automation) – Contract", "https://example.com/p/1"),
    ("Executive Operations & Finance Specialist | AI & Automation", "https://example.com/p/1"),
    ("Sr. Software Engineer - AI Platforms & Automation", "https://example.com/p/1"),
    ("AI Solutions Architect jobs — 825 recorded open listings", "https://example.com/p/1"),
    ("Police Chief Simulator - Part 1 - The Beginning (FULL GAME)", "https://example.com/p/1"),
    ("Kansas City Chiefs vs Miami Dolphins - NFL Week 3", "https://example.com/p/1"),
    ("Consulting Head of Engineering (Part Time) - Hardware ...", "https://example.com/p/1"),
    ("Part-Time Compliance Officer & MLRO Support — Web3 ...", "https://example.com/p/1"),
    ("Impact Leader - Solution Architect /Enterprise Delivery", "https://example.com/p/1"),
    # Google-truncated candidates are never a name (the first is a real log title; only the '...'
    # rule stops it), and the part after " | " never leaks into one.
    ("Technology Leadership for Madrid ... - Fractional CTO Madrid", "https://example.com/p/1"),
    ("Lead AI Engineer (LLM & Agents) @ Trust Wal...", "https://example.com/p/1"),
    ("Founding Engineer @ Neuromorphic La…", "https://example.com/p/1"),
    ("Solutions Architect - AI | Element Solutions Inc", "https://example.com/p/1"),
    # A lowercase '@' name must be one token like "n8n" — this is a real log title, not an employer.
    ("AI Solutions Engineer @ fast-growing, mission-driven startup", "https://example.com/p/1"),
])
def test_never_a_generic_word_as_company(title, link):
    assert door._extract_company(title, link) == ""


@pytest.mark.parametrize("word", ["jobs", "careers", "remote", "apply", "Jobs", "Remote Jobs"])
def test_generic_words_are_not_companies(word):
    assert door._is_generic_company(word)
    assert door._extract_company(f"AI Lead at {word.title()}", "") == ""


def test_a_company_field_on_the_result_is_used():
    assert door._extract_company("AI Lead", "https://example.com/1", hint="Acme Labs") == "Acme Labs"
    assert door._extract_company("AI Lead", "https://example.com/1", hint="Jobs") == ""


# ─── 3. client intent: whole words only ───

@pytest.mark.parametrize("title", ["Director of AI", "Director, Product", "October hiring: AI Lead",
                                   "Head of Airline Operations", "Doctor of Operations"])
def test_cto_does_not_match_inside_words(title):
    assert not door._client_intent(title)


@pytest.mark.parametrize("title", ["Fractional CTO", "CTO / Co-founder", "Head of AI", "Chief AI Officer",
                                   "Interim CTO (Remote)", "VP Engineering", "Technical Co-Founder"])
def test_real_cto_intent_still_matches(title):
    assert door._client_intent(title)


# ─── 4. the seen-list drops the OLDEST, not whatever hash order puts last ───

def test_seen_cache_keeps_the_newest(tmp_path, monkeypatch):
    monkeypatch.setattr(door, "STATE_FILE", tmp_path / "seen.json")
    seen = door.load_seen()
    assert seen == {}
    for i in range(door.SEEN_CAP + 5):
        door.mark_seen(seen, f"id{i}")
    door.mark_seen(seen, "id0")                 # still showing in Google -> moves to the newest end
    door.save_seen(seen)
    kept = json.loads((tmp_path / "seen.json").read_text())
    assert len(kept) == door.SEEN_CAP           # cap unchanged
    assert kept[-1] == "id0" and kept[-2] == f"id{door.SEEN_CAP + 4}"
    assert "id1" not in kept and "id5" not in kept and kept[0] == "id6"   # the 5 oldest went, id0 was kept
    assert list(door.load_seen()) == kept       # order survives the round trip


def test_seen_cache_reads_the_old_file_as_is(tmp_path, monkeypatch):
    f = tmp_path / "seen.json"
    f.write_text(json.dumps(["b", "a", "c"]))   # the pre-6-Oct format: a plain JSON list
    monkeypatch.setattr(door, "STATE_FILE", f)
    seen = door.load_seen()
    assert list(seen) == ["b", "a", "c"] and "a" in seen


# ─── 2. read the CRM answer ───

class _Resp:
    def __init__(self, status, body=None, text=None):
        self.status_code = status
        self.text = text if text is not None else (json.dumps(body) if body is not None else "")
        self.ok = 200 <= status < 400

    def json(self):
        return json.loads(self.text)


def _post_returning(monkeypatch, *answers):
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        a = answers[min(len(calls), len(answers)) - 1]
        if isinstance(a, BaseException):
            raise a
        return a
    monkeypatch.setattr(door.requests, "post", fake_post)
    return calls


def test_push_returns_status_and_answer(monkeypatch):
    monkeypatch.setattr(door, "OUTREACH_SECRET", "s")
    _post_returning(monkeypatch, _Resp(400, {"error": "jobTitle and company required for hiring pipeline"}))
    status, data = door.push_crm_event({"pipeline": "hiring"})
    assert status == 400
    assert door._crm_outcome(status, data) == {
        "kind": "rejected", "msg": "HTTP 400: jobTitle and company required for hiring pipeline"}


def test_push_timeout_is_unknown_not_success(monkeypatch):
    monkeypatch.setattr(door, "OUTREACH_SECRET", "s")
    _post_returning(monkeypatch, requests.exceptions.ReadTimeout("read timed out"))
    status, data = door.push_crm_event({"pipeline": "hiring"})
    assert status == 0 and door._crm_outcome(status, data)["kind"] == "unknown"


def test_push_without_secret_is_unknown(monkeypatch):
    monkeypatch.setattr(door, "OUTREACH_SECRET", "")
    assert door._crm_outcome(*door.push_crm_event({}))["kind"] == "unknown"


def test_non_json_error_body_still_gives_a_message(monkeypatch):
    monkeypatch.setattr(door, "OUTREACH_SECRET", "s")
    _post_returning(monkeypatch, _Resp(502, text="<html>Bad Gateway</html>"))
    out = door._crm_outcome(*door.push_crm_event({}))
    assert out["kind"] == "rejected" and out["msg"].startswith("HTTP 502: <html>Bad Gateway")


@pytest.mark.parametrize("body,kind", [
    # today's server: no duplicate field -> a 2xx counts as new, exactly as before
    ({"ok": True, "pipeline": "hiring", "hubspot": {"contactId": None, "companyId": "1", "dealId": "9"}}, "new"),
    # the parallel cto-aipa change
    ({"ok": True, "duplicate": True, "decided": True, "stage": "closedlost", "dealId": "7"}, "duplicate"),
    ({"ok": True, "duplicate": False, "dealId": "8"}, "new"),
    ({"ok": True, "hubspot": {"dealId": "7", "duplicate": True, "stage": "qualifiedtobuy"}}, "duplicate"),
    # HubSpot wrote nothing — not a deal, so not "I Act TODAY"
    ({"ok": True, "pipeline": "hiring", "hubspot": None}, "unknown"),
    # 6 Oct review — a 2xx that names no deal is not a deal: a proxy's HTML page, an empty body, and
    # cto-aipa's own 200 when HubSpot refused the create (createDeal → null, duplicate:false).
    ({"_raw": "<html>nginx default</html>"}, "unknown"),
    ({}, "unknown"),
    ({"ok": True, "hubspot": {"dealId": None}}, "unknown"),
    ({"ok": True, "pipeline": "hiring", "hubspot": {"contactId": None, "companyId": None, "dealId": None},
      "duplicate": False, "dealId": None}, "unknown"),
    ({"hubspot": {"dealId": "9"}}, "unknown"),                 # no ok:true
])
def test_crm_outcome_kinds(body, kind):
    assert door._crm_outcome(200, body)["kind"] == kind


def test_a_bodyless_2xx_is_unknown():
    out = door._crm_outcome(204, None)
    assert out["kind"] == "unknown" and out["msg"].startswith("HTTP 204 but no deal id")


def test_new_carries_the_deal_id():
    assert door._crm_outcome(200, {"ok": True, "hubspot": {"dealId": "9"}}) == {"kind": "new", "dealId": "9"}
    assert door._crm_outcome(200, {"ok": True, "duplicate": False, "dealId": "8",
                                   "hubspot": {"dealId": "8"}}) == {"kind": "new", "dealId": "8"}


def test_duplicate_carries_stage_and_decided():
    out = door._crm_outcome(200, {"duplicate": True, "decided": True, "stage": "closedlost", "dealId": "7"})
    assert out["stage"] == "closedlost" and out["decided"] is True and out["dealId"] == "7"


# ─── 5. Bright Data: one retry on an empty / non-JSON 2xx or a read timeout ───

_BD_OK = {"organic": [{"title": "DEUNA - Product Head of AI",
                       "link": "https://jobs.lever.co/deuna/ec4f69ac-f28e-496e-b925-45d21c53e467",
                       "description": "Remote, LATAM"}]}


@pytest.fixture
def bd(monkeypatch):
    monkeypatch.setattr(door, "BRIGHTDATA_API_TOKEN", "t")
    monkeypatch.setattr(door, "BRIGHTDATA_ZONE", "z")
    sleeps = []
    monkeypatch.setattr(door.time, "sleep", sleeps.append)

    def install(*answers):
        calls = []

        def fake(url):
            calls.append(url)
            a = answers[min(len(calls), len(answers)) - 1]
            if isinstance(a, BaseException):
                raise a
            return a
        monkeypatch.setattr(door, "_bd_post", fake)
        return calls
    install.sleeps = sleeps
    return install


def test_bd_empty_body_is_retried_once(bd):
    calls = bd(_Resp(200, text=""), _Resp(200, _BD_OK))
    jobs = door.fetch_google_jobs("head of AI remote latin america startup")
    assert len(calls) == 2 and bd.sleeps == [door.BD_RETRY_SLEEP_S]
    assert jobs and jobs[0]["company_name"] in ("Deuna", "DEUNA")


def test_bd_read_timeout_is_retried_once(bd):
    calls = bd(requests.exceptions.ReadTimeout("Read timed out. (read timeout=45)"), _Resp(200, _BD_OK))
    assert len(door.fetch_google_jobs("q")) == 1 and len(calls) == 2


def test_bd_gives_up_after_one_retry(bd):
    calls = bd(_Resp(200, text="not json"), _Resp(200, text=""))
    assert door.fetch_google_jobs("q") == [] and len(calls) == 2


def test_bd_http_error_is_not_retried(bd):
    calls = bd(_Resp(500, text="boom"))
    assert door.fetch_google_jobs("q") == [] and len(calls) == 1 and bd.sleeps == []


def test_bd_cooldown_answer_waits_long_enough(bd):
    bd(_Resp(200, text="This query recently failed, try again after a minimum of 15 seconds"),
       _Resp(200, _BD_OK))
    door.fetch_google_jobs("q")
    assert bd.sleeps == [door.BD_COOLDOWN_S]


# ─── 2 + 3 end to end: what the ingest logs and pushes ───

@pytest.fixture
def ingest(monkeypatch, tmp_path, caplog):
    """ingest_once with every network / model call replaced. Yields (run, pushes)."""
    monkeypatch.setattr(door, "STATE_FILE", tmp_path / "seen.json")
    monkeypatch.setattr(door, "JOBS_QUERIES", ["q"])
    monkeypatch.setattr(door, "_GATE_AVAILABLE", False)
    monkeypatch.setattr(door, "_read_full_posting", lambda t, u, d: (d, False))
    monkeypatch.setattr(door, "_salary_verdict", lambda *a, **k: ("unknown", None, ""))
    monkeypatch.setattr(door, "record_judged_posting", lambda *a, **k: False)
    monkeypatch.setattr(door, "_borderline_check", lambda *a, **k: (False, ""))
    monkeypatch.setattr(door.time, "sleep", lambda s: None)
    monkeypatch.setitem(sys.modules, "src.core.learned_rules",
                        types.SimpleNamespace(learned_veto=lambda *a, **k: (False, "")))
    monkeypatch.setitem(sys.modules, "src.core.llm_judge",
                        types.SimpleNamespace(judge_fit=lambda *a, **k: (True, "fits")))
    caplog.set_level(logging.INFO, logger=door.log.name)
    pushes = []

    def run(jobs, answer=(200, {"ok": True, "hubspot": {"dealId": "1"}}), fit=True):
        monkeypatch.setattr(door, "fetch_google_jobs", lambda q: jobs)
        monkeypatch.setattr(door, "iron_clad_fit", lambda t, l, d: fit)

        def fake_push(payload):
            pushes.append(payload)
            return answer
        monkeypatch.setattr(door, "push_crm_event", fake_push)
        door.ingest_once()
        return caplog.text
    return run, pushes


def _job(title, company, url="https://jobs.lever.co/acme/1"):
    return {"title": title, "company_name": company, "location": "", "description": "Remote, LATAM",
            "related_links": [{"link": url}]}


def test_new_deal_is_i_act_today(ingest):
    run, pushes = ingest
    text = run([_job("Product Head of AI", "Deuna")])
    assert "IRON-CLAD FIT + judge OK -> I Act TODAY: Product Head of AI @ Deuna" in text
    assert [p["pipeline"] for p in pushes] == ["hiring", "client"]   # 'head of ai' = client intent too


def test_duplicate_is_not_i_act_today(ingest):
    run, pushes = ingest
    text = run([_job("AI Automation Engineer", "HireLATAM")],
               answer=(200, {"ok": True, "duplicate": True, "decided": True, "stage": "closedlost"}))
    assert "I Act TODAY" not in text
    assert "already in CRM (stage closedlost) — not new" in text
    assert [p["pipeline"] for p in pushes] == ["hiring"]


def test_rejected_push_says_so(ingest):
    run, _ = ingest
    text = run([_job("AI Automation Engineer", "Airtm")],
               answer=(400, {"error": "jobTitle and company required for hiring pipeline"}))
    assert "I Act TODAY" not in text
    assert "CRM REJECTED (HTTP 400: jobTitle and company required for hiring pipeline)" in text


def test_blank_company_is_never_pushed(ingest):
    run, pushes = ingest
    text = run([_job("Fractional CTO", "", url="https://example.com/p/1"),
                _job("Fractional CTO", "   ", url="https://example.com/p/2")])
    assert pushes == []
    assert text.count("skipped: no company") == 2 and "I Act TODAY" not in text
    assert "IRON-CLAD FIT + judge OK, skipped: no company: Fractional CTO (https://example.com/p/1)" in text


def test_blank_company_still_gets_the_borderline_alert(ingest, monkeypatch):
    # 6 Oct review: the Telegram alert needs no company and was the only way such a job reached
    # Elena ("Hire Overseas hiring Product Manager in Latin America" was alerted twice). The skip sits
    # after it, so the alert fires exactly as before; only the CRM pushes are skipped.
    run, pushes = ingest
    alerts = []
    monkeypatch.setattr(door, "_borderline_check", lambda *a, **k: (True, "x"))
    monkeypatch.setattr(door, "_borderline_alert", lambda *a, **k: alerts.append(a))
    text = run([_job("Hire Overseas hiring Product Manager in Latin America", "",
                     url="https://www.linkedin.com/jobs/view/1")], fit=False)
    assert len(alerts) == 1 and alerts[0][0] == "Hire Overseas hiring Product Manager in Latin America"
    assert pushes == []
    assert "parked, skipped: no company: Hire Overseas hiring Product Manager in Latin America" in text


def test_a_200_without_a_deal_id_is_not_i_act_today(ingest):
    # cto-aipa answers 200 ok:true even when HubSpot refused the create (dealId null).
    run, pushes = ingest
    text = run([_job("Fractional CTO", "Empirical")],
               answer=(200, {"ok": True, "pipeline": "hiring", "hubspot": {"dealId": None},
                             "duplicate": False, "dealId": None}))
    assert "I Act TODAY" not in text
    assert "CRM outcome UNKNOWN (HTTP 200 but no deal id" in text
    assert [p["pipeline"] for p in pushes] == ["hiring"]          # no client prospect off a non-deal


def test_parked_job_fires_no_client_prospect(ingest):
    run, pushes = ingest
    run([_job("Fractional CTO", "Empirical")], fit=False)
    assert [p["pipeline"] for p in pushes] == ["hiring"]
    assert pushes[0]["stage"] == "lead_parked"


def test_director_title_fires_no_client_prospect(ingest):
    run, pushes = ingest
    run([_job("Director of AI Operations", "Acme")])
    assert [p["pipeline"] for p in pushes] == ["hiring"]


def test_real_fractional_cto_still_becomes_a_client_prospect(ingest):
    run, pushes = ingest
    run([_job("Fractional CTO", "Empirical")])
    client = [p for p in pushes if p["pipeline"] == "client"]
    assert len(client) == 1
    assert client[0]["company"] == "Empirical" and client[0]["name"] == "Hiring manager @ Empirical"
    assert client[0]["urgency"] == 5


def test_a_job_seen_last_run_is_not_new(ingest):
    run, pushes = ingest
    job = _job("AI Implementation Lead", "Acme")
    run([job])
    n = len(pushes)
    run([job])
    assert len(pushes) == n


def test_paid_queries_carry_the_outlook_titles_and_keep_the_protected_ones():
    qs = door.JOBS_QUERIES
    for keep in ("AI chief of staff remote latin america", "AI product manager remote latin america",
                 "chief AI officer remote latin america startup", "head of AI remote latin america startup",
                 "creative technologist generative AI remote latin america",
                 "AI video producer remote latin america"):
        assert keep in qs, keep
    added = [q for q in qs if q.endswith("remote latin america") and any(
        t in q for t in ("implementation lead", "workflow architect", "agentic workflow designer",
                         "transformation lead", "generative AI product lead", "innovation lead",
                         "systems operator"))]
    assert len(added) == 4
    assert len(set(qs)) == len(qs) == 18
