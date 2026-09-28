"""RAG memory for the judge (2026-09-28): her verdicts on the most SIMILAR past postings.

No API calls: a bag-of-words embedding stands in for text-embedding-3-small, so similar postings
really are similar vectors. Every database is a temp file.
"""
import hashlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")      # find_posting lives in database_models (Oracle venv)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core import decision_memory as dm  # noqa: E402
from src.core import llm_judge  # noqa: E402
from src.database.database_models import record_judged_posting  # noqa: E402


def fake_embed(text, dim=64):
    v = [0.0] * dim
    for w in (text or "").lower().split():
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1.0
    return v if any(v) else None


@pytest.fixture
def world(tmp_path):
    db = tmp_path / "app.db"
    url = f"sqlite:///{db.as_posix()}"
    posts = {
        "https://j/1": ("AI Automation Engineer", "Manukora", "Build AI automation workflows with agents and n8n"),
        "https://j/2": ("AI Automation Engineer", "Contractor Pros", "AI automation workflows, Make and agents"),
        "https://j/3": ("Senior Java Engineer", "Bank", "Java Spring microservices backend banking"),
        "https://j/4": ("Video Editor", "Studio", "Premiere After Effects editing footage"),
    }
    for u, (t, c, d) in posts.items():
        record_judged_posting(t, c, u, "Remote", d, db_url=url)
    ledger = {
        "1": {"title": "AI Automation Engineer @ Manukora", "company": "Manukora", "stage": "contractsent", "url": "https://j/1"},
        "2": {"title": "AI Automation Engineer @ Contractor Pros", "company": "Contractor Pros", "stage": "presentationscheduled",
              "applied": True, "url": "https://j/2"},
        "3": {"title": "Senior Java Engineer @ Bank", "company": "Bank", "stage": "closedlost",
              "why": "her reason: manual coding required", "url": "https://j/3"},
        "4": {"title": "Video Editor @ Studio", "company": "Studio", "stage": "appointmentscheduled", "url": "https://j/4"},
    }
    return db, ledger


def test_index_embeds_decided_postings_once(world):
    db, ledger = world
    s = dm.index_decisions(ledger, db_path=db, embed=fake_embed)
    assert s == {"decided_with_posting": 3, "already": 0, "embedded_now": 3, "failed": 0}   # #4 is undecided
    assert dm.index_decisions(ledger, db_path=db, embed=fake_embed)["embedded_now"] == 0     # idempotent


def test_most_similar_first_and_labelled(world):
    db, ledger = world
    dm.index_decisions(ledger, db_path=db, embed=fake_embed)
    hits = dm.similar_decisions("AI Automation Lead", "NewCo", "Remote", "AI automation workflows with agents",
                                ledger=ledger, db_path=db, embed=fake_embed, min_sim=0.0)
    assert [h["label"] for h in hits[:2]] == ["APPLIED", "APPLIED"]
    assert hits[-1]["title"].startswith("Senior Java Engineer") and hits[-1]["label"] == "REJECTED"


def test_never_retrieves_itself(world):
    db, ledger = world
    dm.index_decisions(ledger, db_path=db, embed=fake_embed)
    hits = dm.similar_decisions("AI Automation Engineer", "Manukora", "Remote", "Build AI automation workflows",
                                exclude_url="https://j/1", ledger=ledger, db_path=db, embed=fake_embed, min_sim=0.0)
    assert all("Manukora" not in h["title"] for h in hits)
    # the same job re-posted under a NEW url is still itself
    hits2 = dm.similar_decisions("AI Automation Engineer", "Manukora", "Remote", "Build AI automation workflows",
                                 exclude_url="https://j/other", ledger=ledger, db_path=db, embed=fake_embed, min_sim=0.0)
    assert all("Manukora" not in h["title"] for h in hits2)


def test_applied_only_variant_returns_only_applications(world):
    db, ledger = world
    dm.index_decisions(ledger, db_path=db, embed=fake_embed)
    hits = dm.similar_decisions("Java Backend Engineer", "Other", "Remote", "Java Spring backend",
                                ledger=ledger, db_path=db, embed=fake_embed, min_sim=0.0, labels=("APPLIED",))
    assert hits and all(h["label"] == "APPLIED" for h in hits)


def test_fail_safe(world, tmp_path):
    db, ledger = world
    assert dm.similar_decisions("x", "y", "", "text", ledger=ledger, db_path=db, embed=lambda t: None) == []
    assert dm.similar_block("x", "y", "", "text", ledger=ledger, db_path=db, embed=lambda t: None) == ""
    bad = tmp_path / "no" / "such" / "dir" / "x.db"
    assert dm.similar_decisions("x", "y", "", "text", ledger=ledger, db_path=bad, embed=fake_embed) == []


def test_block_shows_her_reason_not_vjh_text(world):
    db, ledger = world
    dm.index_decisions(ledger, db_path=db, embed=fake_embed)
    b = dm.similar_block("Java Backend Engineer", "Other", "Remote", "Java Spring backend",
                         ledger=ledger, db_path=db, embed=fake_embed, min_sim=0.0)
    assert "She REJECTED: Senior Java Engineer @ Bank — her reason: manual coding required" in b
    assert "retrieved by meaning" in b


FEEDBACK = ("ELENA'S LESSONS — learned from her own rejections.\n  - lesson one\n\n"
            "REAL RECENT OUTCOMES from Elena's own pipeline (refreshed hourly):\nShe APPLIED to these (fit):\n"
            "  - Recent A\nShe REJECTED these (not fit) — pay attention to WHY:\n  - Recent B\n"
            "REMINDER: a listing SILENT on location or eligibility is open to her (criterion 2).\n\n")


def test_similar_replaces_only_the_recent_examples():
    out = llm_judge._with_similar(FEEDBACK, "HER OWN VERDICTS ON THE MOST SIMILAR PAST POSTINGS\n  - x")
    assert "lesson one" in out and "REMINDER: a listing SILENT" in out
    assert "Recent A" not in out and "Recent B" not in out
    assert out.index("lesson one") < out.index("HER OWN VERDICTS") < out.index("REMINDER")
    assert llm_judge._with_similar(FEEDBACK, "") == FEEDBACK


def test_default_mode_leaves_the_prompt_untouched(monkeypatch):
    monkeypatch.setattr(llm_judge, "_key", lambda name: "")
    assert llm_judge._examples_mode() == "recent"
    seen = {}
    monkeypatch.setattr(llm_judge, "_call_llm", lambda p: (seen.setdefault("p", p) and "", ["no provider"]))
    monkeypatch.setattr(dm, "similar_block", lambda *a, **k: pytest.fail("RAG ran in recent mode"))
    llm_judge.judge_fit("AI Lead", "Co", "Remote", "desc")
    assert "HER OWN VERDICTS" not in seen["p"]
