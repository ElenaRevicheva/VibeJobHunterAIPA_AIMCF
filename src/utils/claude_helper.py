"""
Claude API Helper
Handles model selection, fallbacks, and retry with backoff for transient errors (529/503/429).
Credit-exhaustion (400): falls back to Groq (model id via model_config.groq_model()),
then to OpenAI gpt-4o-mini (added 2026-07-30 — see call_llm_fallback).
"""

import asyncio
import json
import logging
import os
import time
import urllib.request

from .model_config import groq_model  # THE one Groq model switch (GROQ_MODEL env)
from typing import Optional, Any, Set

import anthropic

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_STATUS_CODES: Set[int] = {529, 503, 429}

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class _GroqTextBlock:
    def __init__(self, text: str):
        self.text = text
        self.type = "text"


class _GroqResponse:
    """Minimal shim so callers can use .content[0].text same as Anthropic SDK."""
    def __init__(self, text: str):
        self.content = [_GroqTextBlock(text)]


def call_groq_fallback(messages: list, max_tokens: int = 4096) -> "_GroqResponse":
    """Call Groq (model id via model_config.groq_model()) when Claude returns 400 credit exhaustion.

    2026-05-27 CRITICAL FIX (Cloudflare 1010 bug):
    Previous implementation used urllib.request with no User-Agent. Cloudflare
    (which fronts api.groq.com) blocks the default `Python-urllib/x.x` UA with
    "error code: 1010", surfaced to Python as HTTP 403. This fallback was
    therefore broken on EVERY call since it shipped — resume + cover-letter
    generation in content_generator.py silently failed whenever Claude credits
    ran out. Switched to `requests` (sends a Cloudflare-permitted UA) plus an
    explicit User-Agent so it never regresses, and we log the response body on
    non-200 so provider-side blocks are debuggable from logs alone.
    """
    import requests
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Groq fallback unavailable: GROQ_API_KEY not set")
    resp = requests.post(
        _GROQ_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "VibeJobHunter/1.0 (+https://aideazz.xyz)",
        },
        json={
            "model": groq_model(),
            "messages": messages,
            "max_tokens": min(max_tokens, 4096),
            "temperature": 0.3,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        logger.error(f"[claude_helper] Groq fallback HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    logger.info("[claude_helper] Groq fallback (400 credit exhaustion) succeeded")
    return _GroqResponse(text)


# ─────────────────────────────────────────────────────────────────────────────
# OPENAI LAST-RESORT FALLBACK (added 2026-07-30)
#
# ADDITIVE ONLY. Claude and Groq behaviour is unchanged: OpenAI is tried solely
# when Groq itself raises (429 TPD / 403 / no key). Nothing that works today
# starts taking a different path.
#
# Why: Anthropic is credit-dead (400) and Groq's free tier hits its daily token
# limit mid-cycle ("TPD: Limit 100000, Used 99427"), so `job_matcher`'s deep
# analysis returned None all through June and July. As of 2026-07-30 that means
# every job is capped at 54 and nothing surfaces at all. `llm_judge` already
# uses OpenAI gpt-4o-mini successfully and has credits — this borrows the same
# proven provider for the shared helper.
#
# Cost: gpt-4o-mini at ~$0.15/1M input tokens; the job-analysis prompt is ~700
# tokens, so a full cycle of 100 jobs costs about one US cent.
# ─────────────────────────────────────────────────────────────────────────────
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_OPENAI_FALLBACK_MODEL = os.getenv("VJH_OPENAI_FALLBACK_MODEL", "gpt-4o-mini")


def _resolve_key(name: str) -> str:
    """os.environ first, then the repo .env — the bot does not always export .env
    into the process environment (same reason llm_judge._key exists)."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        from dotenv import dotenv_values
        from pathlib import Path
        return (dotenv_values(Path(__file__).resolve().parents[2] / ".env").get(name) or "").strip()
    except Exception:
        return ""


def call_openai_fallback(messages: list, max_tokens: int = 4096) -> "_GroqResponse":
    """Call OpenAI when BOTH Claude (400) and Groq (429/403) are unavailable.

    Returns the same `.content[0].text` shim as the Groq fallback, so every
    existing caller keeps working without a change.
    """
    import requests
    api_key = _resolve_key("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI fallback unavailable: OPENAI_API_KEY not set")
    resp = requests.post(
        _OPENAI_API_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "VibeJobHunter/1.0 (+https://aideazz.xyz)",
        },
        json={
            "model": _OPENAI_FALLBACK_MODEL,
            "messages": messages,
            "max_tokens": min(max_tokens, 4096),
            "temperature": 0.3,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        logger.error(f"[claude_helper] OpenAI fallback HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    logger.info(f"[claude_helper] OpenAI fallback ({_OPENAI_FALLBACK_MODEL}) succeeded")
    return _GroqResponse(text)


def call_llm_fallback(messages: list, max_tokens: int = 4096) -> "_GroqResponse":
    """Groq (free) → OpenAI (cheap). Raises only if BOTH providers fail.

    This replaces bare `call_groq_fallback(...)` at the three Claude-400 sites
    below. Groq stays FIRST so the free path is always preferred and today's
    working behaviour is preserved exactly.
    """
    try:
        return call_groq_fallback(messages, max_tokens)
    except Exception as groq_err:
        logger.warning(f"[claude_helper] Groq fallback failed ({groq_err}) — trying OpenAI")
        return call_openai_fallback(messages, max_tokens)


# Model selection priority (tries in order)
CLAUDE_MODELS = [
    "claude-sonnet-4-5-20250929",   # Latest Sonnet (current, verified live)
    "claude-sonnet-4-6",            # Newer Sonnet
    "claude-opus-4-8",              # Opus (highest quality)
    "claude-haiku-4-5-20251001",    # Haiku (fast/cheap, most reliable fallback)
]


def get_best_available_model(client, preferred_model: Optional[str] = None) -> str:
    """
    Get the best available Claude model
    
    Tries models in order until one works:
    1. Preferred model (if provided)
    2. Latest Sonnet 3.5
    3. Earlier Sonnet 3.5
    4. Sonnet 3
    5. Opus 3 (most reliable fallback)
    
    Args:
        client: Anthropic client
        preferred_model: Preferred model name (optional)
    
    Returns:
        Working model name
    """
    models_to_try = []
    
    # Add preferred model first if provided
    if preferred_model:
        models_to_try.append(preferred_model)
    
    # Add standard fallbacks
    models_to_try.extend(CLAUDE_MODELS)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_models = []
    for model in models_to_try:
        if model not in seen:
            seen.add(model)
            unique_models.append(model)
    
    # Try each model
    for model in unique_models:
        try:
            # Test with minimal token request
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            
            logger.info(f"✅ Using Claude model: {model}")
            return model
        
        except Exception as e:
            logger.debug(f"Model {model} not available: {e}")
            continue
    
    # If all else fails, return the most reliable one
    # (Anthropic will error if it's not available, which is fine)
    logger.warning("⚠️ Could not verify model availability, using claude-sonnet-4-5-20250929")
    return "claude-sonnet-4-5-20250929"


# Cached model (determined once per session)
_cached_model: Optional[str] = None


def get_cached_model(client) -> str:
    """Get cached working model (determined once)"""
    global _cached_model
    
    if _cached_model is None:
        _cached_model = get_best_available_model(client)
    
    return _cached_model


def call_claude_sync(client, *, retries: int = MAX_RETRIES, **kwargs) -> Any:
    """Synchronous Claude call with retry on 529/503/429. Groq→OpenAI fallback on 400."""
    for attempt in range(retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 400:
                logger.warning("Claude 400 credit exhaustion — falling back to Groq→OpenAI")
                return call_llm_fallback(kwargs.get("messages", []), kwargs.get("max_tokens", 4096))
            if e.status_code in RETRY_STATUS_CODES and attempt < retries - 1:
                wait = 2 * (attempt + 1)
                logger.warning(f"Claude {e.status_code} (attempt {attempt+1}/{retries}), retrying in {wait}s")
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise
    return None


async def call_claude_async(client, *, retries: int = MAX_RETRIES, **kwargs) -> Any:
    """Async Claude call with retry on 529/503/429. Groq→OpenAI fallback on 400."""
    for attempt in range(retries):
        try:
            return await asyncio.to_thread(client.messages.create, **kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 400:
                logger.warning("Claude 400 credit exhaustion — falling back to Groq→OpenAI")
                return await asyncio.to_thread(call_llm_fallback, kwargs.get("messages", []), kwargs.get("max_tokens", 4096))
            if e.status_code in RETRY_STATUS_CODES and attempt < retries - 1:
                wait = 2 * (attempt + 1)
                logger.warning(f"Claude {e.status_code} (attempt {attempt+1}/{retries}), retrying in {wait}s")
                await asyncio.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
            raise
    return None


async def acall_claude(client, *, retries: int = MAX_RETRIES, **kwargs) -> Any:
    """Native async Claude call with retry on 529/503/429. Groq→OpenAI fallback on 400."""
    for attempt in range(retries):
        try:
            return await client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 400:
                logger.warning("Claude 400 credit exhaustion — falling back to Groq→OpenAI")
                return await asyncio.to_thread(call_llm_fallback, kwargs.get("messages", []), kwargs.get("max_tokens", 4096))
            if e.status_code in RETRY_STATUS_CODES and attempt < retries - 1:
                wait = 2 * (attempt + 1)
                logger.warning(f"Claude {e.status_code} (attempt {attempt+1}/{retries}), retrying in {wait}s")
                await asyncio.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2)
                continue
            raise
    return None
