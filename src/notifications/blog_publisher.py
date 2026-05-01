"""
blog_publisher.py — GEO+SEO blog cross-posting for tech milestone posts.

SAFE DESIGN:
- Called ONLY after a successful LinkedIn tech_update post.
- Any failure here is logged and swallowed — LinkedIn posting is NEVER affected.
- If API keys are absent, silently skips that platform.

PLATFORMS:
  Hashnode: GraphQL API (HASHNODE_API_KEY + HASHNODE_PUBLICATION_ID)
  dev.to  : REST API   (DEVTO_API_KEY)

WIRING (in linkedin_cmo_v4.py, after _mark_tech_update_posted):
    from src.notifications.blog_publisher import schedule_blog_post
    asyncio.create_task(schedule_blog_post(update, linkedin_content, language, anthropic_api_key))
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp
from anthropic import AsyncAnthropic

logger = logging.getLogger("src.notifications.blog_publisher")

# ── Env vars ─────────────────────────────────────────────────────────────────
HASHNODE_API_KEY        = os.environ.get("HASHNODE_API_KEY", "")
HASHNODE_PUBLICATION_ID = os.environ.get("HASHNODE_PUBLICATION_ID", "")
DEVTO_API_KEY           = os.environ.get("DEVTO_API_KEY", "")
ANTHROPIC_API_KEY       = os.environ.get("ANTHROPIC_API_KEY", "")

PORTFOLIO_URL = "https://aideazz.xyz/portfolio"

DEVTO_TAGS_TECH  = ["ai", "buildinpublic", "machinelearning", "python"]
HASHNODE_TAGS    = [
    {"slug": "ai"},
    {"slug": "machinelearning"},
    {"slug": "buildinpublic"},
    {"slug": "python"},
]

# ── Long-form article generation ─────────────────────────────────────────────

async def _generate_article(
    update: Dict[str, Any],
    linkedin_snippet: str,
    language: str,
    api_key: str,
) -> Optional[Dict[str, str]]:
    """
    Generate a long-form blog article about a CTO milestone.
    Returns {"title": ..., "markdown": ...} or None on failure.

    The LinkedIn post is passed as a "teaser" — the article must expand it,
    NOT repeat it verbatim.
    """
    lang_full = "English" if language.upper() == "EN" else "Spanish"
    repo = update.get("repo", "AIdeazz")
    title_raw = update.get("title", "Technical milestone")
    desc = update.get("description", "")
    update_type = update.get("type", "feature")

    article_title = f"{title_raw} — Building AI Agents in Public"
    if language.upper() == "ES":
        article_title = f"{title_raw} — Construyendo agentes de IA en público"

    prompt = f"""You are Elena Revicheva writing a long-form technical blog post for Hashnode and dev.to.

CONTEXT:
- You are a solo technical founder (Applied AI Engineer) building AIdeazz — a suite of AI agents.
- CTO AIPA, your AI technical co-founder, shipped this milestone:

  Repository: {repo}
  Title: {title_raw}
  Type: {update_type}
  Description: {desc}

- You already posted this short teaser on LinkedIn (do NOT copy it verbatim):
  ---
  {linkedin_snippet[:500]}
  ---

WRITE A BLOG POST:
Language: {lang_full}
Target length: 550–800 words
Tone: Honest, technical, first-person. "Building in public" energy. No hype.
Format: Markdown. Use ## for sections, ` backticks ` for code/tool names, no HTML.

REQUIRED STRUCTURE:
## What We Shipped
(1–2 paragraphs — the concrete technical thing, named specifically)

## Why It Matters
(1–2 paragraphs — user/product impact, not marketing fluff)

## How It Works (Brief)
(technical sketch — enough for a developer to understand the approach)

## What's Next
(1 paragraph — honest next step, not a roadmap promise)

---
*(optional footer)* Built by Elena Revicheva — Applied AI Engineer & Founder @ AIdeazz.
Find the full demo at {PORTFOLIO_URL}

RULES:
1. Use real, specific names: repos, tools, models (e.g. "Claude Sonnet 4", "pgvector", "LangGraph").
2. Zero invented metrics. If you don't know a number, don't cite one.
3. No corporate language, no buzzword soup.
4. Write as yourself — first person singular, direct.
5. Return ONLY the markdown article body (no YAML front matter, no title header — title is set separately).

Write the article now:"""

    try:
        client = AsyncAnthropic(api_key=api_key or ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        markdown = resp.content[0].text.strip() if resp.content else ""
        if not markdown:
            return None
        return {"title": article_title, "markdown": markdown}
    except Exception as e:
        logger.error(f"[BlogPublisher] Article generation failed: {e}")
        return None


# ── Hashnode ──────────────────────────────────────────────────────────────────

async def _publish_hashnode(title: str, markdown: str) -> bool:
    if not HASHNODE_API_KEY or not HASHNODE_PUBLICATION_ID:
        logger.info("[BlogPublisher] Hashnode: no API key/publication — skipping")
        return False

    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { id url title }
      }
    }
    """
    variables = {
        "input": {
            "title": title,
            "contentMarkdown": markdown,
            "publicationId": HASHNODE_PUBLICATION_ID,
            "tags": HASHNODE_TAGS,
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://gql.hashnode.com/",
                json={"query": mutation, "variables": variables},
                headers={
                    "Authorization": HASHNODE_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                data = await resp.json()
                if "errors" in data:
                    logger.error(f"[BlogPublisher] Hashnode error: {data['errors']}")
                    return False
                url = data.get("data", {}).get("publishPost", {}).get("post", {}).get("url", "")
                logger.info(f"✅ [BlogPublisher] Hashnode published: {url}")
                return True
    except Exception as e:
        logger.error(f"[BlogPublisher] Hashnode publish failed: {e}")
        return False


# ── dev.to ────────────────────────────────────────────────────────────────────

async def _publish_devto(title: str, markdown: str) -> bool:
    if not DEVTO_API_KEY:
        logger.info("[BlogPublisher] dev.to: no API key — skipping")
        return False

    # dev.to needs the title stripped from markdown body (it sets title separately)
    body = re.sub(r'^#{1,2}\s+.*\n', '', markdown, count=1).strip()

    payload = {
        "article": {
            "title": title,
            "body_markdown": body,
            "published": True,
            "tags": DEVTO_TAGS_TECH,
            "canonical_url": PORTFOLIO_URL,
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://dev.to/api/articles",
                json=payload,
                headers={
                    "api-key": DEVTO_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    url = data.get("url", "")
                    logger.info(f"✅ [BlogPublisher] dev.to published: {url}")
                    return True
                text = await resp.text()
                logger.error(f"[BlogPublisher] dev.to HTTP {resp.status}: {text[:200]}")
                return False
    except Exception as e:
        logger.error(f"[BlogPublisher] dev.to publish failed: {e}")
        return False


# ── Public entry point ────────────────────────────────────────────────────────

async def schedule_blog_post(
    update: Dict[str, Any],
    linkedin_content: str,
    language: str,
    api_key: str = "",
) -> None:
    """
    Fire-and-forget coroutine. Called via asyncio.create_task() from CMO AIPA.
    Generates and publishes a long-form article to Hashnode + dev.to.
    Any failure is logged — never raises.
    """
    title_raw = update.get("title", "milestone")
    logger.info(f"[BlogPublisher] Starting blog cross-post for: {title_raw}")

    try:
        article = await _generate_article(update, linkedin_content, language, api_key)
        if not article:
            logger.warning("[BlogPublisher] Article generation returned nothing — skipping publish")
            return

        title, markdown = article["title"], article["markdown"]

        # Publish in parallel
        hashnode_ok, devto_ok = await asyncio.gather(
            _publish_hashnode(title, markdown),
            _publish_devto(title, markdown),
            return_exceptions=True,
        )

        summary = []
        if hashnode_ok is True:
            summary.append("Hashnode ✅")
        elif isinstance(hashnode_ok, Exception):
            summary.append(f"Hashnode ❌ ({hashnode_ok})")
        else:
            summary.append("Hashnode ⏭️")

        if devto_ok is True:
            summary.append("dev.to ✅")
        elif isinstance(devto_ok, Exception):
            summary.append(f"dev.to ❌ ({devto_ok})")
        else:
            summary.append("dev.to ⏭️")

        logger.info(f"[BlogPublisher] Cross-post result: {' | '.join(summary)}")

    except Exception as e:
        logger.error(f"[BlogPublisher] Unexpected error in schedule_blog_post: {e}")
        # NEVER re-raise — LinkedIn pipeline must not be affected
