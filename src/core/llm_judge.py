"""
LLM judge (Groq, free) — the PRECISION layer of the VJH pipeline.

The keyword gate + iron_clad_fit are generous (high RECALL: catch every AI candidate).
This judge evaluates each candidate against Elena's EXACT criteria right before it would
surface to her Telegram/HubSpot (high PRECISION: veto "Senior Counsel @ AI-company" etc.).

Runs only on the handful of jobs about to surface (post-gate, post-score), so Groq calls
are few. FAIL-OPEN: if Groq is unavailable, returns fit=True so the pipeline still fires
(better to surface an unjudged job than to silently drop everything).
"""

import os
import json
import re
import urllib.request

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"

_PROMPT = """You are screening ONE job for Elena, an AI-AUGMENTED BUILDER who ships products
using AI tools (Claude Code, Cursor, GPT). She has NO formal computer-science degree and does
NOT do hardcore hand-coding or leetcode-style interviews. She is based in Panama (Latin America,
UTC-5) and works fully remote.

APPROVE the job ONLY IF ALL of these are true:
1. FULLY REMOTE (work from anywhere / worldwide) — NOT hybrid, NOT onsite.
2. OPEN TO LATIN AMERICA / PANAMA (worldwide, Americas, LATAM, or no country restriction) —
   NOT US-only, NOT restricted to a single other country/region.
3. An AI / AI-augmented / automation / AI-solutions / builder role doable by BUILDING WITH AI
   TOOLS — NOT one that requires years of professional software engineering, a CS degree, or
   heavy algorithms / data-structures.
4. A role Elena would actually want — NOT legal/counsel, sales, recruiter, developer-relations
   (devrel), developer-advocate, marketing, finance, HR, executive/VP/director, or data-entry.

JOB:
Title: {title}
Company: {company}
Location: {location}
Description: {desc}

Respond with ONLY JSON, nothing else: {{"fit": true or false, "reason": "<one short sentence>"}}"""


def judge_fit(title: str, company: str, location: str, desc: str) -> tuple:
    """Judge a job against Elena's criteria. Returns (is_fit: bool, reason: str).
    FAIL-OPEN: returns (True, ...) if Groq is unavailable or errors."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return True, "judge unavailable (no GROQ_API_KEY) — fail-open"
    prompt = _PROMPT.format(
        title=(title or "")[:160], company=(company or "")[:80],
        location=(location or "")[:80], desc=(desc or "")[:1500])
    try:
        payload = json.dumps({
            "model": _GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 120, "temperature": 0,
        }).encode()
        req = urllib.request.Request(
            _GROQ_URL, data=payload, method="POST",
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                     "User-Agent": "Mozilla/5.0 (VJH judge)"})  # Cloudflare 403s default urllib UA
        raw = urllib.request.urlopen(req, timeout=25).read().decode()
        text = json.loads(raw)["choices"][0]["message"]["content"]
        m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if not m:
            return True, "judge parse-fail — fail-open"
        result = json.loads(m.group())
        return bool(result.get("fit", True)), str(result.get("reason", ""))[:120]
    except Exception as e:
        return True, f"judge error ({str(e)[:40]}) — fail-open"
