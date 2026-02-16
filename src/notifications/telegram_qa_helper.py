"""
📱 TELEGRAM QA HELPER — Voice & free-form question answering

Additive module: answers job-focused questions from REAL data.
Used by telegram_bot_enhanced for voice + text handlers.

Data sources (read-only):
- autonomous_data/seen_jobs.json (status=applied)
- autonomous_data/submissions/submission_log.json
- autonomous_data/outreach_log.jsonl
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Tuple


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

    # "stats" / "summary"
    if any(k in t for k in ["stats", "summary", "overview", "how am i doing"]):
        count = get_applied_count_today()
        pending = get_pending_outreach_count()
        return (
            f"📊 *Quick stats today:*\n"
            f"• Applications: {count}\n"
            f"• Pending outreach: {pending}\n"
            f"\nUse /stats for full metrics, /today for details."
        )

    # Default
    return (
        "I answer questions about your job hunt using real data. Try:\n\n"
        "• _What companies did I apply to today?_\n"
        "• _How many applications today?_\n"
        "• _Any pending outreach?_\n\n"
        "Or use /today, /stats, /outreach for summaries."
    )
