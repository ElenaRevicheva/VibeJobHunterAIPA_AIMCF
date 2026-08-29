"""
AI-NATIVE-BUILDER.COM - curated AI-builder / automation board (added 2026-08-29)

WHAT THIS REPLACES: nothing. New, fully self-contained source. It does not import
from, modify, or share state with any existing scraper. On any error it returns []
and the discovery cycle proceeds exactly as before.

WHY IT EXISTS - SIGNAL DENSITY, NOT VOLUME
VJH already sees ~2,200 jobs/cycle and the career gate discards ~94% of them. More
generic volume makes that worse, not better. This board is the opposite shape: it is
hand-curated for one audience - people who BUILD with AI tools rather than train
models. Measured over its full 345-posting sitemap on 2026-08-29:

    automation / low-code (n8n, Make, workflow, integration)   159   (46.1%)
    AI builder / agent / LLM                                   249   (72.2%)
    solutions architect / lead                                  28   ( 8.1%)
    ML-researcher titles (Elena's hard discard)                   0   ( 0.0%)

Zero research-scientist noise is the point. Its own taxonomy pages are Elena's lanes
verbatim: /ai-automation-jobs, /n8n-jobs, /make-jobs, /claude-code-jobs, /cursor-jobs.

HOW IT INGESTS - no key, no auth, no paywall, no scraping tricks
  * https://www.ai-native-builder.com/sitemap.xml -> 345 /jobs/<slug> URLs
  * each job page carries a schema.org JobPosting JSON-LD block with title,
    hiringOrganization, datePosted, validThrough, employmentType, description and
    applicantLocationRequirements - i.e. the publisher's own machine-readable feed.
  * robots.txt is "User-Agent: * / Allow: /" and explicitly welcomes ClaudeBot,
    GPTBot and PerplexityBot. Verified 2026-08-29.

COST CONTROL: detail pages are cached on disk by slug, so a cycle only fetches slugs
it has never seen. First run pays ~345 fetches; steady state is the handful the board
adds per day. Progress is written as it goes, so a timeout on the first run is
self-healing - the next cycle resumes instead of restarting.
"""

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_BASE = "https://www.ai-native-builder.com"
_SITEMAP = _BASE + "/sitemap.xml"
_UA = "Mozilla/5.0 (VibeJobHunter/1.0; +https://aideazz.xyz)"
_CACHE_DIR = Path("autonomous_data/cache/ai_native_builder")

# Politeness + blast-radius caps. The board is a one-person operation; do not hammer it.
_CONCURRENCY = 6
_MAX_NEW_PER_CYCLE = 150
_CACHE_TTL_DAYS = 30

_LDJSON_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_ATS_RE = re.compile(
    r'https?://[a-zA-Z0-9./_%-]*(?:greenhouse|lever\.co|ashbyhq|workable|teamtailor|'
    r'zohorecruit|smartrecruiters|recruitee|bamboohr|jobvite|myworkdayjobs)'
    r'[a-zA-Z0-9./_%-]*')
_TAG_RE = re.compile(r"<[^>]+>")


def _slug_of(url: str) -> str:
    return url.rstrip("/").split("/jobs/")[-1]


def _cache_path(slug: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", slug)[:120]
    return _CACHE_DIR / (safe + ".json")


def _read_cache(slug: str) -> Optional[Dict]:
    p = _cache_path(slug)
    if not p.exists():
        return None
    try:
        if (time.time() - p.stat().st_mtime) > _CACHE_TTL_DAYS * 86400:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(slug: str, job: Dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(slug).write_text(
            json.dumps(job, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # cache is an optimisation; never fail the cycle over it


def _parse_job_page(html: str, page_url: str) -> Optional[Dict]:
    """Extract the publisher's own JobPosting JSON-LD. Returns None if absent."""
    posting = None
    for block in _LDJSON_RE.findall(html):
        try:
            data = json.loads(block)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            posting = data
            break
    if not posting:
        return None

    title = (posting.get("title") or "").strip()
    org = posting.get("hiringOrganization") or {}
    company = (org.get("name") if isinstance(org, dict) else str(org)) or ""
    company = company.strip()
    if not title or not company:
        return None

    # Location: the gate needs the word "remote" to treat a posting as remote-friendly,
    # so only say it when the publisher actually declared TELECOMMUTE.
    alr = posting.get("applicantLocationRequirements") or {}
    if isinstance(alr, list):
        region = ", ".join(str(a.get("name", "")) for a in alr
                           if isinstance(a, dict)) or "Worldwide"
    elif isinstance(alr, dict):
        region = str(alr.get("name") or "Worldwide")
    else:
        region = "Worldwide"

    if str(posting.get("jobLocationType") or "").upper() == "TELECOMMUTE":
        location = "Remote - " + region
    else:
        loc = posting.get("jobLocation") or {}
        addr = loc.get("address", {}) if isinstance(loc, dict) else {}
        location = " ".join(
            str(addr.get(k, "")) for k in
            ("addressLocality", "addressRegion", "addressCountry")).strip() or region

    description = _TAG_RE.sub(" ", posting.get("description") or "")
    description = re.sub(r"\s+", " ", description).strip()

    # The board links straight through to the employer's ATS. Carrying that URL saves
    # Elena a hop and lets the ATS layer recognise the posting if auto-apply is re-enabled.
    ats = _ATS_RE.search(html)

    return {
        "title": title,
        "company": company,
        "location": location,
        "description": description[:2000],
        "source": "ai_native_builder",
        "url": ats.group(0) if ats else page_url,
        "board_url": page_url,
        "posted_date": posting.get("datePosted") or "",
        "valid_through": posting.get("validThrough") or "",
        "employment_type": posting.get("employmentType") or "",
    }


async def _fetch_slug(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                      url: str) -> Optional[Dict]:
    slug = _slug_of(url)
    async with sem:
        try:
            async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None
        await asyncio.sleep(0.15)  # be a good citizen on a small publisher
    job = _parse_job_page(html, url)
    if job:
        _write_cache(slug, job)
    return job


async def fetch_ai_native_builder_jobs(timeout_seconds: int = 120) -> List[Dict]:
    """Return every live posting on ai-native-builder.com. Fails soft to []."""
    logger.info("Checking ai-native-builder.com...")
    jobs: List[Dict] = []
    fresh_urls: List[str] = []
    try:
        headers = {"User-Agent": _UA}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                    _SITEMAP, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    logger.warning(
                        "ai-native-builder sitemap HTTP %s", resp.status)
                    return []
                sitemap = await resp.text()

            job_urls = [u for u in re.findall(r"<loc>(.*?)</loc>", sitemap)
                        if "/jobs/" in u]
            logger.info("   ai-native-builder sitemap: %d job URLs", len(job_urls))

            for u in job_urls:
                cached = _read_cache(_slug_of(u))
                if cached:
                    jobs.append(cached)
                else:
                    fresh_urls.append(u)
            cached_n = len(jobs)

            if len(fresh_urls) > _MAX_NEW_PER_CYCLE:
                logger.info(
                    "   capping new fetches %d -> %d (remainder resumes next cycle)",
                    len(fresh_urls), _MAX_NEW_PER_CYCLE)
                fresh_urls = fresh_urls[:_MAX_NEW_PER_CYCLE]

            if fresh_urls:
                sem = asyncio.Semaphore(_CONCURRENCY)
                results = await asyncio.gather(
                    *[_fetch_slug(session, sem, u) for u in fresh_urls],
                    return_exceptions=True)
                for r in results:
                    if isinstance(r, dict):
                        jobs.append(r)

        logger.info("ai-native-builder: %d jobs (%d from cache, %d newly fetched)",
                    len(jobs), cached_n, len(jobs) - cached_n)
    except Exception as e:
        logger.warning("ai-native-builder failed: %s", e)
        return jobs  # partial is better than none; cache makes the next cycle cheaper
    return jobs
