"""Closed-posting detection — a dead job must never reach "I Act TODAY" as live.

28 Sep 2026: Torre changed its banner to "This job post is closed." and 5 closed Torre jobs sat in
Elena's queue for 10 days, because the July phrase no longer matched. These pin both wordings, and
that ordinary prose never reads as closed.
"""
from src.scrapers.job_enricher import looks_closed


def test_torre_banners_both_wordings():
    assert looks_closed('<div class="torrebanner__wrapper"><span>this job post is closed.</span></div>')
    assert looks_closed("This job opening is closed. SET AN ALERT")


def test_prose_is_not_closed():
    assert not looks_closed("We build closed-loop systems and post updates on our blog.")
    assert not looks_closed("<p>Remote (anywhere). Apply now.</p>")
