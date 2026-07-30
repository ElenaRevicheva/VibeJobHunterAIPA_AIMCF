"""
🦄 YC OSS → REAL OPENINGS converter (added 2026-07-30)

WHAT THIS REPLACES: nothing. This is a NEW, fully self-contained source. It does
not import from, modify, or share state with any existing scraper. If it fails it
returns [] and the cycle proceeds exactly as before.

WHY IT EXISTS
The `openclaw-vibejob-shortlist` repo (last pushed 2026-03-23, service inactive)
fetched YC companies from the free yc-oss API, scored them for remote/LATAM/hiring,
and exported a *company* list. Companies are not applyable — they have no title, no
URL, no salary. VJH's `/priority sync yc` bridge consumed that list, but priority
membership only adds +15 to a job some OTHER scraper already found; nothing ever
went and fetched those companies' openings.

This module closes that gap: YC companies → filter → **fetch each company's real
ATS board** → job dicts in the same shape every other job_monitor source emits.

HONEST COVERAGE LIMIT (measured 2026-07-30): only ~13% of hiring YC companies
expose a public ATS board (6 of 44 on the ai-assistant tag). The rest post solely
on workatastartup.com, which is login-gated — deliberately NOT scraped here. So
this is a partial converter that adds free supply VJH gets nowhere else, not
complete YC coverage.

NO AUTH. NO COOKIES. All endpoints are public JSON.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp

logger = logging.getLogger(__name__)

YC_OSS_ENABLED = os.getenv("VJH_YC_OSS_ENABLED", "true").strip().lower() == "true"

# Free, daily-updated, no key. Tag files verified to exist 2026-07-30.
_YC_TAG_URL = "https://yc-oss.github.io/api/tags/{tag}.json"
YC_TAGS = [t.strip() for t in os.getenv(
    "VJH_YC_TAGS",
    "ai,ai-assistant,generative-ai,automation,workflow-automation,developer-tools,no-code",
).split(",") if t.strip()]

# Public ATS job-board APIs — the SAME endpoints src/scrapers/ats_scraper.py uses.
_ATS_ENDPOINTS = {
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever":      "https://api.lever.co/v0/postings/{slug}?mode=json",
}

# Probing every slug on every cycle would be ~3 requests x hundreds of companies.
# Cache which slug maps to which ATS (or to nothing) and re-probe monthly.
_CACHE_PATH = Path("autonomous_data/yc_oss_ats_cache.json")
_CACHE_TTL_DAYS = int(os.getenv("VJH_YC_CACHE_TTL_DAYS", "30"))

# Region strings in the YC API that mean "she can actually hold this job".
_REMOTE_REGIONS = {"remote", "fully remote"}
_LATAM_REGIONS = {"latin america", "latam", "south america", "central america", "america / canada"}

_UA = {"User-Agent": "Mozilla/5.0 (VibeJobHunter/1.0; +https://aideazz.xyz)"}

_MAX_COMPANIES = int(os.getenv("VJH_YC_MAX_COMPANIES", "120"))


# ─────────────────────────────────────────────────────────────────────────────
# ATS-mapping cache
# ─────────────────────────────────────────────────────────────────────────────
def _load_cache() -> Dict[str, Any]:
    try:
        if _CACHE_PATH.exists():
            raw = json.loads(_CACHE_PATH.read_text())
            if isinstance(raw, dict):
                return raw
    except Exception as e:
        logger.debug(f"[yc_oss] cache unreadable ({e}) — starting fresh")
    return {}


def _save_cache(cache: Dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(cache))
    except Exception as e:
        logger.debug(f"[yc_oss] could not persist cache: {e}")


def _cache_fresh(entry: Any) -> bool:
    try:
        return (time.time() - float(entry.get("probed_at", 0))) < _CACHE_TTL_DAYS * 86400
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Company selection
# ─────────────────────────────────────────────────────────────────────────────
def _company_is_relevant(c: Dict[str, Any]) -> bool:
    """Active + actively hiring + remote-or-LATAM signal. Deliberately generous:
    the career gate, iron_clad_fit and the LLM judge do the real filtering downstream."""
    if c.get("status") != "Active" or not c.get("isHiring"):
        return False
    regions = {str(r).strip().lower() for r in (c.get("regions") or [])}
    if regions & _REMOTE_REGIONS:
        return True
    if regions & _LATAM_REGIONS:
        return True
    # No region data at all → let it through; the downstream gate reads the posting.
    return not regions


async def _fetch_json(session: aiohttp.ClientSession, url: str, timeout: int = 15) -> Optional[Any]:
    try:
        async with session.get(url, headers=_UA, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return await resp.json(content_type=None)
    except Exception:
        return None


async def _fetch_yc_companies(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Union of the configured tag files, deduped by slug."""
    by_slug: Dict[str, Dict[str, Any]] = {}
    for tag in YC_TAGS:
        data = await _fetch_json(session, _YC_TAG_URL.format(tag=tag))
        if not isinstance(data, list):
            logger.debug(f"[yc_oss] tag '{tag}' unavailable — skipped")
            continue
        for c in data:
            slug = str(c.get("slug") or "").strip()
            if slug and slug not in by_slug:
                by_slug[slug] = c
    return list(by_slug.values())


# ─────────────────────────────────────────────────────────────────────────────
# Company → openings
# ─────────────────────────────────────────────────────────────────────────────
def _norm_jobs(provider: str, payload: Any) -> List[Dict[str, Any]]:
    if provider == "lever":
        return payload if isinstance(payload, list) else []
    if isinstance(payload, dict):
        return payload.get("jobs") or []
    return []


async def _probe_ats(session: aiohttp.ClientSession, slug: str) -> Tuple[Optional[str], List[Dict]]:
    """Find which public ATS board (if any) belongs to this slug."""
    for provider, tmpl in _ATS_ENDPOINTS.items():
        payload = await _fetch_json(session, tmpl.format(slug=slug), timeout=12)
        jobs = _norm_jobs(provider, payload) if payload is not None else []
        if jobs:
            return provider, jobs
    return None, []


def _job_dict(company_name: str, provider: str, raw: Dict[str, Any], website: str) -> Optional[Dict[str, Any]]:
    """Normalise one ATS posting into the dict shape job_monitor already consumes."""
    title = (raw.get("title") or raw.get("text") or "").strip()
    if not title:
        return None

    if provider == "ashby":
        location = raw.get("location") or ""
        desc = raw.get("descriptionPlain") or raw.get("description") or ""
        url = raw.get("jobUrl") or website
        jid = raw.get("id") or title
        if raw.get("isRemote") and "remote" not in str(location).lower():
            location = f"{location} (Remote)".strip()
    elif provider == "greenhouse":
        location = (raw.get("location") or {}).get("name", "") if isinstance(raw.get("location"), dict) else ""
        desc = raw.get("content") or ""
        url = raw.get("absolute_url") or website
        jid = raw.get("id") or title
    else:  # lever
        cats = raw.get("categories") or {}
        location = cats.get("location") or ""
        commitment = cats.get("commitment") or ""
        desc = raw.get("descriptionPlain") or raw.get("description") or ""
        if commitment:
            desc = f"{commitment}. {desc}"
        url = raw.get("hostedUrl") or website
        jid = raw.get("id") or title

    return {
        "id": f"ycoss_{provider}_{jid}",
        "title": title,
        "company": company_name,
        "location": str(location)[:200],
        # Full text on purpose: iron_clad_fit reads the WHOLE description (the
        # June-21 truncation bug made genuine worldwide-AI roles fail ai_aug).
        "description": str(desc)[:8000],
        "url": url,
        "source": "yc_oss",
        "remote": "remote" in f"{location} {desc[:400]}".lower(),
    }


async def fetch_yc_oss_jobs(timeout_seconds: int = 120) -> List[Dict[str, Any]]:
    """
    Public entrypoint. Returns job dicts, or [] on ANY failure — never raises.
    """
    if not YC_OSS_ENABLED:
        logger.info("🦄 YC OSS source disabled (VJH_YC_OSS_ENABLED=false)")
        return []

    started = time.time()
    jobs: List[Dict[str, Any]] = []
    cache = _load_cache()
    cache_dirty = False
    probed = matched = 0

    try:
        async with aiohttp.ClientSession() as session:
            companies = await _fetch_yc_companies(session)
            if not companies:
                logger.warning("🦄 YC OSS: no companies returned — skipping")
                return []

            relevant = [c for c in companies if _company_is_relevant(c)]
            # Smaller teams first: a 12-person YC startup is likelier to want an
            # AI-augmented generalist than a 350-person one.
            relevant.sort(key=lambda c: c.get("team_size") or 9999)
            relevant = relevant[:_MAX_COMPANIES]
            logger.info(
                f"🦄 YC OSS: {len(companies)} companies across {len(YC_TAGS)} tags → "
                f"{len(relevant)} active+hiring+remote/LATAM"
            )

            for c in relevant:
                if time.time() - started > timeout_seconds:
                    logger.warning(f"🦄 YC OSS: timeout budget spent — returning {len(jobs)} jobs so far")
                    break

                slug = str(c.get("slug") or "").strip()
                name = str(c.get("name") or slug)
                website = str(c.get("website") or c.get("url") or "")
                if not slug:
                    continue

                entry = cache.get(slug)
                if entry and _cache_fresh(entry):
                    provider = entry.get("provider")
                    if not provider:
                        continue  # known to have no public board — skip cheaply
                    payload = await _fetch_json(session, _ATS_ENDPOINTS[provider].format(slug=slug), timeout=12)
                    raw_jobs = _norm_jobs(provider, payload) if payload is not None else []
                else:
                    provider, raw_jobs = await _probe_ats(session, slug)
                    probed += 1
                    cache[slug] = {"provider": provider, "probed_at": time.time()}
                    cache_dirty = True

                if not provider or not raw_jobs:
                    continue

                matched += 1
                for raw in raw_jobs:
                    jd = _job_dict(name, provider, raw, website)
                    if jd:
                        jobs.append(jd)

    except Exception as e:
        logger.error(f"❌ YC OSS source failed ({e}) — returning {len(jobs)} jobs, cycle unaffected")

    if cache_dirty:
        _save_cache(cache)

    logger.info(
        f"✅ YC OSS: {len(jobs)} openings from {matched} companies "
        f"({probed} newly probed, {len(cache)} cached) in {time.time()-started:.0f}s"
    )
    return jobs


async def _selftest() -> None:
    """python -m src.scrapers.yc_oss_jobs"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    jobs = await fetch_yc_oss_jobs(timeout_seconds=180)
    print(f"\nTOTAL: {len(jobs)} openings")
    for j in jobs[:12]:
        print(f"  {j['company']:<22} {j['title'][:52]:<54} {j['location'][:28]}")


if __name__ == "__main__":
    asyncio.run(_selftest())
