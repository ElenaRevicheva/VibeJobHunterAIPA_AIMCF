"""The bot review door (src/langgraph_pipeline/crm_hub.py) resolves an aggregator copy to its origin, 26 Oct 2026.

Elena: "if VJH finds a job position presented by paid job aggregating, it will automatically head to its original
job board location, wire the original link inside a deal note with all profound kit automatically prepared
corresponding to original job source requirements." The Bright Data door did this since 24 Oct; the review door
(Tailscale via weworkremotely.com, Clara via remotefront.com, both in I Act TODAY) did not. Offline.
"""
import json

import pytest

import src.langgraph_pipeline.crm_hub as hub
import src.search.serpapi_jobs_ingest as door

WWR = "https://weworkremotely.com/remote-jobs/tailscale-analytics-engineer-data"
GH = "https://job-boards.greenhouse.io/tailscale/jobs/4721289005"


@pytest.fixture
def push(monkeypatch):
    """push_application_to_crm with the network replaced; yields the list of payloads sent."""
    sent = []

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"ok": true}'

    def urlopen(req, timeout=0):
        sent.append(json.loads(req.data.decode("utf-8")))
        return _Resp()
    monkeypatch.setattr(hub, "urlopen", urlopen)
    monkeypatch.setenv("OUTREACH_SECRET", "s")
    return sent


def test_an_aggregator_copy_is_pushed_with_its_origin(push, monkeypatch):
    monkeypatch.setattr(door, "_find_origin", lambda t, c: (GH, "Job Application for Analytics Engineer, Data at Tailscale"))
    assert hub.push_application_to_crm(job_title="Analytics Engineer, Data", company="Tailscale", job_url=WWR,
                                       source="vjh_review", notes="Score: 80")
    p = push[0]
    assert p["jobUrl"] == GH                                          # the deal carries the origin
    assert p["domain"] == "job-boards.greenhouse.io"
    assert "Origin posting: " + GH in p["notes"] and "weworkremotely.com" in p["notes"]
    assert p["notes"].startswith("Score: 80")                         # the caller's note is kept


def test_a_board_url_is_untouched_and_costs_no_search(push, monkeypatch):
    searched = []
    monkeypatch.setattr(door, "_find_origin", lambda t, c: searched.append(t))
    hub.push_application_to_crm(job_title="Analytics Engineer, Data", company="Tailscale", job_url=GH, notes="n")
    assert push[0]["jobUrl"] == GH and push[0]["notes"] == "n" and searched == []


def test_the_employers_own_site_is_untouched(push, monkeypatch):
    monkeypatch.setattr(door, "_find_origin", lambda t, c: (GH, "x"))
    hub.push_application_to_crm(job_title="TPM", company="Nuro", job_url="https://nuro.ai/careersitem?gh_jid=8279156", notes="n")
    assert push[0]["jobUrl"] == "https://nuro.ai/careersitem?gh_jid=8279156"


def test_no_origin_keeps_the_copy_and_says_so(push, monkeypatch):
    monkeypatch.setattr(door, "_find_origin", lambda t, c: None)
    hub.push_application_to_crm(job_title="AI Growth Automation Engineer", company="Clara",
                                job_url="https://www.remotefront.com/remote-jobs/clara-x", notes="n")
    assert push[0]["jobUrl"] == "https://www.remotefront.com/remote-jobs/clara-x"
    assert "Found on an aggregator (remotefront.com)" in push[0]["notes"]


def test_no_company_means_no_search(push, monkeypatch):
    monkeypatch.setattr(door, "_find_origin", lambda t, c: (GH, "x"))
    hub.push_application_to_crm(job_title="Analytics Engineer, Data", company="", job_url=WWR, notes="n")
    assert push[0]["jobUrl"] == WWR and push[0]["notes"] == "n"


def test_a_resolver_failure_changes_nothing(push, monkeypatch):
    def boom(t, c):
        raise RuntimeError("bright data down")
    monkeypatch.setattr(door, "_find_origin", boom)
    hub.push_application_to_crm(job_title="Analytics Engineer, Data", company="Tailscale", job_url=WWR, notes="n")
    assert push[0]["jobUrl"] == WWR and push[0]["notes"] == "n"


def test_an_origin_is_https():
    want = door._title_tokens("Analytics Engineer, Data")
    hit = [("Job Application for Analytics Engineer, Data at Tailscale", "http://job-boards.greenhouse.io/tailscale/jobs/4721289005")]
    assert door._best_match(want, hit) == (GH, "Job Application for Analytics Engineer, Data at Tailscale")
