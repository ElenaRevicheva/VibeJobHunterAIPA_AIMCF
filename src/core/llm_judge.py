"""
LLM judge — the PRECISION layer of the VJH pipeline.

The keyword gate + iron_clad_fit are generous (high RECALL: catch every AI candidate).
This judge evaluates each candidate against Elena's EXACT criteria right before it would
surface to her Telegram/HubSpot (high PRECISION: veto "Senior Counsel @ AI-company" etc.).

Runs only on the handful of jobs about to surface (post-gate, post-score), so cost is tiny.

PROVIDER ORDER — five tiers, and the order is NOT the fleet default (2026-08-29):

    1. OpenAI  gpt-4o-mini   reliable, ~fractions of a cent  ← serves virtually every call
    2. Gemini
    3. Groq                  free; model id via model_config.groq_model()
    4. xAI / Grok
    5. Claude                LAST on purpose — see the comment at the tier itself

Claude is deliberately the LAST tier here, not the first. It is the most reliable and
the most expensive, and this judge is the highest-volume LLM caller in the fleet, so
reaching tier 5 means four providers are down simultaneously — a situation worth
paying to survive, and only that situation.

This ordering is per USE CASE and differs from the classification path, which is
Anthropic-first. A consequence worth stating plainly, because it looks alarming in
the logs and is not: when Anthropic credits ran out on 2026-08-17, the classifier
started logging "Anthropic unavailable" on every call while THIS JUDGE was completely
unaffected — it had never reached tier 5. Verified 2026-08-29: zero JUDGE_UNAVAILABLE
events in 14 days.

FAIL-OPEN: if all five are unavailable, returns fit=True so the pipeline still fires —
but tagged JUDGE_UNAVAILABLE (see below) so an unjudged job never wears a vetted badge.
"""

import logging
import os
import json
import re
import urllib.request

logger = logging.getLogger(__name__)

# A judge that cannot judge must SAY SO, and say WHY (2026-08-07).
# Previously every provider error was swallowed by `except Exception: pass` and the
# caller received a bland "judge unavailable (no LLM)" — indistinguishable in the
# logs from a judge that ran and approved. Silence shaped like success is the
# failure mode this project keeps being bitten by. Callers detect this prefix and
# label the surfaced job, so an unjudged job never wears a vetted badge.
JUDGE_UNAVAILABLE = "JUDGE UNAVAILABLE"

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
from ..utils.model_config import groq_model  # THE one Groq model switch (GROQ_MODEL env)
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL = os.environ.get("OPENAI_JUDGE_MODEL", "").strip() or "gpt-4o-mini"

# ── The rest of the chain (added 2026-08-16) ────────────────────────────────
#
# Order is chosen for THIS use case, not copied from the other agents. The judge
# runs on every job in a high-volume pipeline and needs ~20 words back, so:
#
#   1. openai gpt-4o-mini  — proven primary, PLAIN model, pennies/month
#   2. gemini flash-lite   — FREE and plain; catches an OpenAI outage at zero cost
#   3. groq gpt-oss-120b   — free, but reasoning: needs the 300-token budget
#   4. grok                — team credits
#   5. claude haiku        — paid, most reliable, deliberately LAST because the
#                            judge is the highest-volume caller in the fleet;
#                            Claude belongs FIRST in message_generator, where a
#                            human reads the output, not here.
#
# Every model named here is verified by evals/test_provider_chain.py to return a
# parseable verdict at JUDGE_MAX_TOKENS. Nothing joins this chain unproven.
_GEMINI_MODEL = os.environ.get("GEMINI_JUDGE_MODEL", "").strip() or "gemini-3.5-flash-lite"
_XAI_URL = "https://api.x.ai/v1/chat/completions"
_XAI_MODEL = os.environ.get("XAI_MODEL", "").strip() or "grok-4.20-0309-non-reasoning"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_CLAUDE_MODEL = os.environ.get("CLAUDE_JUDGE_MODEL", "").strip() or "claude-haiku-4-5-20251001"

# 300, not the original 120 — the budget must fit the SLOWEST provider in the chain.
#
# Groq retired llama-3.3-70b (2026-08-16) and every free-tier replacement is a
# REASONING model: it spends tokens thinking privately before it writes. At 120
# the Groq leg returned a verdict truncated mid-sentence —
#     {"fit": true, "reason": "Elena's AI
# which fails JSON parsing and fails the judge OPEN on a job it never finished
# reading. Measured floor for openai/gpt-oss-120b: >=200.
#
# Costs nothing on the plain models: max_tokens is a ceiling, not a target, so
# gpt-4o-mini, Gemini and Claude still stop the moment they are done. Proven by
# evals/test_provider_chain.py — 120: groq FAILED, 300: all five PASSED.
_MAX_TOKENS = int(os.environ.get("JUDGE_MAX_TOKENS", "300"))

# 2026-09-16: the lane block is RENDERED from src/core/target_lanes.py — the same list
# the AI scoring prompt uses and evals/test_target_lanes.py checks against every gate.
# Before this, "AI Product Manager" was opened in the gates and the searches on
# 2026-08-05 and never reached this prompt, so those jobs scored 85-100 and were vetoed
# here as "not a hands-on builder". Criteria 2, 5 and 7 close the other veto failures
# seen in production: US Eastern hours read as incompatible with Panama, customers
# counted as employees, and opinions or guesses about a company used as reasons.
from .target_lanes import render_lanes_for_prompt  # noqa: E402

_PROMPT_TEMPLATE = """You are screening ONE job for Elena Revicheva. Decide whether it deserves HER time.

WHO SHE IS
- An AI-augmented operator, product lead and solutions architect. Seven years as Deputy CEO
  and Chief Legal Officer, running large regulated digital-transformation programs at board
  level. Since May 2025 she has designed, shipped and run twelve live AI systems (agents,
  automation pipelines, CRM automation, a public AI-visibility API) as the sole architect and
  operator.
- She is also a creative director of generative media: 8 published AI films made with her own
  automated production pipeline (a bot that directs a dozen image and video models, edits,
  mixes and publishes), and 99 published poems in Russian and English. Creative AI roles that
  generate with models ARE her work.
- She builds by directing AI coding tools (Claude Code, Cursor, GPT) and reviewing what they
  produce. Python, TypeScript, APIs, LLMs, RAG, agents, integrations and system design are
  POSITIVE signals: she ships production systems in them. She does NOT hand-write code
  without AI tools and does not take leetcode or live-coding screens.
- She and her AI environment are ONE operating unit: specialized agents handle much of the
  implementation, she owns requirements, architecture, orchestration, evaluation, deployment,
  monitoring and production decisions. A listing that expects or encourages AI tools (Claude,
  Cursor, Copilot, "AI-native", "AI-first") is a POSITIVE signal: that is how she works.
- So AI product management, solution design, AI consulting, AI strategy and transformation,
  automation and AI leadership are her CORE lanes, not exceptions to a "builder" rule.
- She lives in Panama (Latin America), UTC-5 all year, works fully remote, and needs at least
  $3,000 USD per month.

APPROVE the job ONLY IF ALL of these are true:

1. FULLY REMOTE — not hybrid, not onsite, no required office days.

2. SHE CAN HOLD IT FROM PANAMA — open to Panama, Latin America, the Americas or worldwide, or no
   country restriction is stated.
   - PANAMA IS IN LATIN AMERICA AND CENTRAL AMERICA. A role open to "LATAM", "Latin America",
     "Central America" or "the Americas" INCLUDES her — never reject it for location. (Seen
     28 Sep 2026: "Senior Solutions Engineer - LATAM" rejected as "LATAM may exclude Panama".)
   - US Eastern or Central working hours (ET, CT, EST, CST, EDT, CDT, UTC-5, UTC-6) are
     COMPATIBLE: Panama is UTC-5. Never reject for requiring US Eastern/Central overlap.
   - Reject only when the listing restricts WHERE SHE MAY LIVE (US-only, a residency list of
     countries that excludes Panama, EMEA-only, one other country), or requires working
     hours clearly incompatible with UTC-5 (for example IST or APAC business hours).

3. THE ROLE IS IN ONE OF HER TARGET LANES:
__LANES__
   Judge the WORK the listing describes, not whether the title contains "engineer" or
   "builder". A title from these lanes is a strong fit signal on its own.
   EVERY lane is AI work: a role whose work has no AI, LLM, agent or automation component
   (for example a plain payments product manager, a claims-domain consultant, a copywriter)
   is NOT in a lane, whatever its title.
   CODING DISQUALIFIERS — ONLY these five, and only when the listing states them:
     (i)   a computer-science or engineering degree is REQUIRED (not "or equivalent experience");
     (ii)  a leetcode / HackerRank / live-coding / algorithmic coding test;
     (iii) deep low-level systems work (kernels, compilers, embedded, distributed-systems internals);
     (iv)  the job is mainly hand-writing production code as an individual software engineer,
           with no AI, product, solution-design, automation or leadership component;
     (v)   AI tools may NOT be used in the work or in the hiring test ("without the use of AI",
           "AI tools are not permitted during the assessment"). A request that the APPLICATION
           answers be written without AI is NOT this disqualifier.
   YEARS OF EXPERIENCE: her experience is her whole career — seven years of executive
   leadership plus the live AI systems she has built and run since May 2025. A requirement for
   N+ years of experience, of professional experience, or of product, management, leadership,
   consulting, transformation, automation or AI work is MET — never reject for it, whatever N is.
   Reject for years ONLY when the listing demands years of hand-writing code as a software
   engineer ("7+ years of professional Java development") AND the job is mainly coding —
   that is disqualifier (iv), not a seniority bar.

4. NOT one of these (NON-AI roles, unless stated otherwise):
   pure ML/AI RESEARCH (research scientist or research engineer, model-training research, PhD
   research); machine-learning ENGINEERING focused on training models; quota-carrying sales
   (account executive, SDR, BDR); recruiting; HR; legal or counsel; finance or accounting;
   generic marketing; developer relations or advocacy; data entry, data labeling or annotation
   gigs; NON-AI executive leadership (VP Sales, CFO, COO, a "Head of" anything with no AI mandate).
   AI LEADERSHIP IS A LANE: Chief AI Officer, Head / VP / Director of AI, AI Transformation
   leaders and similar are NEVER rejected for seniority.

5. THE EMPLOYER can realistically hire her: startups, scale-ups, product companies, agencies,
   consultancies, fractional or contract engagements.
   Reject when the employer has roughly 5,000 or more EMPLOYEES, or is a staffing, body-shop or
   IT-outsourcing firm, or a recruiter posting for one.
   - Count EMPLOYEES only. Customers, users, clients, partners, brands a company serves, and
     freelancers or contractors in a talent network are NOT its size ("serves 30,000
     businesses" says nothing about how many people work there).
   - Reject on size ONLY for a household-name enterprise you are CERTAIN of (a Fortune-1000
     or large publicly traded company, a Big-4 firm, a global IT-outsourcing giant). For any
     other company the size is UNKNOWN — do not reject on size, and do not estimate one.
   - A job marketplace or talent platform that relays postings (Torre, Toptal, Upwork,
     Braintrust, Get on Board) is NOT the employer; never judge its size.
   - NEVER use reputation, politics, culture, news, reviews or opinions about a company.

6. PAY — reject only if the listing STATES pay whose maximum is below $3,000 USD per month (or
   the hourly or annual equivalent). Pay that is not stated is NOT a reason to reject.

7. NO GUESSES. Reject only for a disqualifier the listing EXPLICITLY states, or a known employee
   count over the threshold in criterion 5. "May", "might", "likely", "suggests" and "could
   involve" are never grounds to reject. When the listing is silent, give the benefit of the doubt.

{feedback}JOB:
Title: {title}
Company: {company}
Location: {location}
Description: {desc}

Respond with ONLY JSON, nothing else: {{"fit": true or false, "reason": "<criterion number, then one short sentence>"}}"""

# Rendered once at import, so every caller's _PROMPT.format(...) keeps its exact signature.
_PROMPT = _PROMPT_TEMPLATE.replace("__LANES__", render_lanes_for_prompt(indent="   "))


def _feedback_block() -> str:
    """Few-shot taste calibration from Elena's REAL deal outcomes, written weekly by
    scripts/judge_feedback_sync.py into autonomous_data/judge_feedback.json.
    FAIL-SAFE: any problem (file absent, invalid JSON, empty lists) returns '' and the
    prompt is byte-identical to the pre-feature version."""
    try:
        from pathlib import Path
        p = Path(__file__).resolve().parents[2] / "autonomous_data" / "judge_feedback.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        pos = [t for t in data.get("positives", []) if isinstance(t, str) and t.strip()][:12]
        neg = [t for t in data.get("negatives", []) if isinstance(t, str) and t.strip()][:12]
        lessons = data.get("lessons_text") if isinstance(data.get("lessons_text"), str) else ""
        if not pos and not neg and not lessons:
            return ""
        lines = []
        if lessons.strip():
            # 2026-09-27: her lessons used to arrive as 12 recent examples labelled "do NOT
            # override criteria 1-7", so a reason as crisp as "only hires people born in LATAM"
            # could never veto anything. The summary covers ALL of her rejections, and when a
            # job matches one of these lessons that is a reason to reject — she is the authority
            # on her own fit. It can only REJECT; it never widens what criteria 1-7 allow.
            # Apply a lesson only on EVIDENCE. The first replay (27 Sep) showed the judge citing
            # "Location or eligibility she cannot meet" for a listing that stated no location at
            # all — a lesson turned into a guess, which criterion 7 forbids.
            lines += ["ELENA'S LESSONS — learned from her own rejections. These are HER criteria too:",
                      "reject when THIS listing itself STATES the fact a lesson is about (a country list",
                      "without Panama, a closed notice, a required degree, the tool, the company) and name",
                      "the lesson. If the listing is silent on it, criterion 7 applies — never reject by",
                      "assuming a lesson. A lesson can only reject; it never passes what criteria 1-7 reject.",
                      lessons.strip()[:1800], ""]
        lines += ["REAL RECENT OUTCOMES from Elena's own pipeline (refreshed hourly):"]
        if pos:
            lines.append("She APPLIED to these (fit):")
            lines += ["  - " + t for t in pos]
        if neg:
            # Negatives now arrive as "Title — her reason: ...", written by
            # scripts/judge_feedback_sync.py from her own note or from the screenshot
            # she attached. One per line: a 12-way ' | ' join was unreadable once the
            # reasons were included, and the reason is the part that must land.
            lines.append("She REJECTED these (not fit) — pay attention to WHY:")
            lines += ["  - " + t for t in neg]
        if lessons.strip():
            # Placed LAST, nearest the job. Replay 27 Sep: the lessons and the location-heavy
            # examples were each harmless alone, but together they flipped Rove Concepts — a job
            # she APPLIED to, silent on location — to a reject in 2/2 runs. With this line: 3/3
            # approved, and a listing that STATES "Colombia only" is still rejected 2/2.
            lines.append("REMINDER: a listing SILENT on location or eligibility is open to her "
                         "(criterion 2). Only a restriction the listing STATES can reject.")
        return "\n".join(lines) + "\n\n"
    except Exception:
        return ""


def _post(url: str, key: str, model: str, prompt: str, extra_headers: dict) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": _MAX_TOKENS, "temperature": 0,
    }).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    raw = urllib.request.urlopen(req, timeout=25).read().decode()
    return json.loads(raw)["choices"][0]["message"]["content"]


def _post_gemini(key: str, model: str, prompt: str) -> str:
    """Gemini speaks a different shape than the OpenAI-compatible providers.

    Note there is no thinkingConfig here: gemini-3.5-flash-lite is a PLAIN model
    and REJECTS thinkingBudget with a 400. That rejection is the reason it was
    chosen — the newer 3.6/3.7 Flash models think first and returned empty at
    small budgets, exactly like Groq's reasoning line-up.
    """
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": _MAX_TOKENS, "temperature": 0},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    raw = urllib.request.urlopen(req, timeout=25).read().decode()
    cands = json.loads(raw).get("candidates") or [{}]
    parts = (cands[0].get("content") or {}).get("parts") or [{}]
    return parts[0].get("text") or ""


def _post_anthropic(key: str, model: str, prompt: str) -> str:
    """Anthropic uses x-api-key and returns content blocks, not choices."""
    payload = json.dumps({
        "model": model,
        "max_tokens": _MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(_ANTHROPIC_URL, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    raw = urllib.request.urlopen(req, timeout=25).read().decode()
    blocks = [b for b in json.loads(raw).get("content", []) if b.get("type") == "text"]
    return "".join(b.get("text", "") for b in blocks)


def _key(name: str) -> str:
    """Read an API key from os.environ, falling back to the repo .env file — the bot does
    not always load .env into os.environ, which would otherwise fail-open the judge."""
    v = os.environ.get(name, "").strip()
    if v:
        return v
    try:
        from dotenv import dotenv_values
        from pathlib import Path
        return (dotenv_values(Path(__file__).resolve().parents[2] / ".env").get(name) or "").strip()
    except Exception:
        return ""


def _call_llm(prompt: str):
    """
    OpenAI (reliable) → Groq (free).

    Returns (text, errors). `errors` records why each provider failed — a missing
    key is as much a reason as an HTTP 400, and both used to vanish into a bare
    `except: pass`. When the judge goes quiet, this is the evidence that says why.
    """
    errors = []

    ok = _key("OPENAI_API_KEY")
    if not ok:
        errors.append("openai: no API key configured")
    else:
        try:
            text = _post(_OPENAI_URL, ok, _OPENAI_MODEL, prompt, {})
            if text:
                return text, errors
            errors.append("openai: empty response")
        except Exception as e:
            errors.append(f"openai: {str(e)[:140]}")

    gem = _key("GEMINI_API_KEY")
    if not gem:
        errors.append("gemini: no API key configured")
    else:
        try:
            text = _post_gemini(gem, _GEMINI_MODEL, prompt)
            if text:
                return text, errors
            errors.append("gemini: empty response")
        except Exception as e:
            errors.append(f"gemini: {str(e)[:140]}")

    gk = _key("GROQ_API_KEY")
    if not gk:
        errors.append("groq: no API key configured")
    else:
        try:
            text = _post(_GROQ_URL, gk, groq_model(), prompt, {"User-Agent": "Mozilla/5.0 (VJH judge)"})
            if text:
                return text, errors
            errors.append("groq: empty response")
        except Exception as e:
            errors.append(f"groq: {str(e)[:140]}")

    xk = _key("XAI_API_KEY")
    if not xk:
        errors.append("grok: no API key configured")
    else:
        try:
            text = _post(_XAI_URL, xk, _XAI_MODEL, prompt, {})
            if text:
                return text, errors
            errors.append("grok: empty response")
        except Exception as e:
            errors.append(f"grok: {str(e)[:140]}")

    # Claude LAST on purpose: it is the most reliable and the most expensive, and
    # the judge is the highest-volume caller in the fleet. Reaching this line means
    # four providers are down at once, which is worth paying to survive.
    ck = _key("ANTHROPIC_API_KEY")
    if not ck:
        errors.append("claude: no API key configured")
    else:
        try:
            text = _post_anthropic(ck, _CLAUDE_MODEL, prompt)
            if text:
                return text, errors
            errors.append("claude: empty response")
        except Exception as e:
            errors.append(f"claude: {str(e)[:140]}")

    return "", errors


_CRIT2_REASON = re.compile(r"^\s*2\b")
_OPEN_TO_HER = re.compile(r"\b(latam|latin america|central america|the americas|americas|worldwide|"
                          r"anywhere in the world|work from anywhere)\b", re.IGNORECASE)
_COUNTRY_ONLY = re.compile(
    r"\b(?:only|exclusively)\b[^.\n]{0,25}\b(colombia|brazil|mexico|argentina|chile|peru|uruguay|"
    r"costa rica|guatemala|ecuador|venezuela|bolivia|paraguay|dominican|us|usa|united states|canada)\b|"
    r"\b(colombia|brazil|mexico|argentina|chile|peru|uruguay|costa rica|guatemala|ecuador|venezuela|"
    r"bolivia|paraguay|dominican|usa|united states|canada)\b[^.\n]{0,12}\bonly\b", re.IGNORECASE)


def latam_veto_is_wrong(title: str, location: str, desc: str) -> bool:
    """True when a criterion-2 (location) veto contradicts criterion 2 itself.

    Seen in production 28 Sep 2026: "Senior Solutions Engineer - LATAM @ Fin" vetoed as "LATAM may
    exclude Panama" — 3/3 runs with the old prompt, with no feedback at all, and even after an explicit
    "Panama is in Latin America" line. A prompt could not fix it, so the criterion is enforced here.
    A listing open to LATAM / the Americas / worldwide includes her UNLESS it also names a country list
    or a single country that excludes Panama — fit_gate's rosters, or "Colombia only".
    """
    blob = f"{title or ''}\n{location or ''}\n{desc or ''}"
    if not _OPEN_TO_HER.search(blob) or _COUNTRY_ONLY.search(blob):
        return False
    try:
        from .fit_gate import roster_excludes_home, residency_excludes_home
        if roster_excludes_home(location or "") or roster_excludes_home(title or "") \
                or residency_excludes_home(desc or ""):
            return False
    except Exception:
        return False
    return True


def judge_fit(title: str, company: str, location: str, desc: str) -> tuple:
    """Judge a job against Elena's criteria. Returns (is_fit: bool, reason: str).
    FAIL-OPEN: returns (True, ...) if no provider is available."""
    prompt = _PROMPT.format(
        feedback=_feedback_block(),
        title=(title or "")[:160], company=(company or "")[:80],
        location=(location or "")[:80], desc=(desc or "")[:1500])
    text, errors = _call_llm(prompt)

    if not text:
        why = "; ".join(errors) or "no provider attempted"
        # LOUD, with the actual provider errors. Elena asked for exactly this: if the
        # judge cannot work, it must say so and say why. Still fail-open so lead flow
        # continues — but the caller labels the job as unjudged, so it can never be
        # mistaken for one the judge approved.
        logger.warning(
            f"⚖️ {JUDGE_UNAVAILABLE} — no LLM could screen '{(title or '')[:60]}' "
            f"@ {(company or '')[:40]}. Providers: {why}"
        )
        return True, f"{JUDGE_UNAVAILABLE}: {why}"[:300]

    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if not m:
        logger.warning(f"⚖️ {JUDGE_UNAVAILABLE} — model replied but no JSON found "
                       f"for '{(title or '')[:60]}': {text[:120]}")
        return True, f"{JUDGE_UNAVAILABLE}: model returned no JSON"
    try:
        result = json.loads(m.group())
    except Exception as e:
        logger.warning(f"⚖️ {JUDGE_UNAVAILABLE} — JSON parse failed "
                       f"for '{(title or '')[:60]}': {str(e)[:100]}")
        return True, f"{JUDGE_UNAVAILABLE}: JSON parse failed"
    fit, reason = bool(result.get("fit", True)), str(result.get("reason", ""))[:120]
    if not fit and _CRIT2_REASON.match(reason) and latam_veto_is_wrong(title, location, desc):
        logger.info(f"⚖️ location veto OVERRULED (listing is open to LATAM/Americas, no roster excludes "
                    f"Panama): '{(title or '')[:60]}' @ {(company or '')[:40]} — judge said: {reason[:80]}")
        return True, f"criterion-2 veto overruled — LATAM-open listing ({reason[:70]})"
    return fit, reason


def judge_health() -> tuple:
    """
    Can the judge actually judge right now? Returns (ok: bool, detail: str).

    A cheap live probe for status checks and the eval harness, so "the judge is
    working" is something you verify rather than assume.
    """
    text, errors = _call_llm('Reply with exactly this JSON: {"fit": true, "reason": "health check"}')
    if text:
        return True, "judge reachable"
    return False, "; ".join(errors) or "no provider attempted"
