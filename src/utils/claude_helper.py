"""
Claude API Helper
Handles model selection, fallbacks, and retry with backoff for transient errors (529/503/429).
"""

import asyncio
import logging
import time
from typing import Optional, Any, Set

import anthropic

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_STATUS_CODES: Set[int] = {529, 503, 429}


# Model selection priority (tries in order)
CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",  # Latest
    "claude-sonnet-4-20250514",  # Fallback 1
    "claude-sonnet-4-20250514",    # Fallback 2
    "claude-sonnet-4-20250514",      # Fallback 3 (most reliable)
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
    logger.warning("⚠️ Could not verify model availability, using claude-sonnet-4-20250514")
    return "claude-sonnet-4-20250514"


# Cached model (determined once per session)
_cached_model: Optional[str] = None


def get_cached_model(client) -> str:
    """Get cached working model (determined once)"""
    global _cached_model
    
    if _cached_model is None:
        _cached_model = get_best_available_model(client)
    
    return _cached_model


def call_claude_sync(client, *, retries: int = MAX_RETRIES, **kwargs) -> Any:
    """Synchronous Claude call with retry on 529/503/429."""
    for attempt in range(retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
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
    """Async Claude call with retry on 529/503/429 (wraps sync client in thread)."""
    for attempt in range(retries):
        try:
            return await asyncio.to_thread(client.messages.create, **kwargs)
        except anthropic.APIStatusError as e:
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
    """Native async Claude call with retry on 529/503/429 (for AsyncAnthropic)."""
    for attempt in range(retries):
        try:
            return await client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
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
