"""The screenshot she attaches to a No-fit note (judge_feedback_sync._read_screenshot). Added 2026-10-15.

Pursuit (Data & AI Systems Manager): note "Look why" + 2 screenshots. gpt-4o-mini answered NONE for the
header ("New York City") and the NONE was cached forever; the second screenshot ("Tu - Th on site in Long
Island City") was never read. The reason she gave never reached the ledger.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("jfs_shots", ROOT / "scripts" / "judge_feedback_sync.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._read_env_file = lambda path, name: "k"           # both providers "configured"
    m._file_bytes = lambda key, fid: (b"\xff\xd8 fake", "image/jpeg") if fid.startswith("img") else (None, "")
    return m


def test_one_models_none_gets_a_second_opinion_and_every_image_is_read():
    m = _load()
    m._vision_openai = lambda k, mime, b64: "NONE"
    seen = []
    m._vision_gemini = lambda k, mime, b64: seen.append(1) or f"reading {len(seen)}"
    cache = {}
    out = m._read_screenshot("key", ["pdf-cv", "img-header", "img-details"], cache)
    assert out == "reading 1 | reading 2"
    assert cache == {"img-header": "reading 1", "img-details": "reading 2"}


def test_none_from_every_provider_is_cached_empty_and_a_failure_is_not_cached():
    m = _load()
    m._vision_openai = lambda k, mime, b64: "NONE"
    m._vision_gemini = lambda k, mime, b64: "NONE — a chat window"
    cache = {}
    assert m._read_screenshot("key", ["img-chat"], cache) == ""
    assert cache == {"img-chat": ""}

    def boom(k, mime, b64):
        raise RuntimeError("HTTP 429")
    m._vision_openai = m._vision_gemini = boom
    cache = {}
    assert m._read_screenshot("key", ["img-later"], cache) == ""
    assert cache == {}                                   # the next run tries again


def test_on_site_and_must_live_in_teach_the_location_lesson():
    m = _load()
    loc = next(k for k in m._LESSON_KINDS if k[0] == "location")
    import re
    for text in ("Candidates must live or work in New York City",
                 "Tuesday-Thursday on site in Long Island City", "hybrid, 3 days in office"):
        assert re.search(loc[2], text, re.I), text
