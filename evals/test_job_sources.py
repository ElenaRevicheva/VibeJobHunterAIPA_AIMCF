"""
Job-source tests for src/autonomous/job_monitor.py (added 2026-10-06). NO network.

Why these exist:
- Torre answered every search with HTTP 400 from 2 Oct 02:56 UTC and the log said
  "✅ Torre.ai: 0 jobs found" for four days. A refused call and an empty result must
  never print the same line — tested below with a fake HTTP session.
- Puente Talent Partners is a new LATAM-only source. Its listing and role pages are
  parsed from HTML saved live on 6 Oct 2026 (evals/fixtures/puente_*.html), so a
  layout change shows up here instead of as a silent "0 jobs".
- Remotive's free API ignores `search` and limits clients to 2 requests a minute;
  the source must fetch its feed once and match the lane terms locally.

The fake session stands in for aiohttp.ClientSession: every test patches it, so a
test that accidentally reached the network would fail on the missing handler.
"""
import asyncio
import json
import logging
import re
from pathlib import Path

import pytest

from src.autonomous import job_monitor as jm
from src.autonomous.job_monitor import JobMonitor, _source_result_line, _http_error

FIX = Path(__file__).parent / "fixtures"
LISTING = (FIX / "puente_jobs_listing.html").read_text(encoding="utf-8")
AI_OPS = (FIX / "puente_job_ai-operations-lead-2660.html").read_text(encoding="utf-8")
CHIEF = (FIX / "puente_job_chief-of-staff-2663.html").read_text(encoding="utf-8")

TORRE_400 = '{"meta":{"message":"Invalid request"}}'

# Professional Outlook (Oct 2026, p.7) titles that were added to the free sources.
OUTLOOK_TERMS = ("ai implementation lead", "ai workflow architect", "agentic workflow",
                 "ai systems operator", "ai innovation lead", "generative ai product lead",
                 "ai prototyping", "creative ai pipeline", "ai product automation")


# ─────────────────────────────────────────────────────────────────────────────
# Fake aiohttp
# ─────────────────────────────────────────────────────────────────────────────
class _Resp:
    def __init__(self, status, body, tracker=None):
        self.status, self._body, self._tracker = status, body, tracker

    async def text(self):
        return self._body

    async def json(self, content_type=None):
        return json.loads(self._body)

    async def __aenter__(self):
        if self._tracker is not None:
            self._tracker["active"] += 1
            self._tracker["max"] = max(self._tracker["max"], self._tracker["active"])
            await asyncio.sleep(0.001)      # let other fetches overlap, so the cap is real
        return self

    async def __aexit__(self, *exc):
        if self._tracker is not None:
            self._tracker["active"] -= 1
        return False


class _Session:
    """Records every request; `handler(method, url, kwargs) -> (status, body)`."""

    def __init__(self, handler, calls, tracker=None):
        self._handler, self.calls, self._tracker = handler, calls, tracker

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def _req(self, method, url, kw):
        self.calls.append((method, url, kw))
        status, body = self._handler(method, url, kw)
        return _Resp(status, body, self._tracker)

    def get(self, url, **kw):
        return self._req("GET", url, kw)

    def post(self, url, **kw):
        return self._req("POST", url, kw)


@pytest.fixture
def fake_http(monkeypatch):
    """Install a fake ClientSession; returns (set_handler, calls, tracker)."""
    calls, tracker, box = [], {"active": 0, "max": 0}, {}

    def factory(*a, **kw):
        return _Session(box["handler"], calls, tracker)

    monkeypatch.setattr(jm.aiohttp, "ClientSession", factory)

    def set_handler(fn):
        box["handler"] = fn
    return set_handler, calls, tracker


@pytest.fixture
def monitor(monkeypatch):
    """A JobMonitor without __init__ (no seen_jobs.json read, no cache dir created),
    with the class-level caches emptied so tests cannot leak into each other."""
    monkeypatch.setattr(JobMonitor, "_PUENTE_PAGE_CACHE", {})
    monkeypatch.setattr(JobMonitor, "_REMOTIVE_CACHE", {})
    m = JobMonitor.__new__(JobMonitor)
    m._source_health = {}
    return m


def _run(coro):
    return asyncio.run(coro)


def _messages(caplog, level=None):
    return [r.getMessage() for r in caplog.records
            if r.name == jm.__name__ and (level is None or r.levelno == level)]


# ─────────────────────────────────────────────────────────────────────────────
# The honest result line
# ─────────────────────────────────────────────────────────────────────────────
def test_zero_jobs_with_failures_is_a_red_line():
    lvl, msg = _source_result_line("Torre.ai", 0, 46, 46, "HTTP 400 " + TORRE_400)
    assert lvl == logging.WARNING
    assert msg == f"❌ Torre.ai: 0 jobs — 46/46 requests failed (HTTP 400 {TORRE_400})"
    assert "✅" not in msg


def test_partial_failure_is_a_warning_not_a_tick():
    lvl, msg = _source_result_line("Himalayas", 120, 2, 24, "HTTP 429 slow down", unit="searches")
    assert lvl == logging.WARNING
    assert msg.startswith("⚠️ Himalayas: 120 jobs found — 2/24 searches failed (HTTP 429")


def test_genuine_success_keeps_the_tick():
    assert _source_result_line("Torre.ai", 551, 0, 46) == (logging.INFO, "✅ Torre.ai: 551 jobs found")
    # A clean empty answer is still a success — only FAILED calls turn the line red.
    assert _source_result_line("Torre.ai", 0, 0, 46) == (logging.INFO, "✅ Torre.ai: 0 jobs found")


def test_http_error_keeps_status_and_first_120_chars_on_one_line():
    err = _http_error(503, "line one\n" + "x" * 300)
    assert err.startswith("HTTP 503 line one x")
    assert "\n" not in err and len(err) == len("HTTP 503 ") + 120


# ─────────────────────────────────────────────────────────────────────────────
# Torre
# ─────────────────────────────────────────────────────────────────────────────
def test_torre_payload_builder_shape():
    assert JobMonitor._torre_payload("ai automation") == {
        "and": [{"skill/role": {"text": "ai automation", "experience": "potential-to-develop"}}]}
    assert JobMonitor._TORRE_SEARCH_URL.startswith("https://search.torre.co/opportunities/_search")


def test_torre_identifies_as_vjh_not_as_torres_own_client():
    # 6 Oct 2026: search.torre.co only answers its internal client's User-Agent.
    # Torre's terms forbid circumventing its security features, so VJH must keep
    # naming itself. Restoring Torre needs access Torre grants, not a borrowed name.
    ua = JobMonitor._TORRE_HEADERS["User-Agent"]
    assert "VibeJobHunter" in ua
    assert "torre" not in ua.lower()


def test_torre_keywords_follow_the_lane_decision():
    kws = JobMonitor._TORRE_KEYWORDS
    assert "ai evaluation" not in kws                      # lane dropped 6 Oct 2026
    for term in OUTLOOK_TERMS:
        assert term in kws, term
    for kept in ("ai chief of staff", "ai operations lead", "chief ai officer", "creative technologist"):
        assert kept in kws, kept                           # kept lanes still searched
    assert len(kws) == len(set(kws))


def test_torre_refusals_print_red_and_stop_early(monitor, fake_http, caplog):
    set_handler, calls, _ = fake_http
    set_handler(lambda method, url, kw: (400, TORRE_400))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    jobs = _run(monitor._search_torre())

    assert jobs == []
    # A 4xx is deterministic — stop after 3 instead of sending ~58 doomed requests.
    assert len(calls) == JobMonitor._TORRE_FAIL_FAST_AFTER == 3
    assert calls[0][2]["json"] == JobMonitor._torre_payload(JobMonitor._TORRE_KEYWORDS[0])
    warn = _messages(caplog, logging.WARNING)
    assert f"❌ Torre.ai: 0 jobs — 3/3 requests failed (HTTP 400 {TORRE_400})" in warn
    assert any("[ai engineer]: HTTP 400" in m for m in warn)          # each refusal is visible
    assert not any("✅ Torre.ai" in m for m in _messages(caplog))
    assert monitor._source_health["torre"]["failed"] == 3


def test_torre_exceptions_are_counted_not_swallowed(monitor, fake_http, caplog):
    set_handler, calls, _ = fake_http

    def boom(method, url, kw):
        raise RuntimeError("connection reset")
    set_handler(boom)
    caplog.set_level(logging.INFO, logger=jm.__name__)

    assert _run(monitor._search_torre()) == []
    n = len(JobMonitor._TORRE_KEYWORDS)
    assert len(calls) == n                 # a crash is not a refusal — it keeps asking
    assert any(m.startswith(f"❌ Torre.ai: 0 jobs — {n}/{n} requests failed (RuntimeError")
               for m in _messages(caplog, logging.WARNING))


def test_torre_success_still_parses_remote_and_latam(monitor, fake_http, caplog):
    set_handler, calls, _ = fake_http
    opp = {"id": "ZW53kGkd", "slug": "acme-ai-ops", "objective": "AI Operations Lead",
           "tagline": "Run AI ops", "remote": True, "status": "open",
           "organizations": [{"name": "Acme"}], "locations": ["Panama", "Mexico"]}
    onsite = dict(opp, id="x2", slug="onsite", remote=False)
    body = json.dumps({"results": [opp, onsite]})
    set_handler(lambda method, url, kw: (200, body))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    jobs = _run(monitor._search_torre())

    assert len(jobs) == 1                                   # same slug deduped; on-site dropped
    j = jobs[0]
    assert j["company"] == "Acme" and j["url"] == "https://torre.ai/jobs/ZW53kGkd"
    assert j["location"] == "Remote — Worldwide / LATAM (Panama, Mexico)"
    assert "✅ Torre.ai: 1 jobs found" in _messages(caplog, logging.INFO)


# ─────────────────────────────────────────────────────────────────────────────
# Puente — parsing (saved live pages)
# ─────────────────────────────────────────────────────────────────────────────
def test_puente_listing_parses_every_role():
    rows = JobMonitor._parse_puente_listing(LISTING)
    assert len(rows) == 55
    by_id = {r["role_id"]: r for r in rows}
    assert by_id["2660"] == {
        "role_id": "2660", "url": "https://puentetalent.com/jobs/ai-operations-lead-2660",
        "title": "AI Operations Lead", "location_text": "Latin America · Remote",
        "salary_text": "$3,000 - $4,000 / month"}
    assert by_id["2663"]["title"] == "Chief of Staff"
    assert by_id["2663"]["salary_text"] == "$3,500 - $5,000 / month"
    # The shapes that are not "Latin America · Remote":
    assert by_id["2671"]["location_text"] == "Brazil, Argentina, Colombia, Chile · Remote"
    assert by_id["2696"]["location_text"] == "Remote"
    assert by_id["2698"]["salary_text"] == ""                # no pay listed → empty, not a crash
    assert all(r["url"].startswith("https://puentetalent.com/jobs/") for r in rows)


def test_puente_listing_with_no_rows_parses_to_nothing():
    assert JobMonitor._parse_puente_listing("<html><a href='/jobs'>Jobs</a></html>") == []


def test_puente_detail_reads_the_jsonld_jobposting():
    d = JobMonitor._parse_puente_detail(AI_OPS)
    assert "What you'll own" in d["description"]
    assert "What we're looking for" in d["description"]
    assert "- Internal AI workflows and agents built with tools like n8n, Make, Zapier" in d["description"]
    assert "<" not in d["description"]
    assert len(d["countries"]) == 18 and "Panama" in d["countries"]
    assert d["salary_text"] == "$3,000 - $4,000 / month"
    assert d["employment_type"] == "CONTRACTOR"
    assert JobMonitor._parse_puente_detail(CHIEF)["salary_text"] == "$3,500 - $5,000 / month"


def test_puente_jsonld_description_drops_the_why_puente_boilerplate():
    # 2026-10-06: both fixtures' JSON-LD descriptions carry "Why Puente" + the hiring
    # steps ("a recruiter interview", "skills assessment") — Puente's pitch, not the role.
    for page in (AI_OPS, CHIEF):
        raw = next(json.loads(m.group(1)) for m in
                   re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S)
                   if '"JobPosting"' in m.group(1))
        assert "Why Puente" in raw["description"]            # the cut is not vacuous
        d = JobMonitor._parse_puente_detail(page)
        assert "Why Puente" not in d["description"]
        assert "recruiter interview" not in d["description"]
        assert "What you'll own" in d["description"] or "What we're looking for" in d["description"]


def test_puente_boilerplate_cut_never_empties_a_description():
    assert JobMonitor._puente_cut_boilerplate("Role text\nWhy Puente\nPitch") == "Role text"
    assert JobMonitor._puente_cut_boilerplate("No pitch here") == "No pitch here"
    assert JobMonitor._puente_cut_boilerplate("") == ""


def test_puente_detail_falls_back_to_visible_text_without_jsonld():
    stripped = re.sub(r'<script[^>]*application/ld\+json[^>]*>.*?</script>', "", AI_OPS, flags=re.S)
    d = JobMonitor._parse_puente_detail(stripped)
    assert "What you'll own" in d["description"]
    assert "Why Puente" not in d["description"]              # stops before the boilerplate
    assert d["countries"] == []


@pytest.mark.parametrize("loc, countries, expected", [
    # 2026-10-06: home country first — the LLM judge only sees location[:80].
    ("Latin America · Remote", ["Mexico", "Panama"], "Remote — Latin America (Panama, Mexico)"),
    ("Latin America · Remote", ["México", "Panamá"], "Remote — Latin America (Panamá, México)"),
    ("Latin America · Remote", [], "Remote — Latin America (" + JobMonitor._PUENTE_LATAM_FALLBACK + ")"),
    ("Brazil, Argentina, Colombia, Chile · Remote", [], "Remote (Brazil, Argentina, Colombia, Chile)"),
    ("Brazil, Argentina · Remote", ["Brazil", "Argentina"], "Remote (Brazil, Argentina)"),
    ("Remote", [], "Remote"),
])
def test_puente_location(loc, countries, expected):
    assert JobMonitor._puente_location(loc, countries) == expected


def test_puente_location_fallback_names_panama():
    assert "Panama" in JobMonitor._puente_location("Latin America · Remote", [])


def test_puente_location_lets_the_gate_decide():
    from src.core.fit_gate import roster_excludes_home
    # Names Panama → not excluded; a roster without Panama → excluded (parked).
    assert not roster_excludes_home(JobMonitor._puente_location("Latin America · Remote", ["Mexico", "Panama"]))
    assert roster_excludes_home(JobMonitor._puente_location("Brazil, Argentina, Colombia, Chile · Remote", []))


def test_puente_job_dict_matches_the_shared_schema():
    row = {r["role_id"]: r for r in JobMonitor._parse_puente_listing(LISTING)}["2660"]
    job = JobMonitor._puente_job(row, JobMonitor._parse_puente_detail(AI_OPS))
    assert job["id"] == "puente_2660"
    assert job["title"] == "AI Operations Lead"
    assert job["company"] == "Puente Talent Partners"
    assert job["url"] == "https://puentetalent.com/jobs/ai-operations-lead-2660"
    assert job["source"] == "puente"
    assert job["salary"] == "$3,000 - $4,000 / month"
    assert job["remote"] is True
    assert job["location"].startswith("Remote — Latin America (") and "Panama" in job["location"]
    # 2026-10-06: llm_judge.judge_fit shows the judge location[:80]. Puente's JSON-LD
    # lists Panama 12th of 18, so without reordering the judge saw a roster without her.
    assert "Panama" in job["location"][:80]  # the judge's window
    roster = job["location"][len("Remote — Latin America ("):-1].split(", ")
    assert roster[0] == "Panama"
    assert sorted(roster) == sorted(JobMonitor._parse_puente_detail(AI_OPS)["countries"])  # nothing lost
    # Pay sits first so the 4,000-char cut downstream can never drop it.
    assert job["description"].startswith("Salary: $3,000 - $4,000 / month")
    assert "What you'll own" in job["description"]


def test_puente_pay_is_judged_by_the_salary_gate():
    from src.core.salary_gate import salary_verdict
    rows = {r["role_id"]: r for r in JobMonitor._parse_puente_listing(LISTING)}
    ok = JobMonitor._puente_job(rows["2660"], {"description": "x"})
    intern = JobMonitor._puente_job(rows["2681"], {"description": "x"})      # $350 / month
    assert salary_verdict(ok["title"], ok["description"], "")[0] == "ok"
    assert salary_verdict(intern["title"], intern["description"], "")[0] == "below_floor"


# ─────────────────────────────────────────────────────────────────────────────
# Puente — the fetch path
# ─────────────────────────────────────────────────────────────────────────────
def _puente_handler(method, url, kw):
    if url == "https://puentetalent.com/jobs":
        return 200, LISTING
    if url.endswith("/jobs/ai-operations-lead-2660"):
        return 200, AI_OPS
    if url.endswith("/jobs/chief-of-staff-2663"):
        return 200, CHIEF
    return 404, "<html>not found</html>"


def test_puente_fetches_pages_four_at_a_time_and_holds_back_failures(monitor, fake_http, caplog):
    set_handler, calls, tracker = fake_http
    set_handler(_puente_handler)
    caplog.set_level(logging.INFO, logger=jm.__name__)

    jobs = _run(monitor._search_puente())

    assert {j["id"] for j in jobs} == {"puente_2660", "puente_2663"}   # 53 page failures held back
    assert len(calls) == 1 + 55
    assert tracker["max"] <= 4
    assert any(m.startswith("⚠️ Puente: 2 jobs found — 53/55 role pages failed (HTTP 404")
               for m in _messages(caplog, logging.WARNING))
    # Only the first 5 page failures are logged one by one.
    assert sum("Puente role page" in m for m in _messages(caplog, logging.WARNING)) == 5

    # Second cycle: the two good pages come from the cache, the failures are retried.
    calls.clear()
    again = _run(monitor._search_puente())
    assert {j["id"] for j in again} == {"puente_2660", "puente_2663"}
    fetched = [u for _, u, _ in calls]
    assert "https://puentetalent.com/jobs/ai-operations-lead-2660" not in fetched
    assert len(fetched) == 1 + 53


def test_puente_listing_failure_is_red(monitor, fake_http, caplog):
    set_handler, calls, _ = fake_http
    set_handler(lambda method, url, kw: (503, "upstream down"))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    assert _run(monitor._search_puente()) == []
    assert "❌ Puente: 0 jobs — 1/1 listing requests failed (HTTP 503 upstream down)" in \
        _messages(caplog, logging.WARNING)
    assert len(calls) == 1


def test_puente_layout_change_is_red_not_zero(monitor, fake_http, caplog):
    set_handler, _, _ = fake_http
    set_handler(lambda method, url, kw: (200, "<html><body>redesigned</body></html>"))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    assert _run(monitor._search_puente()) == []
    assert any(m.startswith("❌ Puente: 0 jobs — 1/1 listing requests failed (HTTP 200 but 0 role rows")
               for m in _messages(caplog, logging.WARNING))


def test_puente_same_title_keeps_the_better_paid_role(monitor, fake_http):
    # "GTM Engineer" is listed twice (#2680 $2,000-$3,000, #2637 $3,500-$4,500). VJH dedupes
    # dict jobs on company::title, so only one can ever be judged — it must be the one that pays.
    set_handler, _, _ = fake_http
    set_handler(lambda method, url, kw: (200, LISTING) if url.endswith("/jobs") else (200, AI_OPS))

    jobs = _run(monitor._search_puente())

    gtm = [j for j in jobs if j["title"] == "GTM Engineer"]
    assert len(gtm) == 1 and gtm[0]["id"] == "puente_2637"
    assert len(jobs) == 54


# ─────────────────────────────────────────────────────────────────────────────
# Himalayas
# ─────────────────────────────────────────────────────────────────────────────
def _hima_body(q):
    return json.dumps({"jobs": [{"title": f"{q} role", "applicationLink": f"https://h.example/{q}",
                                 "companyName": "Co", "locationRestrictions": []}]})


def test_himalayas_queries_follow_the_lane_decision(monitor, fake_http):
    set_handler, calls, _ = fake_http
    set_handler(lambda method, url, kw: (200, _hima_body(kw["params"]["q"])))

    jobs = _run(monitor._search_himalayas())

    sent = [kw["params"]["q"].lower() for _, _, kw in calls]
    assert "ai evaluation" not in sent
    for term in OUTLOOK_TERMS:
        assert term in sent, term
    assert len(jobs) == len(sent) == len(set(sent))


def test_himalayas_failed_search_is_named(monitor, fake_http, caplog):
    set_handler, _, _ = fake_http

    def handler(method, url, kw):
        q = kw["params"]["q"]
        return (429, "Too Many Requests") if q == "AI automation" else (200, _hima_body(q))
    set_handler(handler)
    caplog.set_level(logging.INFO, logger=jm.__name__)

    _run(monitor._search_himalayas())

    warn = _messages(caplog, logging.WARNING)
    assert "   ⚠️ Himalayas [AI automation]: HTTP 429 Too Many Requests" in warn
    assert any(m.startswith("⚠️ Himalayas: ") and "1/24 searches failed (HTTP 429" in m for m in warn)


def test_himalayas_all_failed_is_red(monitor, fake_http, caplog):
    set_handler, _, _ = fake_http
    set_handler(lambda method, url, kw: (500, "oops"))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    assert _run(monitor._search_himalayas()) == []
    assert "❌ Himalayas: 0 jobs — 24/24 searches failed (HTTP 500 oops)" in _messages(caplog, logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# Remotive
# ─────────────────────────────────────────────────────────────────────────────
_FEED = json.dumps({"jobs": [
    {"id": 1, "title": "AI Workflow Architect", "company_name": "A", "description": "<p>build</p>",
     "candidate_required_location": "LATAM", "url": "https://remotive.com/1"},
    {"id": 2, "title": "Bookkeeper", "company_name": "B", "description": "ledgers",
     "candidate_required_location": "USA", "url": "https://remotive.com/2"},
    {"id": 3, "title": "Ops Lead", "company_name": "C", "description": "You will run our n8n stack",
     "candidate_required_location": "", "url": "https://remotive.com/3"},
]})


def test_remotive_fetches_once_and_matches_locally(monitor, fake_http, caplog):
    set_handler, calls, _ = fake_http
    set_handler(lambda method, url, kw: (200, _FEED))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    jobs = _run(monitor._search_remotive())
    again = _run(monitor._search_remotive())

    assert len(calls) == 1                                 # one request, then the 6 h cache
    assert "search=" not in calls[0][1]                    # the API ignores it anyway
    assert [j["title"] for j in jobs] == ["AI Workflow Architect", "Ops Lead"] == [j["title"] for j in again]
    assert jobs[0]["location"] == "Remote — LATAM" and jobs[1]["location"] == "Remote — Worldwide"
    assert any(m.startswith("✅ Remotive: 2 jobs found") for m in _messages(caplog, logging.INFO))


def test_remotive_refusal_is_red(monitor, fake_http, caplog):
    set_handler, _, _ = fake_http
    set_handler(lambda method, url, kw: (429, "Too Many Requests"))
    caplog.set_level(logging.INFO, logger=jm.__name__)

    assert _run(monitor._search_remotive()) == []
    assert "❌ Remotive: 0 jobs — 1/1 requests failed (HTTP 429 Too Many Requests)" in \
        _messages(caplog, logging.WARNING)
    assert JobMonitor._REMOTIVE_CACHE == {}                # a failure is not cached


# ─────────────────────────────────────────────────────────────────────────────
# Wiring
# ─────────────────────────────────────────────────────────────────────────────
def test_puente_is_wired_into_the_cycle():
    src = Path(jm.__file__).read_text(encoding="utf-8")
    assert 'safe_fetch("Puente (LATAM placement)", self._search_puente(), 45, key="puente")' in src
    assert '"puente": 0' in src
    order = re.search(r"_SRC_YIELD_ORDER = \((.*?)\n\s*\)", src, re.S).group(1)
    names = re.findall(r'^\s*"([a-z_]+)",', order, re.M)
    assert names.index("puente") == names.index("torre") + 1   # LATAM-first, next to Torre
