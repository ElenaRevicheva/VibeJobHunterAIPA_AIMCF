"""No feature may bypass the 5-provider waterfall (src/utils/llm_chain.py).

28 Sep 2026: Anthropic credits at zero since 17 Aug. The waterfall absorbed it — but only where it
was wired. linkedin_cmo_v4 knew ONLY Claude, so every daily LinkedIn post since at least 9 Sep was a
template while logging "sent successfully"; response_detector retried dead Claude ~300x/day and,
with no Claude key, would have skipped the chain for bare keywords. These pin the fix. Offline.
"""
import asyncio

import pytest

from src.autonomous import response_detector as rd
from src.notifications import linkedin_cmo_v4 as li


# ── LinkedIn: Claude fails → the waterfall writes, never a silent template ─────
def test_linkedin_waterfall_writes_when_claude_cannot(monkeypatch):
    import src.utils.llm_chain as chain
    seen = {}

    def fake_complete(messages, max_tokens, order):
        seen["order"], seen["tokens"] = tuple(order), max_tokens
        return "A real post written by Gemini.", ["openai: HTTP Error 429"]

    monkeypatch.setattr(chain, "complete", fake_complete)
    cmo = li.LinkedInCMO.__new__(li.LinkedInCMO)
    out = asyncio.run(cmo._waterfall_text("write a post", 900, "test"))
    assert out == "A real post written by Gemini."
    assert seen["order"] == chain.PROFILE_QUALITY and seen["tokens"] == 900


def test_linkedin_waterfall_exhausted_returns_none(monkeypatch):
    import src.utils.llm_chain as chain
    monkeypatch.setattr(chain, "complete", lambda m, t, o: ("", ["openai: 401", "gemini: 400"]))
    cmo = li.LinkedInCMO.__new__(li.LinkedInCMO)
    assert asyncio.run(cmo._waterfall_text("x", 100, "test")) is None   # → template, as the last resort


def test_both_linkedin_claude_paths_fall_through_to_the_waterfall():
    from pathlib import Path
    src = Path(li.__file__).read_text(encoding="utf-8")
    assert "return await self._waterfall_text(prompt, max_tokens" in src          # daily post
    assert 'await self._waterfall_text(prompt, 600, "[CTO Integration]' in src      # tech-update post


# ── Reply detector: circuit breaker + no key ≠ keywords only ────────────────
class _DeadClaude:
    def __init__(self):
        self.calls = 0

        class _M:
            def create(inner, **kw):
                self.calls += 1
                raise Exception("Error code: 400 - Your credit balance is too low to access the Anthropic API.")
        self.messages = _M()


def _detector(client):
    d = rd.ResponseDetector.__new__(rd.ResponseDetector)
    d.anthropic_client = client
    d._groq_classify = lambda prompt: (rd.ResponseType.POSITIVE, 0.9, "openai: wants a call", "Reply")
    return d


def test_dead_claude_is_called_once_then_skipped(monkeypatch):
    monkeypatch.setattr(rd, "_anthropic_skip_until", 0.0)
    claude = _DeadClaude()
    d = _detector(claude)
    for _ in range(3):
        rtype, *_ = asyncio.run(d._ai_classify("HR", "Interview?", "Can we talk Tuesday?"))
        assert rtype == rd.ResponseType.POSITIVE          # the chain answered every time
    assert claude.calls == 1                               # not 3: the breaker tripped on "credit balance"


def test_no_claude_key_still_uses_the_chain_not_keywords(monkeypatch):
    monkeypatch.setattr(rd, "_anthropic_skip_until", 0.0)
    rtype, conf, analysis, _ = asyncio.run(_detector(None)._ai_classify("HR", "Interview?", "Can we talk?"))
    assert rtype == rd.ResponseType.POSITIVE and analysis.startswith("openai")
