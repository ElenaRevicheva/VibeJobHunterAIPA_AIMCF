"""
VJH LangGraph State Definition
Each job gets its own TypedDict state — processed through the graph as an independent thread.
thread_id = f"vjh_{job_id}" — this is what makes deduplication work across runs.
"""

from typing import TypedDict, Optional, List


class JobState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    job_id: str
    company: str
    title: str
    url: str
    description: str
    source: str           # e.g. "greenhouse", "lever", "ashby", "yc"
    is_yc: bool
    is_priority: bool
    score_boost: int      # Pre-score boost from source (YC=+15, premium=+5)
    raw_job: dict         # Full job dict for passing to existing logic

    # ── Gate result ──────────────────────────────────────────────────────────
    gate_passed: bool
    gate_reason: str      # Why it passed or failed

    # ── Score result ─────────────────────────────────────────────────────────
    score: float          # Final score after boosts
    score_reasons: List[str]

    # ── Routing ──────────────────────────────────────────────────────────────
    # "submit" | "outreach" | "human_review" | "discard"
    route: str

    # ── Human review ─────────────────────────────────────────────────────────
    # When route == "human_review", the graph interrupts before submit_node.
    # The Telegram bot sets human_approved=True/False to resume the thread.
    human_approved: Optional[bool]
    human_review_message_id: Optional[str]  # Telegram message ID for tracking

    # ── Application result ────────────────────────────────────────────────────
    applied: bool
    apply_method: str        # "ats_form" | "email" | "skipped" | "dry_run"
    apply_error: Optional[str]
    confirmation_id: Optional[str]   # Employer-issued ID if received

    # ── Outreach result ────────────────────────────────────────────────────────
    outreach_sent: bool
    outreach_email: Optional[str]
    outreach_error: Optional[str]

    # ── Notification ──────────────────────────────────────────────────────────
    telegram_sent: bool

    # ── Pipeline status ───────────────────────────────────────────────────────
    # "pending" → "gated_out" | "scored" → "applied" | "outreach_sent" |
    # "human_pending" | "discarded" | "completed" | "error"
    status: str
    error: Optional[str]
    cycle_id: str       # Which hourly cycle this job was found in
    timestamp: str      # ISO timestamp of first discovery
