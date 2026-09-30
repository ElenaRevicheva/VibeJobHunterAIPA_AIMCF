"""Our own mail is never an employer reply.

30 Sep 2026: the portfolio form mails aipa@ a copy of every CLIENT inquiry ("[AIdeazz] Inquiry — <name>",
From: AIdeazz <aipa@...>). The response detector read that copy as an employer QUESTION and opened a
[HIRING-VJH-LEAD] deal + cover letter for a business inquiry. The fix is one entry in the existing sender
blocklist; these pin it, and that real recruiters and the old noise rules are unchanged.
"""
from src.autonomous.response_detector import _sender_is_blocked

OWN = "aipa@" "aideazz.xyz"


def test_own_inquiry_copy_is_blocked():
    assert _sender_is_blocked(f"AIdeazz <{OWN}>")
    assert _sender_is_blocked(OWN)
    assert _sender_is_blocked(OWN.upper())


def test_real_recruiters_still_pass():
    assert not _sender_is_blocked("Jane Recruiter <" "jane@" "acme-talent.com" ">")
    assert not _sender_is_blocked("hiring@" "startup.io")
    # a lookalike on another domain is not ours
    assert not _sender_is_blocked("team@" "aideazz-consulting.com")


def test_existing_noise_rules_unchanged():
    assert _sender_is_blocked("no-reply@" "torre.ai")
    assert _sender_is_blocked("digest@" "substack.com")
    assert not _sender_is_blocked("")
    assert not _sender_is_blocked(None)
