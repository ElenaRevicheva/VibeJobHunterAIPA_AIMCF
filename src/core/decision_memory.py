"""
decision_memory.py — Elena's past decisions, retrievable by MEANING (RAG for the judge).

    similar_decisions(title, company, location, desc)  → her verdicts on the most similar postings
    similar_block(...)                                  → the same, formatted for the judge prompt
    index_decisions(ledger)                             → embed decided postings not yet embedded

WHY (28 Sep 2026). The judge's examples were her 12 most RECENT applications and 12 most RECENT
rejections, whatever job it was judging. Measured on real postings it rejected roles like the ones
she applies to ("AI Automation Engineer ... hands-on coding, not her expertise") while two near-
identical AI Automation Engineer applications sat in her history. Retrieval puts THOSE in front of
it: her own verdicts on the postings most like this one.

PORTED, NOT INVENTED: this is EspaLuz's espaluz_rag.py (in production since Jan 2026 — embed with
text-embedding-3-small, cosine top-k, a similarity floor, every failure returns empty) moved onto
VJH's own SQLite app DB. The postings come from job_listings (evidence memory, link_evidence.py),
the verdicts from the ledger (judge_decisions.json). At a few hundred decisions a plain cosine in
Python is enough; pgvector would add a database for no gain.

FAIL-SAFE: no key, no network, no table, no ledger → [] / "" and the judge prompt is unchanged.
"""
import json
import re
import sqlite3
from array import array
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "autonomous_data" / "judge_decisions.json"
EMBED_MODEL = "text-embedding-3-small"
POSITIVE_STAGES = {"presentationscheduled", "contractsent", "closedwon"}   # same as judge_feedback_sync
NEGATIVE_STAGES = {"closedlost"}
_TABLE = ("CREATE TABLE IF NOT EXISTS decision_embeddings (url TEXT PRIMARY KEY, model TEXT, "
          "dim INTEGER, vec BLOB, created TEXT)")


# ── embedding (EspaLuz's call, VJH's key) ────────────────────────────────────
def _embed(text: str):
    try:
        from .llm_judge import _key
        key = _key("OPENAI_API_KEY")
    except Exception:
        return None
    if not key or not (text or "").strip():
        return None
    try:
        import requests
        r = requests.post("https://api.openai.com/v1/embeddings",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": EMBED_MODEL, "input": text[:8000]}, timeout=10)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception:
        return None


def posting_text(title: str, location: str, desc: str) -> str:
    """What gets embedded: the posting as the judge sees it, markup stripped."""
    body = re.sub(r"<[^>]+>|&[a-z#0-9]+;", " ", desc or "")
    body = re.sub(r"\s+", " ", body).strip()
    return f"{title or ''}\n{location or ''}\n{body[:3000]}".strip()


# ── storage: the app DB database_models already resolves ─────────────────────
def _db_path(db_path=None) -> str:
    if db_path:
        return str(db_path)
    from src.database.database_models import _app_db_url
    return _app_db_url()[len("sqlite:///"):]


def _connect(db_path=None):
    con = sqlite3.connect(_db_path(db_path), timeout=10)
    con.execute(_TABLE)
    return con


def _pack(vec) -> bytes:
    return array("f", vec).tobytes()


def _unpack(blob: bytes) -> list:
    a = array("f")
    a.frombytes(blob)
    return a.tolist()


def _cos(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ── her verdicts ─────────────────────────────────────────────────────────────
def _label(e: dict):
    if e.get("stage") in NEGATIVE_STAGES:
        return "REJECTED"
    if e.get("stage") in POSITIVE_STAGES or e.get("applied"):
        return "APPLIED"
    return None


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _ledger(ledger=None) -> dict:
    if ledger is not None:
        return ledger
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))["deals"]
    except Exception:
        return {}


def index_decisions(ledger: dict = None, db_path=None, embed=None) -> dict:
    """Embed every decided posting that has evidence and no embedding yet. Never raises."""
    embed = embed or _embed
    stats = {"decided_with_posting": 0, "already": 0, "embedded_now": 0, "failed": 0}
    try:
        from src.database.database_models import find_posting
    except Exception:
        return stats
    try:
        con = _connect(db_path)
    except Exception:
        return stats
    try:
        have = {r[0] for r in con.execute("SELECT url FROM decision_embeddings")}
        for e in _ledger(ledger).values():
            url = e.get("url")
            if not url or not _label(e):
                continue
            p = find_posting(url=url, db_url=f"sqlite:///{_db_path(db_path)}")
            if not p:
                continue
            stats["decided_with_posting"] += 1
            if url in have:
                stats["already"] += 1
                continue
            vec = embed(posting_text(p["title"], p["location"], p["description"]))
            if not vec:
                stats["failed"] += 1
                continue
            con.execute("INSERT OR REPLACE INTO decision_embeddings VALUES (?,?,?,?,?)",
                        (url, EMBED_MODEL, len(vec), _pack(vec), datetime.now(timezone.utc).isoformat()))
            con.commit()
            have.add(url)
            stats["embedded_now"] += 1
    finally:
        con.close()
    return stats


def similar_decisions(title: str, company: str, location: str, desc: str, k: int = 6,
                      min_sim: float = 0.30, exclude_url: str = None, ledger: dict = None,
                      db_path=None, embed=None, labels=("APPLIED", "REJECTED")) -> list:
    """Her verdicts on the k postings most similar to this one. [] on any problem.

    Never returns the job itself: not its URL, and not another copy of the same title at the same
    company (a job re-posted under a new URL would otherwise hand the judge its own answer)."""
    embed = embed or _embed
    try:
        q = embed(posting_text(title, location, desc))
        if not q:
            return []
        con = _connect(db_path)
        try:
            rows = con.execute("SELECT url, vec FROM decision_embeddings WHERE model=?", (EMBED_MODEL,)).fetchall()
        finally:
            con.close()
        by_url = {e.get("url"): e for e in _ledger(ledger).values() if e.get("url")}
        me = f"{_norm(title)} @ {_norm(company)}"
        scored = []
        for url, blob in rows:
            e = by_url.get(url)
            if not e or url == exclude_url or _label(e) not in labels:
                continue
            t, _, c = (e.get("title") or "").rpartition(" @ ")
            if f"{_norm(t or e.get('title', ''))} @ {_norm(c or e.get('company', ''))}" == me:
                continue
            s = _cos(q, _unpack(blob))
            if s >= min_sim:
                scored.append((s, e))
        scored.sort(key=lambda x: -x[0])
        return [{"similarity": round(s, 3), "label": _label(e), "title": e.get("title", ""),
                 "why": e.get("why", "")} for s, e in scored[:k]]
    except Exception:
        return []


def _her_reason(why: str) -> str:
    """Her words only, never VJH's — the same cut the ledger already applies."""
    r = (why or "").replace("her reason:", "").strip()
    return re.sub(r"\s+", " ", r)[:160]


def similar_block(title: str, company: str, location: str, desc: str, exclude_url: str = None, **kw) -> str:
    hits = similar_decisions(title, company, location, desc, exclude_url=exclude_url, **kw)
    if not hits:
        return ""
    lines = ["HER OWN VERDICTS ON THE MOST SIMILAR PAST POSTINGS (retrieved by meaning, not by date).",
             "Weigh these: they are how SHE judged jobs like this one. A disqualifier THIS listing",
             "states still rejects, and a job she applied to is evidence the work is hers:"]
    for h in hits:
        line = f"  - [{round(h['similarity'] * 100)}% similar] She {h['label']}: {h['title'][:90]}"
        if h["label"] == "REJECTED" and _her_reason(h["why"]):
            line += f" — her reason: {_her_reason(h['why'])}"
        lines.append(line)
    return "\n".join(lines)
