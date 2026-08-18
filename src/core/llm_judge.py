"""
LLM judge — the PRECISION layer of the VJH pipeline.

The keyword gate + iron_clad_fit are generous (high RECALL: catch every AI candidate).
This judge evaluates each candidate against Elena's EXACT criteria right before it would
surface to her Telegram/HubSpot (high PRECISION: veto "Senior Counsel @ AI-company" etc.).

Runs only on the handful of jobs about to surface (post-gate, post-score), so cost is tiny.
Provider order: OpenAI gpt-4o-mini (reliable, ~fractions of a cent) → Groq (free; model id
via model_config.groq_model(), switched fleet-wide with the GROQ_MODEL env var).
FAIL-OPEN: if both are unavailable, returns fit=True so the pipeline still fires.
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

_PROMPT = """You are screening ONE job for Elena, an AI-AUGMENTED BUILDER who ships products
using AI tools (Claude Code, Cursor, GPT). She has NO formal computer-science degree and does
NOT do hardcore hand-coding or leetcode-style interviews. She is based in Panama (Latin America,
UTC-5) and works fully remote.

APPROVE the job ONLY IF ALL of these are true:
1. FULLY REMOTE (work from anywhere / worldwide) — NOT hybrid, NOT onsite.
2. OPEN TO LATIN AMERICA / PANAMA (worldwide, Americas, LATAM, or no country restriction) —
   NOT US-only, NOT restricted to a single other country/region.
3. The role is in one of Elena's FOUR target lanes:
   a) AI-AUGMENTED PRODUCTS / AGENTS / SYSTEMS BUILDER — e.g. "AI Engineer", "AI Agents
      Engineer", "AI Automation Engineer", "AI Solutions Engineer", "Founding AI Engineer",
      "Forward-Deployed Engineer", "AI Product Owner/Builder". Elena builds AI systems USING
      AI tools, so the word "Engineer" is NOT a disqualifier.
   b) GEO / AEO / TECHNICAL SEO — generative-engine & answer-engine optimization, AI-crawler
      visibility, structured data, AI search visibility. She built a full production
      AEO/GEO/tech-SEO stack.
   c) AI AUTOMATION or other AI-AUGMENTED ENGINEERING SOLUTIONS ARCHITECT — designing and
      wiring AI/automation solutions for clients or products.
   d) AI-QUALIFIED EXECUTIVE SUPPORT — "AI Chief of Staff", "AI Executive Assistant",
      "AI-Proficient Executive/Personal Assistant", "AI-Forward EA to the CEO/Founder", and
      similar. APPROVE these when the role is explicitly AI-qualified: the work is running
      and AUTOMATING a founder's or executive's operations with AI tools (ChatGPT/Claude,
      Zapier/Make/n8n, agents, research and reporting automation). This is a deliberate
      lane, not an exception — Elena spent seven years as Deputy CEO and now builds the
      automation, so an AI-qualified chief-of-staff/EA seat is a genuine fit.
      DISQUALIFY only the NON-AI version: generic administrative, secretarial, calendar-only,
      household / personal / lifestyle / travel-concierge assistants, or any assistant role
      with no AI or automation component in the work itself.
   DISQUALIFY for this criterion if the job explicitly requires years of professional
   software engineering, a computer-science degree, leetcode / competitive programming,
   or deep low-level/systems/infra coding.
4. A role Elena would actually want — NOT pure ML/AI RESEARCH (research scientist, research
   engineer, academic/lab research), NOT legal/counsel, sales, recruiter, developer-relations
   (devrel), developer-advocate, marketing, finance, HR, or data-entry. She is a hands-on
   BUILDER and ARCHITECT, not a researcher.
   "Executive" here means executive LEADERSHIP she would be hired INTO — VP, Director,
   Head of, C-level. It does NOT mean "Executive Assistant": an AI-qualified EA / chief of
   staff is lane 3(d) above and must NOT be vetoed by this criterion.
5. The EMPLOYER is one she can realistically be hired by: startups, scale-ups, product
   companies, agencies, and fractional / contract engagements. DISQUALIFY when the employer
   is a very large enterprise or conglomerate (roughly 5,000+ employees — Fortune-500 or
   publicly-traded giant, big bank, big insurer, big healthcare, big retail, big telecom),
   a staffing / body-shop / IT-outsourcing firm, or a recruiter posting on behalf of one.
   Judge this from what you KNOW about the named company, not only from the listing text.
   Apply this EVEN IF the listing claims remote / worldwide / LATAM: aggregators relabel
   geography, and at that scale "remote" is nearly always country-locked in practice and
   hiring runs through ATS pipelines Elena does not clear. Her documented path is founders,
   operators and fractional work — not enterprise ATS funnels.

{feedback}JOB:
Title: {title}
Company: {company}
Location: {location}
Description: {desc}

Respond with ONLY JSON, nothing else: {{"fit": true or false, "reason": "<one short sentence>"}}"""


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
        if not pos and not neg:
            return ""
        lines = ["REAL RECENT OUTCOMES from Elena's own pipeline (taste calibration refreshed daily —",
                 "these refine your judgment but do NOT override criteria 1-4 above):"]
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
    return bool(result.get("fit", True)), str(result.get("reason", ""))[:120]


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
