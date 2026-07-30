"""
💵 SALARY FLOOR GATE (added 2026-07-30)

Elena's hard requirement is **≥ $3,000 USD / month**, and until today NOTHING in
VJH filtered on pay at all — not the career gate, not iron_clad_fit, not the
scorer, not the LLM judge. Every "I Act TODAY" card could have been a $1,200/mo
role and the system had no idea.

DESIGN RULE — this gate can only ever REJECT, never require:

    verdict "below_floor"  → the posting states pay and even its MAXIMUM is
                             under the floor. Safe to discard.
    verdict "unknown"      → no parseable USD figure. NEVER blocks. Most
                             postings omit salary; requiring it would zero out
                             lead flow, which is the opposite of the goal.
    verdict "ok"           → stated pay clears the floor.

Two more deliberate conservatism choices:
  • For a RANGE we test the TOP of the range. "$2,000-$4,000" is not rejected,
    because she could land at $4,000.
  • Only USD (and bare "$") is judged. A figure in EUR/GBP/COP/MXN returns
    "unknown" rather than a guessed conversion.

STDLIB ONLY (no pydantic, no requests) — same constraint as fit_gate.py, so the
PM2 `serpapi-jobs` process running under system python3 can import it by file
path without dragging in src/core/__init__ → config → pydantic_settings.
"""

import os
import re
from typing import List, Optional, Tuple

# Her floor. Env-overridable: she said $3,000 on 2026-07-30; an older note said
# $3,500. Change the env var, not this file, to raise it.
MIN_MONTHLY_USD = float(os.getenv("VJH_MIN_MONTHLY_USD", "3000"))

# Full-time assumptions for normalising non-monthly pay.
_HOURS_PER_MONTH = 160.0   # 40h/week × 4 weeks
_MONTHS_PER_YEAR = 12.0
_WEEKS_PER_MONTH = 4.33
_DAYS_PER_MONTH = 21.0

# Currencies we must NOT silently treat as dollars.
_FOREIGN_CURRENCY = re.compile(
    r"(?:€|£|₹|R\$|C\$|A\$|MX\$|\bEUR\b|\bGBP\b|\bINR\b|\bBRL\b|\bCOP\b|\bMXN\b|"
    r"\bARS\b|\bCLP\b|\bPEN\b|\bCAD\b|\bAUD\b|\bPLN\b|\bZAR\b)", re.I)

# A money amount: $3,000 / 3000 USD / $120k / 45.50
_AMOUNT = r"(?:US)?\$?\s?(\d{1,3}(?:[,\s]\d{3})+|\d+(?:\.\d+)?)\s?([kK])?"

# Period words that follow (or precede) an amount.
_PER_YEAR = r"(?:per\s+year|/\s?yr|/\s?year|a\s+year|annual(?:ly)?|p\.?a\.?|yearly)"
_PER_MONTH = r"(?:per\s+month|/\s?mo(?:nth)?|a\s+month|monthly|mensual)"
_PER_HOUR = r"(?:per\s+hour|/\s?hr|/\s?hour|an\s+hour|hourly)"
_PER_WEEK = r"(?:per\s+week|/\s?wk|/\s?week|a\s+week|weekly)"
_PER_DAY = r"(?:per\s+day|/\s?day|a\s+day|daily|day\s+rate)"

_PERIOD_TO_MONTHLY = {
    "year": lambda v: v / _MONTHS_PER_YEAR,
    "month": lambda v: v,
    "hour": lambda v: v * _HOURS_PER_MONTH,
    "week": lambda v: v * _WEEKS_PER_MONTH,
    "day": lambda v: v * _DAYS_PER_MONTH,
}


def _to_float(num: str, k_suffix: Optional[str]) -> Optional[float]:
    try:
        val = float(num.replace(",", "").replace(" ", ""))
    except Exception:
        return None
    if k_suffix:
        val *= 1000.0
    return val


def _infer_period(value: float, explicit: Optional[str]) -> Optional[str]:
    """Use the stated period; otherwise infer from magnitude.

    Magnitude inference is intentionally narrow: a bare "$150,000" is annual and a
    bare "$45" is hourly, but ambiguous mid-range numbers return None so they are
    ignored rather than guessed into a rejection.
    """
    if explicit:
        return explicit
    if value >= 30000:      # $30k+ with no period stated = annual
        return "year"
    if value <= 200:        # $200 or less = an hourly rate
        return "hour"
    return None


def extract_monthly_usd(text: str) -> List[Tuple[float, str]]:
    """Return every (monthly_usd, evidence) pair found. Empty when nothing parses."""
    if not text:
        return []
    blob = str(text)
    found: List[Tuple[float, str]] = []

    period_patterns = (
        ("year", _PER_YEAR), ("month", _PER_MONTH), ("hour", _PER_HOUR),
        ("week", _PER_WEEK), ("day", _PER_DAY),
    )

    # Pass 1 — amount followed by an explicit period, optionally a range:
    # "$120,000 - $150,000 per year", "$5k/month"
    for period, per_re in period_patterns:
        pattern = re.compile(
            _AMOUNT + r"(?:\s?(?:-|–|—|to)\s?" + _AMOUNT + r")?" + r"[^\n]{0,20}?" + per_re,
            re.I,
        )
        for m in pattern.finditer(blob):
            window = blob[max(0, m.start() - 25): m.end() + 25]
            if _FOREIGN_CURRENCY.search(window):
                continue
            lo = _to_float(m.group(1), m.group(2))
            hi = _to_float(m.group(3), m.group(4)) if m.group(3) else None
            # TOP of the range — never reject on the low end.
            val = max(v for v in (lo, hi) if v is not None) if (lo or hi) else None
            if val is None:
                continue
            monthly = _PERIOD_TO_MONTHLY[period](val)
            found.append((monthly, m.group(0).strip()[:80]))

    if found:
        return found

    # Pass 2 — no period stated anywhere: infer from magnitude, dollar sign required.
    for m in re.finditer(r"(?:US)?\$\s?(\d{1,3}(?:[,\s]\d{3})+|\d+(?:\.\d+)?)\s?([kK])?", blob):
        window = blob[max(0, m.start() - 25): m.end() + 25]
        if _FOREIGN_CURRENCY.search(window):
            continue
        val = _to_float(m.group(1), m.group(2))
        if val is None:
            continue
        period = _infer_period(val, None)
        if not period:
            continue
        found.append((_PERIOD_TO_MONTHLY[period](val), m.group(0).strip()[:80]))

    return found


def salary_verdict(
    title: str = "",
    description: str = "",
    extra: str = "",
    floor: Optional[float] = None,
) -> Tuple[str, Optional[float], str]:
    """
    Returns (verdict, best_monthly_usd, evidence).
      verdict: "below_floor" | "ok" | "unknown"

    Only "below_floor" is actionable — see the module docstring.
    """
    limit = MIN_MONTHLY_USD if floor is None else floor
    hits = extract_monthly_usd(" ".join(p for p in (title, description, extra) if p))
    if not hits:
        return "unknown", None, "no parseable USD figure"

    # Judge on the BEST stated figure: a posting mentioning both a $2,000 stipend
    # and a $6,000 salary should not be rejected.
    best, evidence = max(hits, key=lambda h: h[0])
    if best < limit:
        return "below_floor", best, evidence
    return "ok", best, evidence


def clears_salary_floor(title: str = "", description: str = "", extra: str = "") -> bool:
    """Convenience wrapper: False ONLY for a confidently-below-floor posting."""
    verdict, _, _ = salary_verdict(title, description, extra)
    return verdict != "below_floor"
