"""Origin boards (src/search/serpapi_jobs_ingest.py, 24 Oct 2026). Offline.

Earned from CI&T job 32354: the Google query is restricted to four ATS domains, but Google returned
dailyremote.com — a paid aggregator whose copy hid the employer, said "Brazil" (origin: Colombia) and
sent every Apply button to its own $14.95 checkout. The copy passed the gate and the judge and got a
full apply kit (deal 66619289430); the origin on jobs.lever.co, found the next day, was parked.

Elena: "if VJH finds a job at a paywalled aggregator he should dig the true initial board where the
job is posted and inspect this job on the criteria VJH has".
"""
import logging
import sys
import types

import pytest

import src.search.serpapi_jobs_ingest as door

DAILYREMOTE = "https://dailyremote.com/remote-job/job-32354-ai-solution-architect-brazil-5802670"
LEVER = "https://jobs.lever.co/ciandt/989a2fd5-f970-4c05-a379-5035cd24ec39"
COPY_TITLE = "[Job - 32354] AI Solution Architect, Brazil at CI&T"
ORIGIN_TITLE = "CI&T - [Job - 32354] AI Solution Architect, Colombia"


# ─── what is an origin ───

@pytest.mark.parametrize("url", [
    LEVER, "https://jobs.eu.lever.co/x/1", "https://acme.lever.co/1",
    "https://job-boards.greenhouse.io/coderoad/jobs/4414020009", "https://boards.greenhouse.io/x/jobs/1",
    "https://jobs.ashbyhq.com/n8n/1", "https://wellfound.com/jobs/4271025-platform-engineer",
])
def test_the_four_boards_are_origins(url):
    assert door._is_origin_host(url)


@pytest.mark.parametrize("url", [
    DAILYREMOTE, "https://www.remoterocketship.com/company/x/jobs/1", "https://www.linkedin.com/jobs/view/1",
    "https://jobgether.com/offer/1", "https://frontendnode-25b1.onrender.com/job/1", "", "not a url",
    "https://lever.co.evil.com/1",      # a suffix is not a board
])
def test_everything_else_is_not(url):
    assert not door._is_origin_host(url)


def test_the_employers_own_site_is_an_origin():
    assert door._is_company_domain("https://stripe.com/jobs/listing/solutions-architect-ai/1", "Stripe")
    assert door._is_company_domain("https://careers.kitrum.com/1", "KITRUM")
    assert not door._is_company_domain(DAILYREMOTE, "CI&T")           # "ci", "t": no 4-letter word
    assert not door._is_company_domain("https://www.remoterocketship.com/1", "Acme Corp")
    assert not door._is_company_domain("https://jobgether.com/offer/1", "Deuna")
    assert not door._is_company_domain("https://jobs.example.com/1", "")


# ─── the posting's own title ───

@pytest.mark.parametrize("title, core", [
    (COPY_TITLE, "[Job - 32354] AI Solution Architect"),           # ", Brazil" and " at CI&T" dropped
    ("Senior AI Engineer at KITRUM • Bogota", "Senior AI Engineer"),
    ("AI Automation Specialist @ LanceMart | Remote", "AI Automation Specialist"),
    ("Director, Engineering", "Director, Engineering"),            # the comma part is a role, kept
    ("Product Head of AI", "Product Head of AI"),
    ("Stripe Careers | Solutions Architect, AI", "Solutions Architect"),   # "Company | Role": the role side
    ("CI&T - [Job - 32354] AI Solution Architect, Colombia", "CI&T - [Job - 32354] AI Solution Architect"),
])
def test_core_title(title, core):
    assert door._core_title(title) == core


def test_the_tail_breaks_ties_between_two_postings():
    want, full = door._title_tokens("Solutions Architect"), door._title_tokens("Solutions Architect, AI")
    both = [("Solutions Architect, Payments", "https://g/pay"), ("Solutions Architect, AI", "https://g/ai")]
    assert door._best_match(want, both, full) == ("https://g/ai", "Solutions Architect, AI")
    assert door._best_match(want, both[:1], full) == ("https://g/pay", "Solutions Architect, Payments")


# ─── finding the origin: one search, the right result ───

class _Search:
    def __init__(self, organic=None, boom=False):
        self.calls, self.organic, self.boom = [], organic or [], boom

    def __call__(self, label, url):
        self.calls.append(url)
        if self.boom:
            raise RuntimeError("bright data down")
        return {"organic": self.organic}


@pytest.fixture(autouse=True)
def fresh_board_memory(monkeypatch, tmp_path):
    monkeypatch.setattr(door, "BOARDS_FILE", tmp_path / "origin_boards.json")
    monkeypatch.setattr(door, "_boards_cache", None)


@pytest.fixture
def bd(monkeypatch):
    monkeypatch.setattr(door, "BRIGHTDATA_API_TOKEN", "t")
    monkeypatch.setattr(door, "BRIGHTDATA_ZONE", "z")


@pytest.fixture
def boards(monkeypatch):
    """The boards' public APIs, replaced: {(board, slug): [(title, url)]}; records every call."""
    table, calls = {}, []

    def postings(board, slug):
        calls.append((board, slug))
        return table.get((board, slug), [])
    monkeypatch.setattr(door, "_board_postings", postings)
    return table, calls


def test_origin_is_the_same_posting_on_a_board(bd, boards, monkeypatch):
    s = _Search([
        {"title": "[Job - 32354] AI Solution Architect, Brazil - DailyRemote", "link": DAILYREMOTE},
        {"title": "[Job-00024] Senior AI Architect, Brazil", "link": "https://jobs.lever.co/ciandt/208c24f9"},
        {"title": ORIGIN_TITLE, "link": LEVER},
    ])
    monkeypatch.setattr(door, "_bd_search", s)
    assert door._find_origin(COPY_TITLE, "CI&T") == (LEVER, ORIGIN_TITLE)
    assert len(s.calls) == 1 and boards[1] == []                    # one paid search, no API needed
    assert "q=32354+AI+Solution+Architect+CI%26T" in s.calls[0]      # the title as words, no brackets; "job" is a stop word
    assert "site%3Alever.co" in s.calls[0]                          # "restricted" to the origin boards


def test_the_board_index_leads_to_the_boards_own_api(bd, boards, monkeypatch):
    # Measured 24 Oct: Google's top 10 for this job had Workday, Builtin, LinkedIn and the CI&T Lever
    # board INDEX — not the Lever posting. The index names the board; the board's API has the posting.
    table, calls = boards
    table[("lever", "ciandt")] = [
        ("[Job-00024] Senior AI Architect, Brazil", "https://jobs.lever.co/ciandt/208c24f9"),
        ("[Job - 29399] AI Solutions Architect, Brazil", "https://jobs.lever.co/ciandt/c9b74739"),
        (ORIGIN_TITLE, LEVER),
    ]
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": "[Job - 32354] AI Solution Architect, Colombia - CI&T", "link": "https://builtin.com/job/job-32354"},
        {"title": "Open positions | CI&T", "link": "https://ciandt.com/us/en-us/careers/open-positions"},
        {"title": "CI&T", "link": "https://jobs.lever.co/ciandt"},
        {"title": "AI Solution Architect, Brazil en CI&T — Colombia", "link": "https://co.linkedin.com/jobs/view/1"},
    ]))
    assert door._find_origin(COPY_TITLE, "CI&T") == (LEVER, ORIGIN_TITLE)
    assert calls[0] == ("lever", "ciandt")                           # the board Google showed, first


def test_a_guessed_slug_is_tried_when_google_shows_no_board(bd, boards, monkeypatch):
    table, calls = boards
    table[("greenhouse", "coderoad")] = [("Agentic AI Engineer", "https://job-boards.greenhouse.io/coderoad/jobs/4414020009")]
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": "Agentic AI Engineer at CodeRoad", "link": "https://www.remoterocketship.com/x/1"},
    ]))
    assert door._find_origin("Agentic AI Engineer at CodeRoad", "CodeRoad") == \
        ("https://job-boards.greenhouse.io/coderoad/jobs/4414020009", "Agentic AI Engineer")
    assert calls == [("lever", "coderoad"), ("greenhouse", "coderoad")]   # stops at the first hit


def test_another_role_at_the_same_company_is_not_the_origin(bd, boards, monkeypatch):
    table, _ = boards
    table[("lever", "ciandt")] = [
        ("[Job-23029] Solutions Architect, Brazil", "https://jobs.lever.co/ciandt/00e82872"),
        ("[Job - 29399] AI Solutions Architect, Brazil", "https://jobs.lever.co/ciandt/c9b74739"),
    ]
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": "[Job-23029] Solutions Architect, Brazil", "link": "https://jobs.lever.co/ciandt/00e82872"},
        {"title": "[Job-30896] System Architect, Brazil", "link": "https://jobs.lever.co/ciandt/e65c5314"},
    ]))
    assert door._find_origin(COPY_TITLE, "CI&T") is None


def test_an_aggregator_in_the_answer_is_never_the_origin(bd, boards, monkeypatch):
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": COPY_TITLE, "link": DAILYREMOTE},
        {"title": COPY_TITLE, "link": "https://www.remoterocketship.com/x/1"},
    ]))
    assert door._find_origin(COPY_TITLE, "CI&T") is None


@pytest.mark.parametrize("link, expected", [
    (LEVER, ("lever", "ciandt")),
    ("https://jobs.lever.co/ciandt", ("lever", "ciandt")),
    ("https://jobs.eu.lever.co/deuna/1", ("lever", "deuna")),
    ("https://acme.lever.co/1", ("lever", "acme")),
    ("https://job-boards.greenhouse.io/coderoad/jobs/4414020009", ("greenhouse", "coderoad")),
    ("https://boards.greenhouse.io/embed/job_app?for=minted&token=1", ("greenhouse", "minted")),
    ("https://jobs.ashbyhq.com/n8n/abc", ("ashby", "n8n")),
    ("https://wellfound.com/company/testfyra/jobs/1", None),         # no public API
    (DAILYREMOTE, None),
])
def test_board_slug(link, expected):
    assert door._board_slug(link) == expected


def test_board_apis_are_read_and_a_failure_is_empty(monkeypatch):
    class R:
        ok = True
        def __init__(self, body): self._b = body
        def json(self): return self._b
    seen = []

    def get(url, timeout):
        seen.append(url)
        if "lever" in url:
            return R([{"text": ORIGIN_TITLE, "hostedUrl": LEVER}])
        if "greenhouse" in url:
            return R({"jobs": [{"title": "Agentic AI Engineer", "absolute_url": "https://g/1"}]})
        raise RuntimeError("down")
    monkeypatch.setattr(door.requests, "get", get)
    assert door._board_postings("lever", "ciandt") == [(ORIGIN_TITLE, LEVER)]
    assert door._board_postings("greenhouse", "coderoad") == [("Agentic AI Engineer", "https://g/1")]
    assert door._board_postings("ashby", "n8n") == []
    assert seen[0] == "https://api.lever.co/v0/postings/ciandt?mode=json&limit=500"


def test_no_search_without_bright_data(monkeypatch):
    s = _Search()
    monkeypatch.setattr(door, "_bd_search", s)
    monkeypatch.setattr(door, "BRIGHTDATA_API_TOKEN", "")
    assert door._find_origin(COPY_TITLE, "CI&T") is None and s.calls == []


def test_a_failed_search_is_none_not_a_crash(bd, monkeypatch):
    monkeypatch.setattr(door, "_bd_search", _Search(boom=True))
    assert door._find_origin(COPY_TITLE, "CI&T") is None


# ─── end to end: the gate reads the origin, the deal carries the origin ───

@pytest.fixture
def ingest(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(door, "STATE_FILE", tmp_path / "seen.json")
    monkeypatch.setattr(door, "JOBS_QUERIES", ["q"])
    monkeypatch.setattr(door, "_GATE_AVAILABLE", False)
    monkeypatch.setattr(door, "_salary_verdict", lambda *a, **k: ("unknown", None, ""))
    monkeypatch.setattr(door, "record_judged_posting", lambda *a, **k: False)
    monkeypatch.setattr(door, "_borderline_check", lambda *a, **k: (False, ""))
    monkeypatch.setattr(door.time, "sleep", lambda s: None)
    monkeypatch.setitem(sys.modules, "src.core.learned_rules",
                        types.SimpleNamespace(learned_veto=lambda *a, **k: (False, "")))
    monkeypatch.setitem(sys.modules, "src.core.llm_judge",
                        types.SimpleNamespace(judge_fit=lambda *a, **k: (True, "fits")))
    caplog.set_level(logging.INFO, logger=door.log.name)
    pushes, reads, judged = [], [], []

    def run(jobs, origin):
        monkeypatch.setattr(door, "fetch_google_jobs", lambda q: jobs)
        monkeypatch.setattr(door, "_find_origin", lambda t, c: origin)

        def read(title, url, desc):
            reads.append(url)
            return ("Colombia / Homeoffice. Fluent English (written and spoken) and Spanish. " * 20, False)
        monkeypatch.setattr(door, "_read_full_posting", read)

        def fit(title, location, desc):
            judged.append(desc)
            return True
        monkeypatch.setattr(door, "iron_clad_fit", fit)

        def push(payload):
            pushes.append(payload)
            return 200, {"ok": True, "hubspot": {"dealId": "1"}}
        monkeypatch.setattr(door, "push_crm_event", push)
        door.ingest_once()
        return caplog.text
    return run, pushes, reads, judged


def _copy():
    return {"title": COPY_TITLE, "company_name": "CI&T", "location": "",
            "description": "Remote, Brazil. Apply now on DailyRemote Premium.", "related_links": [{"link": DAILYREMOTE}]}


def test_the_copy_is_resolved_and_the_origin_is_judged(ingest):
    run, pushes, reads, judged = ingest
    text = run([_copy()], origin=(LEVER, ORIGIN_TITLE))
    assert reads == [LEVER]                                         # the origin was read, not the copy
    assert judged and "Spanish" in judged[0] and "DailyRemote" not in judged[0]
    assert [p["jobUrl"] for p in pushes] == [LEVER]                 # the deal carries the origin
    assert pushes[0]["jobTitle"] == ORIGIN_TITLE and pushes[0]["company"] == "CI&T"
    assert "aggregator dailyremote.com -> origin " + LEVER in text


def test_no_origin_means_no_deal(ingest):
    run, pushes, reads, judged = ingest
    text = run([_copy()], origin=None)
    assert pushes == [] and reads == [] and judged == []
    assert "aggregator dailyremote.com, origin not found — skipped: " + COPY_TITLE in text
    assert DAILYREMOTE in text                                      # the URL is logged for a hand check


def test_an_off_lane_copy_costs_no_search(ingest):
    run, pushes, reads, judged = ingest
    job = _copy()
    job["title"] = "Senior QA Automation Engineer at Acme"
    text = run([job], origin=(LEVER, ORIGIN_TITLE))     # an origin the search would have found
    assert pushes == [] and reads == [] and "off-lane — skipped" in text
    assert "-> origin" not in text                       # the search was never consulted


def test_a_board_result_is_untouched(ingest):
    run, pushes, reads, judged = ingest
    job = _copy()
    job["title"], job["related_links"] = ORIGIN_TITLE, [{"link": LEVER}]
    text = run([job], origin=(("never", "called")))
    assert reads == [LEVER] and [p["jobUrl"] for p in pushes] == [LEVER]
    assert "aggregator" not in text


def test_the_employers_own_site_is_untouched(ingest):
    run, pushes, reads, judged = ingest
    job = _copy()
    job["title"], job["company_name"] = "Solutions Architect, AI at Stripe", "Stripe"
    job["related_links"] = [{"link": "https://stripe.com/jobs/listing/solutions-architect-ai/1"}]
    text = run([job], origin=None)
    assert reads == ["https://stripe.com/jobs/listing/solutions-architect-ai/1"] and len(pushes) == 1
    assert "aggregator" not in text


def test_the_origin_is_remembered_so_it_is_not_a_second_deal(ingest, tmp_path):
    run, pushes, reads, judged = ingest
    run([_copy()], origin=(LEVER, ORIGIN_TITLE))
    seen = door.load_seen()
    assert door.job_id({"title": ORIGIN_TITLE, "company_name": "CI&T", "location": ""}) in seen
    assert door.job_id(_copy()) in seen


# ─── the board memory: a company's board, learned once, used free ───

def test_a_board_result_teaches_the_companys_board(bd, boards, monkeypatch):
    # 24 Oct, live on Oracle: the same search answered the Lever posting on one run and nothing on the
    # next (Bright Data empty body). A board learned from ANY earlier result makes the next copy of
    # that company's job resolvable without a search at all.
    table, calls = boards
    table[("lever", "ciandt")] = [(ORIGIN_TITLE, LEVER)]
    door._remember_board("CI&T", "https://jobs.lever.co/ciandt/09ffa3a5")
    s = _Search()                                                   # would answer nothing
    monkeypatch.setattr(door, "_bd_search", s)
    assert door._find_origin(COPY_TITLE, "CI&T") == (LEVER, ORIGIN_TITLE)
    assert s.calls == [] and calls == [("lever", "ciandt")]         # no paid search


def test_the_memory_works_without_bright_data(boards, monkeypatch):
    table, _ = boards
    table[("lever", "ciandt")] = [(ORIGIN_TITLE, LEVER)]
    door._remember_board("Ciandt", LEVER)                           # "CI&T" and "Ciandt" differ; keys do not
    monkeypatch.setattr(door, "BRIGHTDATA_API_TOKEN", "")
    assert door._find_origin(COPY_TITLE, "Ciandt") == (LEVER, ORIGIN_TITLE)
    assert door._find_origin(COPY_TITLE, "CI&T") is None            # a different key, nothing learned


def test_the_search_itself_teaches_boards(bd, boards, monkeypatch):
    monkeypatch.setattr(door, "_bd_search", _Search([{"title": "CI&T", "link": "https://jobs.lever.co/ciandt"}]))
    assert door._find_origin(COPY_TITLE, "CI&T") is None            # empty board table: nothing found
    assert door._known_boards("CI&T") == [("lever", "ciandt")]      # but the board is now known


def test_google_results_teach_boards_and_the_memory_persists(monkeypatch, tmp_path):
    monkeypatch.setattr(door, "BRIGHTDATA_API_TOKEN", "t")
    monkeypatch.setattr(door, "BRIGHTDATA_ZONE", "z")
    monkeypatch.setattr(door, "_bd_search", lambda label, url: {"organic": [
        {"title": "Agentic AI Engineer at CodeRoad", "link": "https://job-boards.greenhouse.io/coderoad/jobs/4414020009"},
        {"title": COPY_TITLE, "link": DAILYREMOTE},
    ]})
    jobs = door.fetch_google_jobs("q")
    assert [j["company_name"] for j in jobs] == ["CodeRoad", "CI&T"]
    assert door._known_boards("CodeRoad") == [("greenhouse", "coderoad")]
    assert door._known_boards("CI&T") == []                          # an aggregator teaches nothing
    door._save_boards()
    monkeypatch.setattr(door, "_boards_cache", None)                 # a new process
    assert door._known_boards("CodeRoad") == [("greenhouse", "coderoad")]
    assert "coderoad" in (tmp_path / "origin_boards.json").read_text()


def test_a_broken_memory_file_is_empty_not_a_crash(tmp_path):
    (tmp_path / "origin_boards.json").write_text("{not json")
    assert door._known_boards("CodeRoad") == []


# ─── live 24 Oct, first run after deploy: two matches that were not the same posting ───

def test_no_company_means_no_origin_search(bd, boards, monkeypatch):
    # gowithpurple.com copy "AI Implementation & Automation Engineer (Remote | LATAM …" with no company
    # was tied to Databricks' "AI Automation Engineer". Nothing proves a title-only match is the same job.
    s = _Search([{"title": "AI Automation Engineer", "link": "https://job-boards.greenhouse.io/databricks/jobs/8829033002"}])
    monkeypatch.setattr(door, "_bd_search", s)
    assert door._find_origin("AI Implementation & Automation Engineer (Remote | LATAM ...", "") is None
    assert s.calls == [] and boards[1] == []


def test_a_near_title_is_not_the_same_posting(bd, boards, monkeypatch):
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": "AI Automation Engineer", "link": "https://job-boards.greenhouse.io/databricks/jobs/8829033002"}]))
    assert door._find_origin("AI Implementation & Automation Engineer (Remote | LATAM ...", "Purple") is None


def test_a_board_index_is_not_a_posting_but_names_the_board(bd, boards, monkeypatch):
    # Google answered job-boards.greenhouse.io/stripe?error=true WITH the posting's title.
    table, calls = boards
    table[("greenhouse", "stripe")] = [("Solutions Architect, AI", "https://job-boards.greenhouse.io/stripe/jobs/7100")]
    monkeypatch.setattr(door, "_bd_search", _Search([
        {"title": "Stripe Careers | Solutions Architect, AI", "link": "https://job-boards.greenhouse.io/stripe?error=true"}]))
    assert door._find_origin("Stripe Careers | Solutions Architect, AI", "Stripe") ==         ("https://job-boards.greenhouse.io/stripe/jobs/7100", "Solutions Architect, AI")
    assert calls == [("greenhouse", "stripe")]


@pytest.mark.parametrize("link, posting", [
    (LEVER, True), ("https://acme.lever.co/abc", True), ("https://jobs.lever.co/ciandt", False),
    ("https://job-boards.greenhouse.io/stripe/jobs/7100", True), ("https://job-boards.greenhouse.io/stripe?error=true", False),
    ("https://boards.greenhouse.io/stripe", False), ("https://jobs.ashbyhq.com/n8n/abc", True), ("https://jobs.ashbyhq.com/n8n", False),
    ("https://wellfound.com/jobs/4271025-platform-engineer", True), ("https://wellfound.com/company/testfyra", False),
    (DAILYREMOTE, False),
])
def test_posting_url(link, posting):
    assert door._is_posting_url(link) is posting
