"""
🌎 GET ON BOARD — LATAM-first job source (added 2026-08-04)

WHAT THIS REPLACES: nothing. New, fully self-contained source. It does not import
from, modify, or share state with any existing scraper. On any error it returns []
and the discovery cycle proceeds exactly as before.

WHY IT EXISTS
A source-conversion audit over 7,087 processed jobs found ONE source carrying the
whole pipeline:

    torre.ai        283 processed → 102 surfaced   (36%)
    dice.com        601 processed →   4 surfaced   (0.7%)
    ashby+gh+lever  314 processed →   2 surfaced   (0.6%)
    ai-jobs.net   2,163 processed →   1 surfaced   (0.05%)
    linkedin.com  3,565 processed →   0 surfaced   (0%)

Torre converts because it is LATAM-first: remote-from-Panama is the default there,
not an exception. The fix for low volume is therefore MORE TORRE-SHAPED SOURCES,
not looser filters. Get on Board (getonbrd.com) is the same shape — a LATAM tech
board — and its public API returns two things almost nothing else does:

  • MONTHLY USD SALARY (min_salary / max_salary) — feeds salary_gate directly
    instead of leaving pay "unknown", which is the state most postings arrive in.
  • A REAL DESCRIPTION (~800-900 chars) — clears the thin-data guard that was
    silently discarding 107 postings per 48h, so these jobs are judged on their
    merits rather than dropped as unreadable.

API: https://www.getonbrd.com/api/v0/  — public, no auth, no key.
Verified live 2026-08-04: 117 pages in the "programming" category alone.
"""

import asyncio
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

_BASE = "https://www.getonbrd.com/api/v0"
_UA = "Mozilla/5.0 (VibeJobHunter/1.0; +https://aideazz.xyz)"

# Elena's lanes. Category feeds give volume; the search terms target the
# AI-automation lane specifically, which categories alone under-serve.
_CATEGORIES = ("programming", "data-science")
_SEARCH_TERMS = (
    "inteligencia artificial",
    "machine learning",
    "automation",
    "agentes ia",
    # 2026-08-05: leadership / advisory lane. Unblocking "Head of AI" at the gate
    # is useless unless a source is asked for it. Spanish variants included —
    # this is a LATAM board and half its postings are written in Spanish.
    "ai consultant",
    "ai product manager",
    "head of ai",
    "arquitecto de ia",
    "lider de ia",
)
_PER_PAGE = 30
_MAX_PAGES = 2  # per feed — keeps one cycle's fetch bounded

# Panama, accent-folded. A listing restricted to specific countries that do not
# include Panama is one Elena cannot hold, however "LATAM" the board is — the
# same lesson the Singular Agency pre-screening rejection taught (roster beats
# label). Handled here at the source so no downstream gate has to guess.
_HOME = "panama"
_OPEN_MARKERS = ("remote", "worldwide", "anywhere", "global", "latam",
                 "latin america", "america")

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\x0b\f\r]+")


def _deaccent(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def _text(html: str) -> str:
    """HTML → plain text. Descriptions arrive as small HTML fragments."""
    t = _TAGS.sub(" ", html or "")
    for ent, rep in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                     ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        t = t.replace(ent, rep)
    return _WS.sub(" ", t).strip()


def _eligible(countries: List[str]) -> bool:
    """True if Elena could hold this job from Panama."""
    if not countries:
        return True  # unspecified → let the downstream gates judge
    blob = _deaccent(" ".join(str(c) for c in countries).lower())
    if _HOME in blob:
        return True
    return any(m in blob for m in _OPEN_MARKERS)


def _location(countries: List[str]) -> str:
    """Location string in the shape iron_clad_fit already understands."""
    if not countries:
        return "Remote — Worldwide"
    blob = " ".join(str(c) for c in countries)
    if _deaccent(blob.lower()).strip() in ("remote", "worldwide", "anywhere"):
        return "Remote — Worldwide / LATAM"
    return f"Remote — LATAM ({blob})"


def _to_job(rec: Dict) -> Dict:
    attrs = rec.get("attributes") or {}
    if not attrs.get("remote"):
        return {}
    countries = attrs.get("countries") or []
    if not _eligible(countries):
        return {}

    title = (attrs.get("title") or "").strip()
    if not title:
        return {}

    company = "Get on Board"
    co = ((attrs.get("company") or {}).get("data") or {}).get("attributes") or {}
    if co.get("name"):
        company = str(co["name"]).strip()

    desc = _text(attrs.get("description") or "")
    for extra in ("functions", "desirable", "benefits"):
        more = _text(attrs.get(extra) or "")
        if more:
            desc = f"{desc}\n\n{more}"

    # Pay stated in the payload is worth more than pay buried in prose — append it
    # verbatim in a shape salary_gate parses, so the floor can actually be applied.
    lo, hi = attrs.get("min_salary"), attrs.get("max_salary")
    if lo or hi:
        desc += f"\n\nSalary: USD {lo or hi} - {hi or lo} per month."

    url = ((rec.get("links") or {}).get("public_url")
           or f"https://www.getonbrd.com/jobs/{rec.get('id', '')}")

    return {
        "id": f"gob_{rec.get('id', '')}",
        "title": title,
        "company": company,
        "location": _location(countries),
        "description": desc[:6000],
        "url": url,
        "source": "getonbrd",
        "remote": True,
    }


def _fetch_sync(timeout_seconds: int) -> List[Dict]:
    import requests

    jobs: List[Dict] = []
    seen = set()
    feeds = [f"{_BASE}/categories/{c}/jobs" for c in _CATEGORIES]
    feeds += [f"{_BASE}/search/jobs?query={requests.utils.quote(t)}" for t in _SEARCH_TERMS]

    for feed in feeds:
        for page in range(1, _MAX_PAGES + 1):
            sep = "&" if "?" in feed else "?"
            url = f'{feed}{sep}page={page}&per_page={_PER_PAGE}&expand=["company"]'
            try:
                resp = requests.get(url, headers={"User-Agent": _UA}, timeout=20)
                if resp.status_code != 200:
                    logger.debug(f"[getonbrd] HTTP {resp.status_code} for {url[:90]}")
                    break
                data = (resp.json() or {}).get("data") or []
            except Exception as e:
                logger.debug(f"[getonbrd] fetch failed ({e}) for {url[:90]}")
                break
            if not data:
                break
            for rec in data:
                job = _to_job(rec)
                if job and job["id"] not in seen:
                    seen.add(job["id"])
                    jobs.append(job)
    return jobs


async def fetch_getonbrd_jobs(timeout_seconds: int = 90) -> List[Dict]:
    """
    LATAM-first remote jobs from Get on Board. Never raises; returns [] on any
    failure so a bad day at getonbrd.com cannot affect the rest of the cycle.
    """
    logger.info("🔍 Checking Get on Board (LATAM)...")
    try:
        jobs = await asyncio.wait_for(
            asyncio.to_thread(_fetch_sync, timeout_seconds),
            timeout=timeout_seconds,
        )
        logger.info(f"✅ Get on Board: {len(jobs)} remote LATAM-eligible jobs")
        return jobs
    except asyncio.TimeoutError:
        logger.warning(f"⚠️ Get on Board timed out after {timeout_seconds}s")
        return []
    except Exception as e:
        logger.warning(f"⚠️ Get on Board failed: {e}")
        return []
