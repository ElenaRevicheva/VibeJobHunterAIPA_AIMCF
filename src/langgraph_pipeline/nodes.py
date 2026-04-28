"""
VJH LangGraph Nodes
Each node receives JobState, does one thing, returns updated JobState fields.

Nodes wrap existing VJH logic — JobGate, JobMatcher, AutoApplicator — so we
don't rewrite business logic, we give it a stateful wrapper with checkpointing.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from .state import JobState

logger = logging.getLogger(__name__)

# ── Routing thresholds (mirrors orchestrator.py) ─────────────────────────────
SUBMIT_THRESHOLD = 70     # ≥70: auto-submit without human review
HUMAN_THRESHOLD = 60      # 60-69: pause for human approval before submitting
OUTREACH_THRESHOLD = 55   # 55-59: founder outreach only, no ATS
DISCARD_THRESHOLD = 0     # <55: discard


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: gate_node
# Runs job_gate.py filters. If fails → status=gated_out. If passes → continue.
# ─────────────────────────────────────────────────────────────────────────────
def gate_node(state: JobState) -> dict:
    """Apply career gate filter. Hard exit for roles that don't fit Elena's profile."""
    try:
        from src.autonomous.job_gate import JobGate

        # JobGate.passes() is a @staticmethod that expects a dict with .get() calls
        job_dict = {
            'title':        state.get('title', ''),
            'description':  state.get('description', ''),
            'company':      state.get('company', ''),
            'location':     state.get('location', ''),
            'salary_min':   state.get('salary_min'),
            'salary_max':   state.get('salary_max'),
            'company_size': state.get('company_size', ''),
            'company_info': state.get('company_info', ''),
        }

        passed = JobGate.passes(job_dict)
        reason = "passed all filters" if passed else "filtered by career gate"

        if passed:
            logger.info(f"[gate] PASS  {state['company']} — {state['title']}")
            return {
                "gate_passed": True,
                "gate_reason": reason,
                "status": "gate_passed",
            }
        else:
            logger.info(f"[gate] FAIL  {state['company']} — {state['title']}")
            return {
                "gate_passed": False,
                "gate_reason": reason,
                "status": "gated_out",
            }

    except Exception as e:
        logger.error(f"[gate] ERROR {state['company']}: {e}")
        return {
            "gate_passed": False,
            "gate_reason": f"gate error: {e}",
            "status": "error",
            "error": str(e),
        }


def should_continue_after_gate(state: JobState) -> str:
    """Conditional edge after gate_node."""
    if state.get("gate_passed"):
        return "score_node"
    return "discard_node"


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: score_node
# Runs JobMatcher + source boosts. Sets score and score_reasons.
# ─────────────────────────────────────────────────────────────────────────────
def score_node(state: JobState) -> dict:
    """Score job against Elena's profile using JobMatcher v3.0 with bias compensation."""
    try:
        from src.agents.job_matcher import JobMatcher
        from src.core.profile_manager import ProfileManager

        profile = ProfileManager.load_default()
        matcher = JobMatcher()

        job_mock = type('Job', (), {
            'title': state['title'],
            'description': state['description'],
            'company': state['company'],
            'url': state['url'],
            'id': state['job_id'],
            'source': state.get('source', ''),
        })()

        score, reasons = matcher.calculate_match_score(profile, job_mock)

        # Apply source boost (YC +15, premium +5)
        boost = state.get('score_boost', 0)
        if boost:
            score = min(score + boost, 100)
            reasons.append(f"Source boost: +{boost}")

        # Priority company boost
        if state.get('is_priority'):
            score = min(score + 15, 100)
            reasons.append("Priority company: +15")

        logger.info(f"[score] {state['company']} | {state['title']} → {score:.0f}")

        return {
            "score": float(score),
            "score_reasons": reasons,
            "status": "scored",
        }

    except Exception as e:
        logger.error(f"[score] ERROR {state['company']}: {e}")
        return {
            "score": 0.0,
            "score_reasons": [f"scoring error: {e}"],
            "status": "error",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: route_node
# Sets the route field based on score. The actual branching is the conditional edge.
# ─────────────────────────────────────────────────────────────────────────────
def route_node(state: JobState) -> dict:
    """Decide routing based on score. Sets state['route'] for the conditional edge."""
    score = state.get('score', 0)

    if score >= SUBMIT_THRESHOLD:
        route = "submit"
    elif score >= HUMAN_THRESHOLD:
        route = "human_review"   # Will interrupt_before submit for human approval
    elif score >= OUTREACH_THRESHOLD:
        route = "outreach"
    else:
        route = "discard"

    logger.info(f"[route] {state['company']} score={score:.0f} → {route}")
    return {"route": route}


def route_after_score(state: JobState) -> str:
    """Conditional edge after route_node. Returns the next node name."""
    return {
        "submit":       "submit_node",
        "human_review": "submit_node",  # interrupt_before="submit_node" handles the pause
        "outreach":     "outreach_node",
        "discard":      "discard_node",
    }.get(state.get("route", "discard"), "discard_node")


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4: submit_node
# Calls AutoApplicator. Captures real delivery status + confirmation ID.
# For human_review jobs, this node is reached only after human approval
# (because interrupt_before=["submit_node"] pauses and waits).
# ─────────────────────────────────────────────────────────────────────────────
async def submit_node(state: JobState) -> dict:
    """
    Submit application via ATS or email.
    For human_review jobs: only reached after human sends /approve command.
    If human_approved == False: skip immediately.
    """
    # Human review jobs that were rejected
    if state.get('route') == 'human_review' and state.get('human_approved') is False:
        logger.info(f"[submit] REJECTED by human: {state['company']}")
        return {
            "applied": False,
            "apply_method": "skipped",
            "apply_error": "rejected by human reviewer",
            "status": "discarded",
        }

    try:
        from src.autonomous.auto_applicator import AutoApplicator
        from src.autonomous.email_service import create_email_service
        from src.core.profile_manager import ProfileManager

        profile = ProfileManager.load_default()
        email_service = create_email_service()
        applicator = AutoApplicator(
            profile=profile,
            db_helper=None,
            email_service=email_service,
            telegram=None,
        )

        # Build job object for the applicator
        job_mock = type('Job', (), state['raw_job'])()
        job_mock.match_score = state['score']
        job_mock.match_reasons = state['score_reasons']

        result = await applicator.apply_to_job(job_mock)

        # Capture real result — not just "generated"
        applied = result.get('success', False)
        method = result.get('method', 'unknown')
        confirmation = result.get('confirmation_id')
        error = result.get('error') if not applied else None

        logger.info(
            f"[submit] {state['company']} | applied={applied} "
            f"method={method} confirmation={confirmation}"
        )

        return {
            "applied": applied,
            "apply_method": method,
            "apply_error": error,
            "confirmation_id": confirmation,
            "status": "applied" if applied else "apply_failed",
        }

    except Exception as e:
        logger.error(f"[submit] ERROR {state['company']}: {e}")
        return {
            "applied": False,
            "apply_method": "error",
            "apply_error": str(e),
            "status": "error",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5: outreach_node
# Founder finder + email outreach for score 55-69.
# Rate-limit aware — checks daily outreach cap before sending.
# ─────────────────────────────────────────────────────────────────────────────
async def outreach_node(state: JobState) -> dict:
    """Send founder outreach email. Respects daily cap (MAX_DAILY_OUTREACH=2)."""
    try:
        from src.autonomous.founder_finder_v2 import FounderFinderV2
        from src.autonomous.message_generator import MessageGenerator
        from src.autonomous.email_service import create_email_service, validate_email_for_resend
        from src.core.profile_manager import ProfileManager
        import json
        from pathlib import Path

        # Check daily outreach cap
        cap_file = Path("autonomous_data/outreach_today.json")
        today = datetime.now(timezone.utc).date().isoformat()
        cap_data = {}
        if cap_file.exists():
            try:
                cap_data = json.loads(cap_file.read_text())
            except Exception:
                cap_data = {}

        if cap_data.get("date") == today and cap_data.get("count", 0) >= 2:
            logger.info(f"[outreach] Daily cap reached — skipping {state['company']}")
            return {
                "outreach_sent": False,
                "outreach_error": "daily cap reached",
                "status": "outreach_capped",
            }

        profile = ProfileManager.load_default()
        job_mock = type('Job', (), state['raw_job'])()

        # Find founder email
        finder = FounderFinderV2()
        founder_info = await finder.find_founder(state['company'], state['url'])

        if not founder_info or not founder_info.get('email'):
            logger.info(f"[outreach] No founder found for {state['company']}")
            return {
                "outreach_sent": False,
                "outreach_error": "no founder email found",
                "status": "outreach_no_contact",
            }

        founder_email = founder_info['email']
        if not validate_email_for_resend(founder_email):
            return {
                "outreach_sent": False,
                "outreach_error": f"invalid email: {founder_email}",
                "status": "outreach_invalid_email",
            }

        # Generate message
        gen = MessageGenerator(profile)
        message = await gen.generate_outreach_message(
            profile=profile,
            job=job_mock,
            company_info=founder_info,
        )

        # Send
        email_service = create_email_service()
        sent = await email_service.send_outreach(
            to_email=founder_email,
            subject=message['subject'],
            body=message['body'],
        )

        if sent:
            # Update daily cap
            new_count = cap_data.get("count", 0) + 1 if cap_data.get("date") == today else 1
            cap_file.write_text(json.dumps({"date": today, "count": new_count}))
            logger.info(f"[outreach] SENT to {founder_email} ({state['company']})")
            return {
                "outreach_sent": True,
                "outreach_email": founder_email,
                "status": "outreach_sent",
            }
        else:
            return {
                "outreach_sent": False,
                "outreach_error": "send failed",
                "status": "outreach_failed",
            }

    except Exception as e:
        logger.error(f"[outreach] ERROR {state['company']}: {e}")
        return {
            "outreach_sent": False,
            "outreach_error": str(e),
            "status": "error",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6: discard_node
# Logs the discard with reason. Terminal node for gated-out and low-score jobs.
# ─────────────────────────────────────────────────────────────────────────────
def discard_node(state: JobState) -> dict:
    """Log discard. Nothing is sent. Status recorded in checkpoint for deduplication."""
    reason = state.get('gate_reason') or f"score too low ({state.get('score', 0):.0f})"
    logger.info(f"[discard] {state['company']} | {state['title']} | {reason}")
    return {
        "status": "discarded",
        "route": state.get("route", "discard"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7: notify_node
# Sends a Telegram message for the job result. Terminal for all active routes.
# ─────────────────────────────────────────────────────────────────────────────
async def notify_node(state: JobState) -> dict:
    """Send Telegram notification for this job's outcome."""
    try:
        from src.notifications import TelegramNotifier
        telegram = TelegramNotifier()

        status = state.get('status', 'unknown')
        company = state.get('company', '?')
        title = state.get('title', '?')
        score = state.get('score', 0)
        url = state.get('url', '')

        if status == "applied":
            method = state.get('apply_method', '')
            conf = state.get('confirmation_id', 'none')
            msg = (
                f"<b>Applied</b>: {company}\n"
                f"Role: {title}\n"
                f"Score: {score:.0f} | Method: {method}\n"
                f"Confirmation: {conf}\n"
                f"<a href='{url}'>View posting</a>"
            )
        elif status in ("outreach_sent",):
            email = state.get('outreach_email', '')
            msg = (
                f"<b>Outreach sent</b>: {company}\n"
                f"Role: {title} | Score: {score:.0f}\n"
                f"Sent to: {email}"
            )
        elif status == "human_pending":
            msg = (
                f"<b>Human review needed</b>: {company}\n"
                f"Role: {title} | Score: {score:.0f}\n"
                f"Reply /approve_vjh_{state['job_id']} or /reject_vjh_{state['job_id']}\n"
                f"<a href='{url}'>View posting</a>"
            )
        elif status in ("apply_failed", "error"):
            err = state.get('apply_error') or state.get('error', '')
            msg = (
                f"<b>Apply FAILED</b>: {company}\n"
                f"Role: {title} | Score: {score:.0f}\n"
                f"Error: {err[:150]}"
            )
        else:
            # discarded / gated_out — don't spam Telegram for these
            return {"telegram_sent": False, "status": state.get("status", "completed")}

        await telegram.send_message(msg)
        return {"telegram_sent": True, "status": "completed"}

    except Exception as e:
        logger.warning(f"[notify] Telegram send failed for {state.get('company')}: {e}")
        return {"telegram_sent": False, "status": "completed"}
