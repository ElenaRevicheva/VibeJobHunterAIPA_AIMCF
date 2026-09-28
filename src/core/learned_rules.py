"""
learned_rules.py — rules VJH learned from Elena's own rejections, enforced before the judge.

WHY (27 Sep 2026). Her rejections reached ONE component — the LLM judge — as few-shot text,
with the instruction that they "do NOT override criteria 1-7". So a lesson as crisp as
"HireLATAM only hires specialists born in LATAM" could never block anything, and the Google-Jobs
path that fills 🔥 I Act TODAY never asked the judge at all. Evolution only happened when an
agent hand-edited fit_gate.py after she complained.

This module is the missing link. scripts/judge_feedback_sync.py reads EVERY decision she has made
(not an 8-day window), classifies her reasons, and writes autonomous_data/learned_rules.json. The
matchers below enforce those rules on every door into I Act TODAY — the Google-Jobs ingest and the
LangGraph submit node — BEFORE the judge. A rule exists only if one of her rejections taught it,
and each carries its provenance (`taught_by`), so every veto is traceable to her own words.

What is learned here is deliberately CRISP. Fuzzy judgement ("is this mostly hand-coding?") stays
with the LLM judge, which now receives a summary of ALL her lessons and may act on them. Rules
that iron_clad_fit already enforces by hand (country rosters, CS degree, years of software
engineering) are not duplicated.

FAIL-SAFE: file missing, unreadable, or malformed → no rules → behaviour identical to before.
Stdlib only: `serpapi-jobs` runs under the system python3, not the venv.
"""

import json
import re
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[2] / "autonomous_data" / "learned_rules.json"

_cache = {"mtime": None, "rules": {}}


def load_rules(path: Path = None) -> dict:
    """The learned rules, re-read only when the file changes. {} on any problem."""
    p = path or RULES_PATH
    try:
        m = p.stat().st_mtime
        if _cache["mtime"] == m and path is None:
            return _cache["rules"]
        data = json.loads(p.read_text(encoding="utf-8"))
        rules = data.get("rules", {}) if isinstance(data, dict) else {}
        if path is None:
            _cache.update(mtime=m, rules=rules)
        return rules
    except Exception:
        return {}


# ── matchers (fixed code; WHICH ones apply, and with what data, is learned) ───

# She rejected "no longer open" and a screenshot reading "This job post is closed."
_CLOSED = re.compile(
    r"this job post is closed|job post is closed|this job is closed|this position is closed|"
    r"job is no longer available|no longer accepting applications|position has been filled|"
    r"(?:posting|job) has expired|this job has expired|applications are (?:now )?closed|"
    r"vacante cerrada|esta vacante (?:est[aá] )?cerrada",
    re.IGNORECASE,
)

# Eligibility she cannot meet from Panama. Each pattern is enabled only if a reason taught it.
_ELIGIBILITY = {
    # About PEOPLE being born somewhere — never "our company was born in Berlin".
    "born_in": re.compile(
        r"\b(?:candidates?|specialists?|professionals?|applicants?|talent|people|engineers?|"
        r"developers?|those|you|must be|hires?|hiring)\b[^.\n]{0,40}\bborn in\b|"
        r"\bborn in (?:latin america|latam|the us|the usa|the united states)\b", re.IGNORECASE),
    "citizenship": re.compile(
        r"\b(?:usc|u\.?s\.? citizens?)\s*(?:or|/|and)\s*(?:gc|green card)\b|"
        r"\bcitizens? only\b|\bmust be a (?:u\.?s\.? )?citizen\b", re.IGNORECASE),
    "w2_only": re.compile(r"\bw-?2\s*(?:only|employment|basis|required)\b", re.IGNORECASE),
}

# "Remote (US, CA, UK, IE, AU, NZ)" — a list of 2-letter codes that fit_gate's country WORDS miss.
# Two-letter COUNTRY codes only — "(AI, ML)" or "(QA, UX)" in a job body is not a residency list.
_CC = (r"(?:US|CA|UK|GB|IE|AU|NZ|DE|FR|ES|PT|IT|NL|BE|PL|RO|IN|PH|BR|MX|AR|CO|CL|PE|UY|IL|SG|JP|KR|CN|"
       r"ZA|NG|KE|EG|TR|UA|SE|NO|DK|FI|CH|AT|CZ)")
_CODE_LIST = re.compile(r"\(\s*(" + _CC + r"(?:\s*[,/]\s*" + _CC + r"){1,})\s*\)")
_HOME_CODES = {"PA"}
_HOME_WORDS = ("panama", "latam", "latin america", "americas", "worldwide", "anywhere", "global")

_GENERIC_TITLE_WORDS = {
    "specialist", "manager", "senior", "sr", "junior", "jr", "lead", "remote", "head", "of", "and",
    "the", "a", "an", "for", "to", "in", "at", "i", "ii", "iii", "contract", "contractor",
    "full", "time", "part", "freelance", "latam", "latin", "america",
}


def _tokens(title: str) -> set:
    words = re.findall(r"[a-z0-9.+]+", (title or "").lower())
    return {w for w in words if w not in _GENERIC_TITLE_WORDS and len(w) > 1}


def norm_company(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower().replace("%20", " ")).strip()


def learned_veto(title: str, company: str, text: str, rules: dict = None) -> tuple:
    """(True, reason) if a rule Elena taught blocks this job; (False, '') otherwise.

    `text` is everything known about the posting (location + description). Never raises.
    """
    try:
        r = load_rules() if rules is None else rules
        if not r:
            return False, ""
        t_low = (title or "").lower()
        blob = f"{title or ''}\n{text or ''}"

        rule = r.get("closed_posting")
        if rule and rule.get("enabled") and _CLOSED.search(blob):
            return True, _why("closed_posting", "the posting says it is closed", rule)

        for code in r.get("eligibility", {}).get("patterns", []):
            rx = _ELIGIBILITY.get(code)
            if rx and rx.search(blob):
                return True, _why("eligibility", f"eligibility she cannot meet ({code})", r["eligibility"])

        rule = r.get("country_code_list")
        if rule and rule.get("enabled"):
            for m in _CODE_LIST.finditer(blob):
                codes = {c.strip().upper() for c in re.split(r"[,/]", m.group(1))}
                window = blob[max(0, m.start() - 60):m.end() + 60].lower()
                if not codes & _HOME_CODES and not any(w in window for w in _HOME_WORDS):
                    return True, _why("country_code_list",
                                      f"location limited to {', '.join(sorted(codes))}", rule)

        rule = r.get("tools_not_hers")
        if rule and rule.get("enabled"):
            for tool in rule.get("tools", []):
                if re.search(r"(?<![a-z0-9])" + re.escape(tool) + r"(?![a-z0-9])", t_low):
                    return True, _why("tools_not_hers", f"a role centred on {tool}, which she does not use", rule)

        rule = r.get("rejected_companies")
        if rule and rule.get("enabled"):
            c = norm_company(company)
            if c and c in set(rule.get("companies", [])):
                return True, _why("rejected_companies", f"a company she rejected {rule['counts'].get(c, 3)}+ times", rule)

        rule = r.get("out_of_field_titles")
        if rule and rule.get("enabled"):
            mine = _tokens(title)
            for bad in rule.get("titles", []):
                theirs = _tokens(bad)
                if mine and theirs and len(mine & theirs) / len(mine | theirs) >= 0.75:
                    return True, _why("out_of_field_titles", f"the same kind of role as '{bad}'", rule)
    except Exception:
        return False, ""
    return False, ""


def _why(code: str, what: str, rule: dict) -> str:
    taught = rule.get("taught_by") or []
    src = f" — taught by {taught[0]}" + (f" (+{len(taught) - 1} more)" if len(taught) > 1 else "") if taught else ""
    return f"LEARNED {code}: {what}{src}"[:240]
