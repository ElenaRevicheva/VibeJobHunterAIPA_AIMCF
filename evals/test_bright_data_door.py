"""The Bright Data door (src/search/serpapi_jobs_ingest.py) — 29 Sep 2026 changes. Offline.

Measured before: of 98 jobs this door parked 27-29 Sep, read in full, 77 were off-lane and 17 failed
the gate (mostly US-only); every in-lane one had been judged on a ~180-char Google snippet.
"""
import re
from pathlib import Path

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
