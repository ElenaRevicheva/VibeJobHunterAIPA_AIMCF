"""
Shared provider fallback chain for VJH.

Why this exists (2026-08-16): message_generator and response_detector each had
Claude as primary and ONE fallback — Groq. That was fine while Groq served a
plain, fast model. Groq retired llama-3.3-70b and every free-tier replacement is
a REASONING model, so the single fallback became the least predictable link at
exactly the moment it mattered.

This module does not touch the happy path. Claude stays primary in both callers;
what changes is what happens AFTER Claude fails — instead of one shaky leg there
are four, ordered by cost and fitness.

Design rules learned the hard way today:

  1. An EMPTY or truncated reply is a FAILURE, not an answer. Reasoning models
     spend a small max_tokens budget thinking privately and return "". Handing
     that back reads like a valid response and fails callers open.
  2. Give every provider at least MIN_REASONING_TOKENS. Measured floor for
     openai/gpt-oss-120b is ~200 tokens to emit any content at all; below that
     it returns nothing or a verdict cut off mid-sentence.
  3. Plain models beat newer ones for short structured work. gpt-4o-mini and
     gemini-3.5-flash-lite answer correctly at 30 tokens; gpt-5.6-luna,
     gemini-3.7-flash and gemini-3.6-flash returned empty at the same budget.
  4. Order follows the USE CASE. Quality work pays for a good model first;
     high-volume classification puts the cheap plain models first and Claude
     last. See PROFILE_* below.

Verified by evals/test_provider_chain.py — nothing is listed here that has not
answered the real prompt at the real budget.
"""
import json
import os
import urllib.request
from typing import Iterable, List, Tuple

# Reasoning models need room before they emit anything. Anything smaller risks a
# truncated reply, which is harder to detect than an empty one.
MIN_REASONING_TOKENS = 300

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_XAI_URL = "https://api.x.ai/v1/chat/completions"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# After Claude, for work a human will read: quality first, then free, then credits.
PROFILE_QUALITY: Tuple[str, ...] = ("openai", "gemini", "groq", "grok")
# For high-volume structured work: cheap plain models first, Claude last.
PROFILE_CLASSIFY: Tuple[str, ...] = ("openai", "gemini", "groq", "grok", "claude")
# Job SCORING (job_matcher._ai_deep_analysis). Added 2026-08-18.
#
# This decides whether a job ever reaches Elena, so a missing opinion costs a real
# lead: when no provider answers, the AI-outage clamp caps the job at 54 and it is
# discarded. On 2026-08-18 that silently killed three jobs whose keyword scores were
# 81, 85 and 100 — including "AI Operations & Automation Manager, Europe/LaTAM",
# squarely in her lane.
#
# Claude sits LAST, not first. It is a genuine leg — but it is currently 400
# credit-exhausted, and a dead provider at the head of the chain buys nothing and
# costs a guaranteed-failing round trip on EVERY scored job. When credits return it
# resumes serving from the back without a code change. Same lesson the whitespace
# repo learned when a retired Groq model sat at tier 2.
PROFILE_SCORING: Tuple[str, ...] = ("openai", "gemini", "groq", "grok", "claude")


def _model(provider: str) -> str:
    """Model ids are env-overridable so the next retirement is a config change."""
    return {
        "openai": os.environ.get("OPENAI_CHAIN_MODEL", "").strip() or "gpt-4o-mini",
        "gemini": os.environ.get("GEMINI_CHAIN_MODEL", "").strip() or "gemini-3.5-flash-lite",
        "grok": os.environ.get("XAI_MODEL", "").strip() or "grok-4.20-0309-non-reasoning",
        "claude": os.environ.get("CLAUDE_CHAIN_MODEL", "").strip() or "claude-haiku-4-5-20251001",
    }.get(provider, "")


def _key(name: str) -> str:
    """Env first, then the repo .env — the bots do not always export .env."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        from pathlib import Path

        from dotenv import dotenv_values

        return (dotenv_values(Path(__file__).resolve().parents[2] / ".env").get(name) or "").strip()
    except Exception:
        return ""


def _openai_style(url: str, key: str, model: str, messages: list, max_tokens: int,
                  headers: dict | None = None) -> str:
    payload = json.dumps({
        "model": model, "messages": messages,
        "max_tokens": max_tokens, "temperature": 0.3,
    }).encode()
    h = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    h.update(headers or {})
    req = urllib.request.Request(url, data=payload, method="POST", headers=h)
    raw = urllib.request.urlopen(req, timeout=45).read().decode()
    return json.loads(raw)["choices"][0]["message"]["content"] or ""


def _gemini(key: str, model: str, messages: list, max_tokens: int) -> str:
    """Gemini has its own shape. System messages become a systemInstruction.

    No thinkingConfig on purpose: gemini-3.5-flash-lite is a PLAIN model and
    rejects thinkingBudget with a 400 — which is precisely why it was chosen.
    """
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    turns = [{"role": "user" if m.get("role") != "assistant" else "model",
              "parts": [{"text": m.get("content", "")}]}
             for m in messages if m.get("role") != "system"]
    body: dict = {
        "contents": turns or [{"role": "user", "parts": [{"text": ""}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=45).read().decode()
    cands = json.loads(raw).get("candidates") or [{}]
    parts = (cands[0].get("content") or {}).get("parts") or [{}]
    return parts[0].get("text") or ""


def _anthropic(key: str, model: str, messages: list, max_tokens: int) -> str:
    system = "\n".join(m["content"] for m in messages if m.get("role") == "system")
    turns = [m for m in messages if m.get("role") != "system"]
    body: dict = {"model": model, "max_tokens": max_tokens,
                  "messages": turns or [{"role": "user", "content": ""}]}
    if system:
        body["system"] = system
    req = urllib.request.Request(_ANTHROPIC_URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-api-key": key,
                                          "anthropic-version": "2023-06-01"})
    raw = urllib.request.urlopen(req, timeout=45).read().decode()
    blocks = [b for b in json.loads(raw).get("content", []) if b.get("type") == "text"]
    return "".join(b.get("text", "") for b in blocks)


_KEY_FOR = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "grok": "XAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


def _call(provider: str, key: str, messages: list, max_tokens: int) -> str:
    if provider == "openai":
        return _openai_style(_OPENAI_URL, key, _model("openai"), messages, max_tokens)
    if provider == "gemini":
        return _gemini(key, _model("gemini"), messages, max_tokens)
    if provider == "groq":
        from .model_config import groq_model  # THE one Groq switch (GROQ_MODEL env)
        return _openai_style(_GROQ_URL, key, groq_model(), messages, max_tokens,
                             {"User-Agent": "Mozilla/5.0 (VJH chain)"})
    if provider == "grok":
        return _openai_style(_XAI_URL, key, _model("grok"), messages, max_tokens)
    if provider == "claude":
        return _anthropic(key, _model("claude"), messages, max_tokens)
    raise ValueError(f"unknown provider {provider}")


def complete(messages: list, max_tokens: int = 1000,
             order: Iterable[str] = PROFILE_QUALITY) -> Tuple[str, List[str]]:
    """Walk the chain until a provider returns real text.

    Returns (text, errors). `errors` explains why each provider was skipped or
    failed — a missing key is as much a reason as an HTTP 500. Callers that get
    "" back know every provider failed AND can say which, instead of guessing.
    """
    budget = max(int(max_tokens), MIN_REASONING_TOKENS)
    errors: List[str] = []
    for provider in order:
        key = _key(_KEY_FOR[provider])
        if not key:
            errors.append(f"{provider}: no API key configured")
            continue
        try:
            text = _call(provider, key, messages, budget)
            if text and text.strip():
                return text, errors
            # Empty is a failure, never an answer — see rule 1 in the module docstring.
            errors.append(f"{provider}: empty response")
        except Exception as e:  # noqa: BLE001 — any failure must advance the chain
            errors.append(f"{provider}: {str(e)[:140]}")
    return "", errors
