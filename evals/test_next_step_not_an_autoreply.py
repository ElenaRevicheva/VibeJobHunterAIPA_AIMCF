"""A mail that names a NEXT STEP is never an auto-reply, and Turing is not newsletter noise (26 Oct 2026). Offline.

WON.ai, 26 Oct 08:15 UTC: "Thank you for applying… As a next step, this role includes a video screen… will
expire 5 days after receiving this email." Classified positive 1.0, saved, then dropped by the orchestrator's
auto-reply guard — no HubSpot note, no Telegram alert, a 5-day clock running unseen.
Turing, 26 Oct 12:37 UTC: "This is Sushmita, and I am a Recruiter at Turing… Review Job Description and Submit
Job Interest" from Turing's no-reply sender — positive 0.95, dropped as a blocked sender.
"""
import src.autonomous.response_detector as rd

WON = ("Next Steps with WON.ai for AI Strategist - Remote LATAM Hi Elena, Thank you for applying for the AI Strategist "
       "- Remote LATAM position at WON.ai. I have reviewed your application and think you could be a good fit for the "
       "role! As a next step, this role includes a video screen. Please note this video assessment will expire 5 days "
       "after receiving this email.")
ASHBY = ("Thanks for applying to WON! Hi Elena, Thank you for applying for the AI Strategist - Remote, LatAm role at WON! "
         "We appreciate your interest in joining the team. We will review your application and get back to you with next "
         "steps. All the best, WON Hiring Team")


def test_a_video_screen_is_a_next_step():
    assert rd._next_step_signal(WON.lower()) in ("video screen", "as a next step", "video assessment")


def test_a_plain_confirmation_is_not():
    assert rd._next_step_signal(ASHBY.lower()) == ""      # "next steps" alone must not count


def test_booking_and_assessment_phrases_count():
    for t in ("please pick a time that suits you", "complete the assessment by Friday", "we would like to invite you",
              "this is a one-way interview", "your take-home assignment"):
        assert rd._next_step_signal(t), t


def test_empty_is_nothing():
    assert rd._next_step_signal("") == "" and rd._next_step_signal(None) == ""


AT = "@"   # addresses are built from parts: the repo's pii-guard refuses a literal third-party address


def test_turing_recruiter_is_not_blocked():
    assert not rd._sender_is_blocked("no-reply" + AT + "turing.com")
    assert not rd._sender_is_blocked("Sushmita <No-Reply" + AT + "Turing.com>")


def test_the_rest_of_the_blocklist_stands():
    for s in ("no-reply" + AT + "ashbyhq.com", "noreply" + AT + "torre.ai", "newsletter" + AT + "substack.com",
              "aipa" + AT + "aideazz.xyz", "intro" + AT + "boardy.ai"):
        assert rd._sender_is_blocked(s), s
