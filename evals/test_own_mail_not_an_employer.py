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


def test_her_own_calendly_is_not_an_employer_booking_link():
    # 15 Oct 2026: a client reply quoting the Lead Concierge's sign-off must not become an interview alert.
    from src.autonomous.response_detector import extract_booking_link
    quoted = "Thanks!\n> Book 15 min: https://calendly.com/elena_revicheva/coffee-chat"
    assert extract_booking_link(quoted) is None
    assert extract_booking_link(quoted.lower()) is None
    assert extract_booking_link("old link https://calendly.com/elena-aideazz") is None
    # an employer's own link is kept, also when hers is quoted below it
    emp = "Pick a slot: https://calendly.com/acme-recruiter/30min\n> https://calendly.com/elena_revicheva/coffee-chat"
    assert extract_booking_link(emp) == "https://calendly.com/acme-recruiter/30min"
    assert extract_booking_link("https://calendly.com/acme-recruiter/30min.") == "https://calendly.com/acme-recruiter/30min"


def test_quoted_thread_links_are_not_their_invite():
    from src.autonomous.response_detector import extract_booking_link, looks_like_interview_request
    # a client's "booked, thanks" quoting her one-off diagnostic link
    reply = "Booked, thanks!\n\nOn Tue, Oct 14, 2026 at 9:00 AM Elena <aipa@x> wrote:\n> Pick a time: https://calendly.com/d/abcd-efg-hij/45-minute-meeting"
    assert extract_booking_link(reply) is None
    assert extract_booking_link("ok\n> https://calendly.com/d/abcd-efg-hij/45-minute-meeting") is None
    # an employer invite with the thread quoted below still counts
    invite = ("Thank you for your interest in the AI Engineer role. Pick a slot: https://calendly.com/acme-talent/30min\n\n"
              "On Mon, Oct 13, 2026 Elena wrote:\n> https://calendly.com/elena_revicheva/coffee-chat")
    assert extract_booking_link(invite) == "https://calendly.com/acme-talent/30min"
    assert looks_like_interview_request("Next steps", invite)


def test_existing_noise_rules_unchanged():
    assert _sender_is_blocked("no-reply@" "torre.ai")
    assert _sender_is_blocked("digest@" "substack.com")
    assert not _sender_is_blocked("")
    assert not _sender_is_blocked(None)
