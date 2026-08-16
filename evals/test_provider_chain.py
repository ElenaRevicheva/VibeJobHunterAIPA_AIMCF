"""
Layer 5 — provider chain reliability.

What this tests:
  - Whether EACH provider in the judge's fallback chain can physically do the
    judge's job: return a non-empty, parseable {"fit": bool, "reason": str}
    at the SAME max_tokens the judge really uses.
  - This is a different question from Layer 4. Layer 4 asks "is the verdict
    good?". This asks "did we get a verdict at all?" — the failure that
    actually bites, because an empty answer makes judge_fit() fail open.

Why it exists (August 2026):
  Groq retired llama-3.3-70b-versatile and every replacement on the free tier
  is a REASONING model. Given a small max_tokens they spend the whole budget
  thinking privately and return content:"". The judge asked for 120 tokens, so
  the moment GROQ_MODEL flipped, its Groq leg would have returned nothing on
  every call — silently, with a JUDGE_UNAVAILABLE tag, approving jobs it never
  actually read. Measured floor for openai/gpt-oss-120b: it needs >=200 tokens
  to emit any content at all.

  So the rule this file enforces: a provider is only in the chain if it can
  answer at the budget we give it. Raising max_tokens is free for plain models
  (they stop when done) and is the price of admission for reasoning ones.

What this does NOT test:
  - Verdict quality or agreement with the scorer (that is Layer 4)
  - Keyword scoring, bias compensation, routing (Layers 1-3)

Cost: a few cents at most — one short call per configured provider.
Run time: 5-20 seconds (network-bound).
When to run:
  - BEFORE and AFTER changing any model id or provider order
  - After a provider announces a deprecation
  - Whenever the judge starts reporting JUDGE_UNAVAILABLE

Requires: at least one provider key. Providers without a key are SKIPPED,
never failed — a missing key is a config choice, not a regression.
"""
import json
import os
import re
import urllib.request

import pytest

# The judge's real contract: ONLY JSON, nothing else.
JUDGE_PROMPT = (
    "You judge whether Elena should apply to a job. She is a hands-on AI builder "
    "and architect in Panama, remote-first, floor $3,000/mo.\n\n"
    "JOB:\nTitle: Senior AI Automation Engineer\nCompany: Truelogic\n"
    "Location: Remote (LATAM)\n"
    "Description: Build LLM workflows and CRM automation for US clients. "
    "Fully remote, open to candidates in Latin America.\n\n"
    'Respond with ONLY JSON, nothing else: {"fit": true or false, "reason": "<one short sentence>"}'
)

# The budget the judge actually sends. Kept in sync with llm_judge._post().
# Overridable so the same test can demonstrate the before/after:
#   JUDGE_MAX_TOKENS=120 pytest ...   → the old budget, reasoning models return ""
#   JUDGE_MAX_TOKENS=300 pytest ...   → the new budget, every provider answers
JUDGE_MAX_TOKENS = int(os.environ.get("JUDGE_MAX_TOKENS", "300"))


def _key(name: str) -> str:
    """Same resolution order as llm_judge._key — env first, then the repo .env."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        from pathlib import Path

        from dotenv import dotenv_values

        return (dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(name) or "").strip()
    except Exception:
        return ""


def _openai_style(url: str, key: str, model: str, headers: dict | None = None) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": JUDGE_PROMPT}],
            "max_tokens": JUDGE_MAX_TOKENS,
            "temperature": 0,
        }
    ).encode()
    h = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    h.update(headers or {})
    req = urllib.request.Request(url, data=payload, method="POST", headers=h)
    raw = urllib.request.urlopen(req, timeout=30).read().decode()
    return json.loads(raw)["choices"][0]["message"]["content"] or ""


def _gemini(key: str, model: str) -> str:
    payload = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": JUDGE_PROMPT}]}],
            "generationConfig": {"maxOutputTokens": JUDGE_MAX_TOKENS, "temperature": 0},
        }
    ).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    req = urllib.request.Request(
        url, data=payload, method="POST", headers={"Content-Type": "application/json"}
    )
    raw = urllib.request.urlopen(req, timeout=30).read().decode()
    cands = json.loads(raw).get("candidates") or [{}]
    parts = (cands[0].get("content") or {}).get("parts") or [{}]
    return parts[0].get("text") or ""


def _anthropic(key: str, model: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "max_tokens": JUDGE_MAX_TOKENS,
            "messages": [{"role": "user", "content": JUDGE_PROMPT}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    raw = urllib.request.urlopen(req, timeout=30).read().decode()
    blocks = [b for b in json.loads(raw).get("content", []) if b.get("type") == "text"]
    return "".join(b.get("text", "") for b in blocks)


def _call(provider: str) -> str:
    if provider == "openai":
        return _openai_style(
            "https://api.openai.com/v1/chat/completions",
            _key("OPENAI_API_KEY"),
            os.environ.get("OPENAI_JUDGE_MODEL", "gpt-4o-mini"),
        )
    if provider == "gemini":
        return _gemini(_key("GEMINI_API_KEY"), os.environ.get("GEMINI_JUDGE_MODEL", "gemini-3.5-flash-lite"))
    if provider == "groq":
        return _openai_style(
            "https://api.groq.com/openai/v1/chat/completions",
            _key("GROQ_API_KEY"),
            os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            {"User-Agent": "Mozilla/5.0 (VJH eval)"},
        )
    if provider == "grok":
        return _openai_style(
            "https://api.x.ai/v1/chat/completions",
            _key("XAI_API_KEY"),
            os.environ.get("XAI_MODEL", "grok-4.20-0309-non-reasoning"),
        )
    if provider == "claude":
        return _anthropic(_key("ANTHROPIC_API_KEY"), os.environ.get("CLAUDE_JUDGE_MODEL", "claude-haiku-4-5-20251001"))
    raise AssertionError(f"unknown provider {provider}")


KEY_FOR = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "grok": "XAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


def _extract_verdict(text: str) -> dict:
    """The judge accepts JSON anywhere in the reply — mirror that leniency here."""
    m = re.search(r"\{.*\}", text, re.S)
    assert m, f"no JSON object found in reply: {text[:200]!r}"
    return json.loads(m.group(0))


@pytest.mark.parametrize("provider", ["openai", "gemini", "groq", "grok", "claude"])
def test_provider_returns_usable_verdict(provider: str):
    """Every configured provider must return parseable JSON with a boolean 'fit'.

    An empty reply is the specific failure this guards against: judge_fit() turns
    it into a fail-open 'fit=True' tagged JUDGE_UNAVAILABLE, which looks like an
    endorsement of a job nobody read.
    """
    if not _key(KEY_FOR[provider]):
        pytest.skip(f"{provider}: no API key configured")

    text = _call(provider)

    assert text.strip(), (
        f"{provider} returned EMPTY at max_tokens={JUDGE_MAX_TOKENS} — "
        "this fails the judge open; raise the budget or drop the provider"
    )
    verdict = _extract_verdict(text)
    assert isinstance(verdict.get("fit"), bool), f"{provider}: 'fit' is not a boolean: {verdict!r}"
    assert str(verdict.get("reason", "")).strip(), f"{provider}: empty reason"
