"""Outreach no longer crashes on a str company_intel; httpx/httpcore stay quiet in the journal.

6 Oct 2026, two fixes pinned here:

1. The LangGraph outreach node (score 55-59) calls `FounderFinderV2.find_founder(company, state['url'])` —
   the job POSTING url, a str — and find_founder did `company_intel.get("url")`. Journal: 2 Oct 13:19:01 UTC
   "[outreach] ERROR CIO Landing", 5 Oct 16:03:59 and 16:04:02 UTC "[outreach] ERROR Nuro", each "'str' object
   has no attribute 'get'" — the only 3 outreach-routed jobs since 1 Sep. A str is now read as a text
   summary, never as the company url (a posting url is a job-board host: the email search would look up the
   ATS vendor's staff), and a record built without a company url is not cached, so it cannot starve the
   orchestrator's find_and_message() — which resolves a real url — for the cache's 24h. The skip is LOGGED,
   so the journal never reads "searched, found nobody" when no search ran.

   2026-10-06 review: fixing the crash alone would have made those jobs DISAPPEAR. The crash turned them into
   'error', and notify_node pinged Elena "Apply FAILED"; the clean exit was 'outreach_no_contact', which
   notify_node drops (no Telegram, no HubSpot) and the runner treats as terminal. The no-contact path now ends
   'human_pending' — the existing LEAD surface — so each one reaches her once, in Telegram and HubSpot.

2. httpx logs every request url at INFO and the Telegram getUpdates url carries the bot token. src/main.py
   (the vibejobhunter entrypoint) holds httpx — and now httpcore — at WARNING. Checked in a fresh process,
   so another test cannot have set the level first.

No network, no Hunter.io credits, no LLM: the email verifier is off and the YC lookup is stubbed.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from src.autonomous.founder_finder_v2 import FounderFinderV2

REPO = Path(__file__).resolve().parents[1]

# Same shape as the crash input: outreach_node passes the posting url, not a company dict.
POSTING_URL = "https://boards.greenhouse.io/nuro/jobs/7000001"


class _FakeCache:
    def __init__(self):
        self.stored = {}
        self.writes = []

    def get_data(self, key):
        return self.stored.get(key)

    def set_data(self, key, data):
        self.writes.append(key)
        self.stored[key] = data


def _light_init(self):
    """FounderFinderV2 minus its side effects (Resend, Telegram, DB, Hunter.io, disk cache)."""
    self.cache = _FakeCache()
    self.email_verifier = None
    self.seen_company_urls = []
    real_find_email_pattern = self._find_email_pattern

    async def _spy_email_pattern(company_name, company_url):
        self.seen_company_urls.append(company_url)
        return await real_find_email_pattern(company_name, company_url)

    async def _no_yc(company_name):
        return {}

    self._find_email_pattern = _spy_email_pattern
    self._check_yc_profile = _no_yc


def _finder():
    f = FounderFinderV2.__new__(FounderFinderV2)
    _light_init(f)
    return f


# ── 1. the crash ────────────────────────────────────────────────────────────

def test_posting_url_str_no_longer_crashes():
    info = asyncio.run(_finder().find_founder("Nuro", POSTING_URL))
    assert isinstance(info, dict)
    assert info["company"] == "Nuro"


def test_posting_url_is_never_used_as_the_company_domain():
    f = _finder()
    info = asyncio.run(f.find_founder("Nuro", POSTING_URL))
    assert f.seen_company_urls == [""]          # no email search against greenhouse.io
    assert "domain" not in info
    assert not any("greenhouse" in p for p in info.get("email_patterns", []))


def test_plain_text_and_none_do_not_crash():
    for intel in ("Series A robotics company building autonomous delivery", "", "   ", None):
        info = asyncio.run(_finder().find_founder("Acme Robotics", intel))
        assert isinstance(info, dict)


def test_str_path_does_not_cache_a_partial_record():
    f = _finder()
    asyncio.run(f.find_founder("Nuro", POSTING_URL))
    assert f.cache.writes == []
    # so the orchestrator path, which passes a real company url, still does the full lookup
    info = asyncio.run(f.find_founder("Nuro", {"url": "https://nuro.ai"}))
    assert f.seen_company_urls == ["", "https://nuro.ai"]
    assert info["domain"] == "nuro.ai"
    assert f.cache.writes == ["founder::nuro"]


def test_dict_path_unchanged():
    f = _finder()
    info = asyncio.run(f.find_founder("Acme", {"url": "https://www.example.com", "description": "x"}))
    assert f.seen_company_urls == ["https://www.example.com"]
    assert info["domain"] == "example.com"
    assert "founder@example.com" in info["email_patterns"]
    assert f.cache.writes == ["founder::acme"]


class _SpyLogger:
    """Stands in for founder_finder_v2's module logger; records warnings, swallows the rest."""

    def __init__(self):
        self.warnings = []

    def warning(self, msg, *a, **k):
        self.warnings.append(str(msg))

    def __getattr__(self, name):  # debug / info / error
        return lambda *a, **k: None


def test_str_path_logs_that_the_email_search_was_skipped(monkeypatch):
    import src.autonomous.founder_finder_v2 as ffv2
    spy = _SpyLogger()
    monkeypatch.setattr(ffv2, "logger", spy)
    asyncio.run(_finder().find_founder("Nuro", POSTING_URL))
    assert len(spy.warnings) == 1, spy.warnings
    assert "Nuro" in spy.warnings[0]
    assert "got str" in spy.warnings[0]
    assert "email search skipped" in spy.warnings[0]


def test_dict_with_url_logs_no_skip_and_still_searches(monkeypatch):
    import src.autonomous.founder_finder_v2 as ffv2
    spy = _SpyLogger()
    monkeypatch.setattr(ffv2, "logger", spy)
    f = _finder()
    info = asyncio.run(f.find_founder("Acme", {"url": "https://www.example.com"}))
    assert f.seen_company_urls == ["https://www.example.com"]   # the email search ran, as before
    assert info["domain"] == "example.com"
    assert not any("email search skipped" in w for w in spy.warnings), spy.warnings


# The three jobs that actually reached outreach since 1 Sep (journal, read-only): all scored 59, all crashed.
_NURO_UNVERIFIED = {
    "job_id": "nuro-lead-tpm",
    "company": "Nuro",
    "title": "Lead Technical Program Manager, AI Platform",
    "url": POSTING_URL,
    "description": "",
    "score": 59.0,
    "unverified": True,
    "gate_reason": "UNVERIFIED — posting unreadable, on-lane title, needs a human look",
    "raw_job": {"company": "Nuro", "title": "Lead Technical Program Manager, AI Platform", "url": POSTING_URL},
}
_CIO_LANDING_VERIFIED = {
    "job_id": "cio-landing-cm",
    "company": "CIO Landing",
    "title": "Freelance Community Manager with AI Video Skills",
    "url": "https://jobs.lever.co/ciolanding/7000002",
    "description": "x" * 400,
    "score": 59.0,
    "unverified": False,
    "gate_reason": "passed career + iron-clad fit",
    "raw_job": {"company": "CIO Landing", "title": "Freelance Community Manager with AI Video Skills",
                "url": "https://jobs.lever.co/ciolanding/7000002"},
}


def _outreach_env(monkeypatch, tmp_path):
    from src.core.profile_manager import ProfileManager
    monkeypatch.setattr(FounderFinderV2, "__init__", _light_init)
    monkeypatch.setattr(ProfileManager, "__init__", lambda self: None)
    monkeypatch.setattr(ProfileManager, "get_profile", lambda self: None)
    monkeypatch.chdir(tmp_path)  # no autonomous_data/outreach_today.json → the daily cap cannot short-circuit
    monkeypatch.setenv("VJH_OUTREACH_AUTOSEND", "false")


def test_outreach_node_surfaces_no_contact_as_a_lead(monkeypatch, tmp_path):
    """The exact production call, end to end through the LangGraph node."""
    from src.langgraph_pipeline.nodes import outreach_node
    from src.langgraph_pipeline.runner import TERMINAL_STATUSES

    _outreach_env(monkeypatch, tmp_path)
    out = asyncio.run(outreach_node(dict(_NURO_UNVERIFIED)))
    assert out["status"] != "error", out
    assert "has no attribute 'get'" not in str(out)
    # NOT 'outreach_no_contact': notify_node drops that status silently.
    assert out["status"] == "human_pending", out
    assert out["outreach_sent"] is False
    # terminal → the runner fingerprints it and never re-pings it
    assert "human_pending" in TERMINAL_STATUSES


class _FakeTelegram:
    sent = []

    def __init__(self, *a, **k):
        pass

    async def send_message(self, msg, *a, **k):
        _FakeTelegram.sent.append(msg)
        return True


def _run_outreach_then_notify(monkeypatch, tmp_path, job_state):
    """outreach_node → notify_node, the pipeline's own edge, with Telegram and HubSpot mocked."""
    import src.notifications as notifications
    import src.langgraph_pipeline.crm_hub as crm_hub
    from src.langgraph_pipeline.nodes import outreach_node, notify_node

    _outreach_env(monkeypatch, tmp_path)
    _FakeTelegram.sent = []
    crm_calls = []
    monkeypatch.setattr(notifications, "TelegramNotifier", _FakeTelegram)
    monkeypatch.setattr(crm_hub, "push_application_to_crm", lambda **kw: crm_calls.append(kw))

    state = dict(job_state)
    state.update(asyncio.run(outreach_node(dict(state))))
    note = asyncio.run(notify_node(state))
    return state, note, list(_FakeTelegram.sent), crm_calls


def test_no_contact_unverified_job_reaches_elena_once_flagged(monkeypatch, tmp_path):
    state, note, tg, crm = _run_outreach_then_notify(monkeypatch, tmp_path, _NURO_UNVERIFIED)
    assert state["status"] == "human_pending"
    assert note["telegram_sent"] is True and note["status"] == "human_pending"
    assert len(tg) == 1, tg
    assert "UNVERIFIED" in tg[0] and "Nuro" in tg[0]
    assert len(crm) == 1, crm
    assert crm[0]["source_prefix"] == "HIRING-VJH-UNVERIFIED"
    assert crm[0]["job_url"] == POSTING_URL


def test_no_contact_verified_job_reaches_elena_once_as_apply_yourself(monkeypatch, tmp_path):
    state, note, tg, crm = _run_outreach_then_notify(monkeypatch, tmp_path, _CIO_LANDING_VERIFIED)
    assert state["status"] == "human_pending"
    assert len(tg) == 1, tg
    assert "Apply yourself" in tg[0] and "CIO Landing" in tg[0]
    assert len(crm) == 1, crm
    assert crm[0]["source_prefix"] == "HIRING-VJH-LEAD"


# ── 2. the token leak ───────────────────────────────────────────────────────

_PROBE = r'''
import io, json, logging
buf = io.StringIO()
# Production's root logger is INFO (serpapi_jobs_ingest's basicConfig, imported in-process); DEBUG is stricter.
logging.basicConfig(level=logging.DEBUG, stream=buf, format="%(name)s %(message)s")
import src.main  # the vibejobhunter entrypoint: python -m src.main autonomous
logging.getLogger("httpx").info('HTTP Request: POST https://api.telegram.org/botFAKE-TOKEN-123/getUpdates "HTTP/1.1 200 OK"')
logging.getLogger("httpcore").debug("FAKE-HTTPCORE-TRACE")
logging.getLogger("httpx").warning("FAKE-HTTPX-WARNING")
out = buf.getvalue()
print("RESULT " + json.dumps({
    "httpx": logging.getLogger("httpx").level,
    "httpcore": logging.getLogger("httpcore").level,
    "token_logged": "FAKE-TOKEN-123" in out,
    "trace_logged": "FAKE-HTTPCORE-TRACE" in out,
    "warning_logged": "FAKE-HTTPX-WARNING" in out,
}))
'''


def _probe_fresh_process():
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("RESULT ")]
    assert lines, f"probe failed (rc={proc.returncode}): {proc.stderr[-2000:]}"
    return json.loads(lines[-1][len("RESULT "):])


def test_httpx_and_httpcore_held_at_warning_after_logging_setup():
    r = _probe_fresh_process()
    assert r["httpx"] >= 30, r      # logging.WARNING
    assert r["httpcore"] >= 30, r
    assert r["token_logged"] is False, r
    assert r["trace_logged"] is False, r
    assert r["warning_logged"] is True, r   # warnings and errors still reach the journal
