"""
📄 THIN-POSTING ENRICHER (added 2026-07-30)

THE PROBLEM IT SOLVES (measured, not theorised)
"Appspring — Senior Python Developer" (torre.ai) reached Elena three times. The
description VJH actually scored was 96 characters long:

    "You will design AI agents and build high-performance backend systems.
     [Remote role via Torre.ai]"

...with `requirements: []`. Torre's list API returns only the one-line `tagline`,
so the keyword scorer, iron_clad_fit, the salary gate and Claude were ALL judging
a headline. Claude said as much when it scored the job 45/100: "description is
incomplete with no specific requirements listed, making it impossible to assess
true role seniority or scope."

WHAT THIS DOES
For a job whose description is too thin to judge, fetch its public posting URL
once, strip the HTML, and hand back real text. One extra HTTP request, only for
jobs that already passed the career gate — so a few per cycle, not thousands.

SAFETY
Never raises. Never returns something shorter than what it was given. On timeout,
non-200, wrong content-type, or a parse failure it returns the ORIGINAL text, so
every existing flow behaves exactly as it does today.
"""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

ENRICH_ENABLED = os.getenv("VJH_ENRICH_ENABLED", "true").strip().lower() == "true"
# Below this many characters a posting cannot be judged on its merits.
THIN_DESCRIPTION_CHARS = int(os.getenv("VJH_THIN_DESC_CHARS", "400"))
FETCH_TIMEOUT_SECONDS = int(os.getenv("VJH_ENRICH_TIMEOUT", "10"))
MAX_ENRICHED_CHARS = 8000

_UA = "Mozilla/5.0 (VibeJobHunter/1.0; +https://aideazz.xyz)"

_DROP_BLOCKS = re.compile(r"<(script|style|noscript|svg|head)[^>]*>.*?</\1>", re.I | re.S)
_BREAKS = re.compile(r"</(p|div|li|tr|h[1-6]|br)\s*/?>", re.I)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\x0b\f\r]+")
_BLANKS = re.compile(r"\n{3,}")

# Some boards embed the posting as JSON-LD JobPosting — richer and cleaner than the
# rendered HTML when present.
_JSONLD = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.I | re.S)


def _html_to_text(html: str) -> str:
    txt = _DROP_BLOCKS.sub(" ", html)
    txt = _BREAKS.sub("\n", txt)
    txt = _TAGS.sub(" ", txt)
    # Entities we actually see in job posts; deliberately not a full unescape table.
    for ent, rep in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                     ("&quot;", '"'), ("&#39;", "'"), ("&rsquo;", "'"), ("&mdash;", "—")):
        txt = txt.replace(ent, rep)
    txt = _WS.sub(" ", txt)
    return _BLANKS.sub("\n\n", txt).strip()


def _from_jsonld(html: str) -> Optional[str]:
    """Pull description + salary out of a JobPosting JSON-LD block if one exists."""
    import json
    for m in _JSONLD.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            if "JobPosting" not in str(node.get("@type", "")):
                continue
            parts = []
            desc = node.get("description")
            if isinstance(desc, str) and desc:
                parts.append(_html_to_text(desc))
            # Structured pay is the most reliable salary signal there is — keep it
            # verbatim so salary_gate can parse it.
            salary = node.get("baseSalary")
            if isinstance(salary, dict):
                value = salary.get("value")
                if isinstance(value, dict):
                    unit = str(value.get("unitText", "")).lower()
                    lo, hi = value.get("minValue"), value.get("maxValue")
                    single = value.get("value")
                    cur = str(salary.get("currency") or value.get("currency") or "USD")
                    per = {"hour": "per hour", "day": "per day", "week": "per week",
                           "month": "per month", "year": "per year"}.get(unit, "")
                    if lo or hi:
                        parts.append(f"Salary: {cur} {lo or hi} - {hi or lo} {per}".strip())
                    elif single:
                        parts.append(f"Salary: {cur} {single} {per}".strip())
            if parts:
                return "\n\n".join(parts)
    return None


def enrich_description(url: str, description: str, force: bool = False) -> str:
    """
    Return a fuller description for `url`, or `description` unchanged.

    Only fetches when the current text is thinner than THIN_DESCRIPTION_CHARS
    (unless force=True).
    """
    original = description or ""
    if not ENRICH_ENABLED or not url or not str(url).startswith(("http://", "https://")):
        return original
    if not force and len(original) >= THIN_DESCRIPTION_CHARS:
        return original

    try:
        import requests
        resp = requests.get(
            url,
            headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"},
            timeout=FETCH_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if resp.status_code != 200:
            logger.debug(f"[enrich] HTTP {resp.status_code} for {url}")
            return original
        if "html" not in resp.headers.get("Content-Type", "").lower():
            return original

        html = resp.text
        text = _from_jsonld(html) or _html_to_text(html)

        # Never trade down: a nav-only page can render shorter than the stub we had.
        if len(text) <= max(len(original), THIN_DESCRIPTION_CHARS // 2):
            logger.debug(f"[enrich] fetched text too thin ({len(text)}c) — keeping original")
            return original

        enriched = text[:MAX_ENRICHED_CHARS]
        logger.info(f"[enrich] {len(original)}c → {len(enriched)}c from {str(url)[:70]}")
        # Keep the original line: it sometimes carries the region tag ("[Remote role
        # via Torre.ai]") that iron_clad_fit reads.
        return f"{original}\n\n{enriched}" if original else enriched

    except Exception as e:
        logger.debug(f"[enrich] failed for {str(url)[:70]}: {e}")
        return original
