"""
📱 TELEGRAM QA HELPER — Professional AI Engineering Job Search Assistant

Answers ANY question (voice or text) with deep, honest, actionable responses.
Uses real data + Claude for a true personal assistant experience.

Data sources (read-only):
- autonomous_data/seen_jobs.json (status=applied)
- autonomous_data/submissions/submission_log.json
- autonomous_data/outreach_log.jsonl
- autonomous_data/manual_outreach_queue.json
- autonomous_data/ats_cache/ (recent jobs)
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def _today_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_today(iso_str: str) -> bool:
    """Check if ISO timestamp is today (UTC)."""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.date() == _today_utc().date()
    except Exception:
        return False


def _load_seen_jobs_applied_today() -> List[Dict]:
    """Load jobs marked as applied today from seen_jobs.json."""
    path = Path("autonomous_data/seen_jobs.json")
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text())
        db = data.get("seen_jobs_v2", data.get("seen_jobs", {}))
        if isinstance(db, list):
            return []

        result = []
        for job_id, rec in db.items():
            if rec.get("status") != "applied":
                continue
            applied_at = rec.get("applied_at") or rec.get("last_seen", "")
            if _is_today(applied_at):
                result.append({
                    "company": rec.get("company", "Unknown"),
                    "title": rec.get("title", ""),
                    "job_id": job_id,
                })
        return result
    except Exception:
        return []


def _load_submission_log_today() -> List[Dict]:
    """Load submissions from today (submitted or dry_run)."""
    path = Path("autonomous_data/submissions/submission_log.json")
    if not path.exists():
        return []

    try:
        entries = json.load(path)
        result = []
        for e in entries:
            if e.get("status") not in ("submitted", "dry_run"):
                continue
            ts = e.get("timestamp", "")
            if _is_today(ts):
                result.append({
                    "company": e.get("company", "Unknown"),
                    "title": e.get("title", ""),
                    "status": e.get("status", "submitted"),
                })
        return result
    except Exception:
        return []


def get_applied_today() -> List[str]:
    """
    Get list of company names we applied to today.
    Merges seen_jobs (status=applied) + submission_log.
    Returns unique companies (honest, no duplicates).
    """
    companies = set()
    for rec in _load_seen_jobs_applied_today():
        c = rec.get("company", "").strip()
        if c and c != "Unknown":
            companies.add(c)
    for rec in _load_submission_log_today():
        c = rec.get("company", "").strip()
        if c and c != "Unknown":
            companies.add(c)
    return sorted(companies)


def get_applied_count_today() -> int:
    """Count applications submitted today."""
    seen = _load_seen_jobs_applied_today()
    sub = _load_submission_log_today()
    # Dedupe by company+title
    keys = set()
    for r in seen:
        keys.add((r.get("company", ""), r.get("title", "")))
    for r in sub:
        keys.add((r.get("company", ""), r.get("title", "")))
    return len(keys)


def _is_within_days(iso_str: str, days: int) -> bool:
    """Check if ISO timestamp is within last N days (UTC)."""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (_today_utc() - dt).days <= days
    except Exception:
        return False


def _load_applied_last_7d() -> List[Dict]:
    """Load applications from last 7 days (seen_jobs + submission_log)."""
    result = []
    path = Path("autonomous_data/seen_jobs.json")
    if path.exists():
        try:
            data = json.loads(path.read_text())
            db = data.get("seen_jobs_v2", {})
            if isinstance(db, dict):
                for job_id, rec in db.items():
                    if rec.get("status") != "applied":
                        continue
                    applied_at = rec.get("applied_at") or rec.get("last_seen", "")
                    if _is_within_days(applied_at, 7):
                        result.append({
                            "company": rec.get("company", "Unknown"),
                            "title": rec.get("title", ""),
                        })
        except Exception:
            pass
    sub_path = Path("autonomous_data/submissions/submission_log.json")
    if sub_path.exists():
        try:
            for e in json.load(sub_path):
                if e.get("status") not in ("submitted", "dry_run"):
                    continue
                if _is_within_days(e.get("timestamp", ""), 7):
                    result.append({
                        "company": e.get("company", "Unknown"),
                        "title": e.get("title", ""),
                    })
        except Exception:
            pass
    return result


def _load_recent_top_jobs(limit: int = 10) -> List[Dict]:
    """Load top jobs from latest ATS cache (by score if available)."""
    cache_dir = Path("autonomous_data/ats_cache")
    if not cache_dir.exists():
        return []
    files = sorted([f for f in cache_dir.glob("jobs_*.json")], key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return []
    try:
        data = json.loads(files[0].read_text())
        jobs = data.get("jobs", [])
        if not jobs:
            return []
        scored = [j for j in jobs if isinstance(j.get("match_score"), (int, float))]
        scored.sort(key=lambda j: j.get("match_score", 0), reverse=True)
        return scored[:limit] if scored else jobs[:limit]
    except Exception:
        return []


def _load_pending_outreach_details() -> List[Dict]:
    """Load pending outreach with company/contact info."""
    result = []
    for p in [Path("autonomous_data/manual_outreach_queue.json"), Path("autonomous_data/outreach_log.jsonl")]:
        if not p.exists():
            continue
        try:
            if p.suffix == ".jsonl":
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            e = json.loads(line)
                            if e.get("status") in ("pending_manual_send", "pending"):
                                result.append({
                                    "company": e.get("company", "Unknown"),
                                    "contact": e.get("contact_name", "Founder"),
                                })
                        except json.JSONDecodeError:
                            continue
            else:
                raw = json.load(p)
                items = raw if isinstance(raw, list) else raw.get("messages", [])
                for m in items:
                    if m.get("status") in ("pending_manual_send", "pending", ""):
                        result.append({
                            "company": m.get("company", "Unknown"),
                            "contact": m.get("contact_name", m.get("contact", "Founder")),
                        })
        except Exception:
            pass
    return result


def get_pending_outreach_count() -> int:
    """Count pending outreach messages."""
    count = 0
    for path in ["autonomous_data/manual_outreach_queue.json", "autonomous_data/outreach_log.jsonl"]:
        p = Path(path)
        if not p.exists():
            continue
        try:
            if path.endswith(".jsonl"):
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            e = json.loads(line)
                            if e.get("status") in ("pending_manual_send", "pending"):
                                count += 1
                        except json.JSONDecodeError:
                            continue
            else:
                data = json.load(p)
                items = data if isinstance(data, list) else data.get("messages", [])
                for m in items:
                    if m.get("status") in ("pending_manual_send", "pending", ""):
                        count += 1
        except Exception:
            pass
    return count


def answer_job_question(text: str) -> str:
    """
    Answer job-focused questions from real data.
    Simple intent matching — no LLM needed for honesty.
    """
    t = (text or "").lower().strip()
    if not t:
        return "Ask me something about your job hunt! Try: \"What companies did I apply to today?\" or use /today, /stats."

    # "applied today" / "companies applied" / "who did you apply to"
    if any(k in t for k in ["applied", "applications", "companies", "who", "where"]) and \
       any(k in t for k in ["today", "this week", "recent", "so far"]):
        companies = get_applied_today()
        count = get_applied_count_today()
        if not companies and count == 0:
            return "📋 I haven't applied to any companies today yet. Next cycle runs hourly — check back after the next run."
        if companies:
            msg = f"📋 *Today I applied to:*\n\n"
            for c in companies[:15]:  # cap at 15
                msg += f"• {c}\n"
            if len(companies) > 15:
                msg += f"\n_...and {len(companies) - 15} more._\n"
            msg += f"\n✅ Total: {count} application(s) today."
            return msg
        return f"✅ I submitted {count} application(s) today (companies in logs). Use /today for full summary."

    # "how many applied"
    if any(k in t for k in ["how many", "count", "number"]) and "applied" in t:
        count = get_applied_count_today()
        return f"📊 Today: *{count}* application(s) submitted."

    # "pending" / "outreach"
    if any(k in t for k in ["pending", "outreach", "linkedin", "messages to send"]):
        n = get_pending_outreach_count()
        if n == 0:
            return "✅ No pending outreach messages. Use /outreach to see when new ones appear."
        return f"📨 You have *{n}* pending outreach message(s). Use /outreach to see them."

    # "stats" / "summary" / "how am i doing" → Claude for deep response
    # (keyword path skipped — Claude gives richer, professional answer)

    # Everything else: Claude for deep, honest, professional answers
    return _answer_with_claude(text)


def _build_rich_context() -> str:
    """Build full context for Claude — real data + career profile."""
    companies_today = get_applied_today()
    count_today = get_applied_count_today()
    pending_count = get_pending_outreach_count()
    applied_7d = _load_applied_last_7d()
    top_jobs = _load_recent_top_jobs(8)
    pending_details = _load_pending_outreach_details()

    # Dedupe applied last 7d by company
    applied_7d_companies = list(dict.fromkeys([r["company"] for r in applied_7d if r.get("company") and r["company"] != "Unknown"]))

    lines = [
        "=== ELENA'S PROFILE (AI Products & Personal Assistants) ===",
        "Focus: AI product building — creating AI products and AI Personal Assistants (e.g. OpenClaw by Peter Steinberger). One of several target areas.",
        "Target roles: Founding Engineer, Senior AI Engineer, AI Product Engineer, Staff Engineer, Principal Engineer, AI Solutions Architect, AI Product Manager",
        "Positioning: Founder-level AI product builder, 0→1, autonomous systems, AI assistants. 10 yrs exp, Panama, remote. Skills: Python, TypeScript, Claude, LLMs, FastAPI, PostgreSQL, Docker, Oracle Cloud.",
        "Platforms: Greenhouse, Lever, Ashby, Workable, Dice MCP, YC, RemoteOK, HN Who's Hiring. Auto-apply threshold: 60. Outreach threshold: 58.",
        "",
        "=== REAL DATA (from VibeJobHunter logs) ===",
        f"Applications TODAY: {count_today}",
        f"Companies applied to TODAY: {', '.join(companies_today) if companies_today else 'none'}",
        f"Applications in LAST 7 DAYS: {len(applied_7d)} ({', '.join(applied_7d_companies[:12])}{'...' if len(applied_7d_companies) > 12 else ''})",
        f"Pending outreach (LinkedIn to send): {pending_count}",
    ]
    if pending_details:
        lines.append("Pending outreach companies: " + ", ".join([f"{r['company']} ({r['contact']})" for r in pending_details[:8]]))
    if top_jobs:
        lines.append("Recent top-scoring jobs in pipeline:")
        for j in top_jobs[:5]:
            co = j.get("company", "?")
            ti = (j.get("title") or "?")[:40]
            sc = j.get("match_score", 0)
            lines.append(f"  - {co}: {ti} (score {sc})")
    return "\n".join(lines)


def _answer_with_claude(question: str) -> str:
    """
    Claude as professional AI engineering job search assistant.
    Deep, honest, actionable answers — not generic chatbot replies.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return _fallback_suggestions()
    except ImportError:
        return _fallback_suggestions()

    context = _build_rich_context()
    prompt = f"""You are Elena's professional job hunting personal assistant. Her focus: AI product building — including AI Personal Assistants (e.g. OpenClaw-style), AI products, founding/staff-level roles. You have access to her REAL data below. Your job is to give DEEP, HONEST, ACTIONABLE responses — not generic chatbot replies.

RULES:
1. Use ONLY the real data provided. Never invent numbers or companies.
2. Be honest: if data is missing or thin, say so and suggest what would help.
3. Give substance: 2–6 sentences with concrete facts, not fluff.
4. For strategy/advice questions: use her profile + real data to give tailored advice.
5. For "how am I doing" / status: summarize the data meaningfully.
6. Format for Telegram: clear, scannable. Use bullet points if helpful.
7. You are her assistant — professional but warm, outcome-focused.

{context}

Question: {question}

Your answer:"""

    try:
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip() if response.content else ""
        if text:
            return text
    except Exception as e:
        logger.warning(f"Claude QA fallback: {e}")

    return _fallback_suggestions()


def _fallback_suggestions() -> str:
    return (
        "I answer questions about your job hunt using real data. Try:\n\n"
        "• _What companies did I apply to today?_\n"
        "• _How many applications today?_\n"
        "• _Any pending outreach?_\n\n"
        "Or use /today, /stats, /outreach for summaries."
    )
