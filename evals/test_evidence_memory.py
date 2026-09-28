"""Evidence memory (2026-09-28): every decision keeps the posting it was made on.

Until this, job_listings had 0 rows and add_job_listing() had 0 callers, so the judge replay judged
Elena's past decisions on an EMPTY listing. These tests pin the pieces that connect the existing
table to the doors (record), the ledger (url), LangGraph's checkpoints (backfill) and the replay
(read). No API calls, no production data: every database here is a temp file.
"""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")      # installed in the Oracle venv; skipped where it is not

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from src.database.database_models import find_posting, record_judged_posting  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def db(tmp_path):
    return "sqlite:///" + (tmp_path / "app.db").as_posix()


# ── the store ────────────────────────────────────────────────────────────────
def test_record_then_find_by_url(db):
    assert record_judged_posting("AI Automation Lead", "Acme", "https://jobs.example/1", "Remote - LATAM",
                                 "Design agent workflows.", "serpapi_jobs", db_url=db)
    p = find_posting(url="https://jobs.example/1", db_url=db)
    assert p["description"] == "Design agent workflows." and p["location"] == "Remote - LATAM"


def test_first_text_is_kept(db):
    # The judge ruled on the FIRST text; a later re-sighting must not rewrite the evidence.
    record_judged_posting("T", "C", "https://jobs.example/2", "", "first text", db_url=db)
    record_judged_posting("T", "C", "https://jobs.example/2", "", "second text", db_url=db)
    assert find_posting(url="https://jobs.example/2", db_url=db)["description"] == "first text"
    con = sqlite3.connect((db[len("sqlite:///"):]))
    assert con.execute("select count(*) from job_listings").fetchone()[0] == 1


def test_find_by_title_and_company_when_no_url(db):
    record_judged_posting("AI Ops Lead", "Niuro", "", "Remote", "text", db_url=db)
    assert find_posting(title="AI Ops Lead", company="Niuro", db_url=db)["description"] == "text"
    assert find_posting(url="https://nowhere/", db_url=db) is None


def test_fail_safe_on_an_unusable_database(tmp_path):
    bad = "sqlite:///" + (tmp_path / "no" / "such" / "dir" / "x.db").as_posix()
    assert record_judged_posting("T", "C", "https://x/", "", "d", db_url=bad) is False   # no raise
    assert find_posting(url="https://x/", db_url=bad) is None
    assert record_judged_posting("", "C", "https://x/", "", "d") is False                # no title


# ── the ledger carries the join key ──────────────────────────────────────────
def test_job_url_parsed_from_deal_description():
    s = _load("sync_ev", "scripts/judge_feedback_sync.py")
    desc = "Category: hiring\nStage: I Act TODAY\nJob URL: https://jobs.ashbyhq.com/agent/8fff\nSource: serpapi_jobs"
    assert s._job_url(desc) == "https://jobs.ashbyhq.com/agent/8fff"
    assert s._job_url("Category: hiring") == "" and s._job_url(None) == ""


def test_unchanged_ledger_entries_get_their_url_without_refetching_notes(monkeypatch):
    s = _load("sync_ev2", "scripts/judge_feedback_sync.py")
    monkeypatch.setattr(s, "_fetch_notes_batch", lambda *a, **k: pytest.fail("notes refetched"))
    old = {"7": {"title": "AI Lead @ X", "company": "X", "prefix": "HIRING-VJH-LEAD", "stage": "closedlost",
                 "modified": "2026-09-01T00:00:00Z", "first_decided": "2026-09-01T00:00:00Z",
                 "why": "her reason: closed", "applied": None}}
    deals = [{"id": "7", "properties": {"dealname": "[HIRING-VJH-LEAD] AI Lead @ X", "dealstage": "closedlost",
                                        "hs_lastmodifieddate": "2026-09-01T00:00:00Z",
                                        "description": "Job URL: https://jobs.example/7"}}]
    ledger, refreshed, _ = s._update_ledger("key", deals, old, {})
    assert ledger["7"]["url"] == "https://jobs.example/7"
    assert ledger["7"]["why"] == "her reason: closed" and refreshed == 0


# ── LangGraph's checkpoints are the history ──────────────────────────────────
def test_checkpoint_postings_decodes_real_langgraph_rows(tmp_path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    le = _load("link_ev", "scripts/link_evidence.py")
    path = tmp_path / "ckpt.db"
    con = sqlite3.connect(str(path), check_same_thread=False)
    saver = SqliteSaver(con)
    saver.setup()
    state = {"title": "AI Automation Lead", "company": "Acme", "location": "Remote - LATAM",
             "description": "<p>Design agent workflows.</p>", "url": "https://jobs.example/9"}
    for i, (ch, v) in enumerate(state.items()):
        typ, val = saver.serde.dumps_typed(v)
        con.execute("INSERT INTO writes VALUES (?,?,?,?,?,?,?,?)", ("vjh_x_9", "", "c1", "t1", i, ch, typ, val))
    con.commit()
    con.close()
    got = le._checkpoint_postings({"https://jobs.example/9", "https://jobs.example/absent"}, path)
    assert set(got) == {"https://jobs.example/9"}
    assert got["https://jobs.example/9"]["description"] == "<p>Design agent workflows.</p>"   # raw, as judged
    assert got["https://jobs.example/9"]["thread"] == "vjh_x_9"


def test_link_evidence_fills_only_what_is_missing(db, tmp_path, monkeypatch):
    le = _load("link_ev2", "scripts/link_evidence.py")
    record_judged_posting("Old", "C", "https://jobs.example/old", "", "kept", db_url=db)
    monkeypatch.setattr(le, "_checkpoint_postings", lambda urls, p=None: {
        u: {"title": "New", "company": "C", "location": "Remote", "description": "from checkpoint", "thread": "t"}
        for u in urls if u.endswith("/new")})
    ledger = {"1": {"url": "https://jobs.example/old"}, "2": {"url": "https://jobs.example/new"},
              "3": {"url": "https://jobs.example/gone"}, "4": {"url": ""}}
    s = le.link_evidence(ledger, db_url=db)
    assert s == {"decisions": 4, "with_url": 3, "had_evidence": 1, "linked_now": 1, "no_evidence": 1}
    assert find_posting(url="https://jobs.example/new", db_url=db)["description"] == "from checkpoint"
    assert find_posting(url="https://jobs.example/old", db_url=db)["description"] == "kept"


# ── the replay judges the posting, never an empty listing ────────────────────
def test_replay_evidence_is_the_posting_plus_her_screenshot(monkeypatch):
    rl = _load("replay_ev", "scripts/replay_learning.py")
    monkeypatch.setattr(rl, "find_posting", lambda **k: {"description": "Posting text.", "location": "Remote - LATAM"}
                        if k.get("url") == "https://jobs.example/5" else None)
    rl._POSTINGS.clear()
    e = {"title": "AI Lead @ X", "url": "https://jobs.example/5", "why": "her reason: x; her screenshot shows: Closed."}
    assert rl._evidence(e) == "Posting text.\nClosed."
    assert rl._location(e) == "Remote - LATAM"
    bare = {"title": "Other @ Y", "url": "", "why": "her reason: nope"}
    assert rl._evidence(bare) == "" and rl._posting(bare) is None       # no posting → excluded from the judge sample
