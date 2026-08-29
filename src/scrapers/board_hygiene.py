"""
BOARD HYGIENE - the no-fluff gate for curated job boards (added 2026-08-29)

WHY THIS EXISTS
On 2026-08-29 two curated "AI builder" boards were evaluated for VJH. One was
honest, one was a ghost town, and the marketing copy did not distinguish them:

    metric                        ai-native-builder   agentic-engineering-jobs
    newest posting on the board        19 days                32 days
    median posting age                 24 days                65 days
    posted within 30 days           99/145 (68%)            0/400 (0%)
    past the board's OWN expiry date   7 (4.8%)             399 (99.8%)
    expired but self-flagged "fresh"        -                    137

The second board advertises 1,463 listings and a polished public API. It has not
added a posting in over a month, essentially everything on it has expired by its
own dates, and its own `isFresh` flag says True on 137 postings it has already
marked expired. A board's self-reported freshness is marketing, not evidence.

So: every posting from a curated board passes through here before it reaches the
career gate. The rule is the same one that governs everything else in this repo -
trust the measurement, not the label.

WHAT GETS DROPPED
  * expired      - the board's own validThrough/expiresAt is in the past
  * stale        - posted more than MAX_AGE_DAYS ago
  * fluff        - "talent pool", "general application", "future opportunities":
                   listings that accept a CV but describe no actual opening
  * unattributed - no company name, or no way to apply

Undated postings are KEPT, not dropped. Absence of a date is missing evidence,
not evidence of staleness, and the career gate downstream still judges them.
"""

import datetime as _dt
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ai-native-builder's oldest live posting measured 34 days on 2026-08-29, so 45
# leaves real headroom while still blocking the 65-day median that made the other
# board worthless. Raise it only with a measurement in hand.
MAX_AGE_DAYS = 45

# Titles that take a CV but name no opening. These are the "no ghost listings"
# promise that boards make and do not keep.
_FLUFF_RE = re.compile(
    r"talent\s*(pool|community|network|pipeline)|general\s*application|"
    r"expression\s+of\s+interest|future\s+opportunit|evergreen\s+req|"
    r"candidate\s*pool|speculative\s+application|open\s+application|"
    r"join\s+our\s+talent",
    re.I)


def _as_date(value: Optional[str]) -> Optional[_dt.date]:
    """Parse the leading YYYY-MM-DD of an ISO date or datetime. None if unparseable."""
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def is_fluff(title: str) -> bool:
    return bool(_FLUFF_RE.search(title or ""))


def clean_board_jobs(jobs: List[Dict], source: str,
                     today: Optional[_dt.date] = None,
                     max_age_days: int = MAX_AGE_DAYS) -> List[Dict]:
    """Drop expired, stale, fluff and unattributed postings. Logs what it removed
    and why, so a board going stale shows up in the logs instead of silently
    feeding ghosts into the pipeline."""
    today = today or _dt.date.today()
    kept: List[Dict] = []
    dropped = {"expired": 0, "stale": 0, "fluff": 0, "unattributed": 0}

    for j in jobs:
        title = j.get("title") or ""
        if not title or not (j.get("company") or "").strip():
            dropped["unattributed"] += 1
            continue
        if not (j.get("url") or j.get("board_url")):
            dropped["unattributed"] += 1
            continue
        if is_fluff(title):
            dropped["fluff"] += 1
            continue

        valid_through = _as_date(j.get("valid_through") or j.get("expiresAt"))
        if valid_through and valid_through < today:
            dropped["expired"] += 1
            continue

        posted = _as_date(j.get("posted_date") or j.get("postedAt"))
        if posted and (today - posted).days > max_age_days:
            dropped["stale"] += 1
            continue

        kept.append(j)

    total_dropped = sum(dropped.values())
    if total_dropped:
        logger.info(
            "   [hygiene] %s: kept %d/%d (dropped %d expired, %d stale>%dd, "
            "%d fluff, %d unattributed)",
            source, len(kept), len(jobs), dropped["expired"], dropped["stale"],
            max_age_days, dropped["fluff"], dropped["unattributed"])
    else:
        logger.info("   [hygiene] %s: kept all %d", source, len(jobs))

    # A board that suddenly drops most of its supply is the failure mode that
    # made agentic-engineering-jobs worthless. Say so loudly rather than quietly
    # returning a short list.
    if jobs and len(kept) < len(jobs) * 0.4:
        logger.warning(
            "   [hygiene] %s FAILED HYGIENE: only %d of %d postings survived "
            "(<40%%). The board may have gone stale - re-qualify it with "
            "scripts/qualify-job-board.py before trusting it again.",
            source, len(kept), len(jobs))

    return kept
