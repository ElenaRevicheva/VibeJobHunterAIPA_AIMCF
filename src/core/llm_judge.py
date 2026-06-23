"""
LLM judge — the PRECISION layer of the VJH pipeline.

The keyword gate + iron_clad_fit are generous (high RECALL: catch every AI candidate).
This judge evaluates each candidate against Elena's EXACT criteria right before it would
surface to her Telegram/HubSpot (high PRECISION: veto "Senior Counsel @ AI-company" etc.).

Runs only on the handful of jobs about to surface (post-gate, post-score), so cost is tiny.
Provider order: OpenAI gpt-4o-mini (reliable, ~fractions of a cent) → Groq llama-3.3-70b (free).
FAIL-OPEN: if both are unavailable, returns fit=True so the pipeline still fires.
"""

import os
import json
import re
import urllib.request

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL = "gpt-4o-mini"

_PROMPT = """You are screening ONE job for Elena, an AI-AUGMENTED BUILDER who ships products
using AI tools (Claude Code, Cursor, GPT). She has NO formal computer-science degree and does
NOT do hardcore hand-coding or leetcode-style interviews. She is based in Panama (Latin America,
UTC-5) and works fully remote.

APPROVE the job ONLY IF ALL of these are true:
1. FULLY REMOTE (work from anywhere / worldwide) — NOT hybrid, NOT onsite.
2. OPEN TO LATIN AMERICA / PANAMA (worldwide, Americas, LATAM, or no country restriction) —
   NOT US-only, NOT restricted to a single other country/region.
3. An AI-BUILDING role. Titles like "AI Engineer", "AI Agents Engineer", "AI Automation
   Engineer", "AI Solutions Engineer", "Founding AI Engineer", "Forward-Deployed Engineer",
   "Solutions Architect (AI)" ARE a great fit — Elena builds AI systems USING AI tools, so the
   word "Engineer" is NOT a disqualifier. DISQUALIFY for this criterion ONLY if the job
   explicitly requires years of professional software engineering, a computer-science degree,
   leetcode / competitive programming, or deep low-level/systems/infra coding.
4. A role Elena would actually want — NOT legal/counsel, sales, recruiter, developer-relations
   (devrel), developer-advocate, marketing, finance, HR, executive/VP/director, or data-entry.

JOB:
Title: {title}
Company: {company}
Location: {location}
Description: {desc}

Respond with ONLY JSON, nothing else: {{"fit": true or false, "reason": "<one short sentence>"}}"""


def _post(url: str, key: str, model: str, prompt: str, extra_headers: dict) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 120, "temperature": 0,
    }).encode()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    raw = urllib.request.urlopen(req, timeout=25).read().decode()
    return json.loads(raw)["choices"][0]["message"]["content"]


def _call_llm(prompt: str) -> str:
    """OpenAI (reliable) → Groq (free). Returns model text, or '' if both fail."""
    ok = os.environ.get("OPENAI_API_KEY", "").strip()
    if ok:
        try:
            return _post(_OPENAI_URL, ok, _OPENAI_MODEL, prompt, {})
        except Exception:
            pass
    gk = os.environ.get("GROQ_API_KEY", "").strip()
    if gk:
        try:
            return _post(_GROQ_URL, gk, _GROQ_MODEL, prompt, {"User-Agent": "Mozilla/5.0 (VJH judge)"})
        except Exception:
            pass
    return ""


def judge_fit(title: str, company: str, location: str, desc: str) -> tuple:
    """Judge a job against Elena's criteria. Returns (is_fit: bool, reason: str).
    FAIL-OPEN: returns (True, ...) if no provider is available."""
    prompt = _PROMPT.format(
        title=(title or "")[:160], company=(company or "")[:80],
        location=(location or "")[:80], desc=(desc or "")[:1500])
    text = _call_llm(prompt)
    if not text:
        return True, "judge unavailable (no LLM) — fail-open"
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if not m:
        return True, "judge parse-fail — fail-open"
    try:
        result = json.loads(m.group())
    except Exception:
        return True, "judge json-fail — fail-open"
    return bool(result.get("fit", True)), str(result.get("reason", ""))[:120]
