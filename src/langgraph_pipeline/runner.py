"""
VJH LangGraph Runner
Replaces the raw for-loop in orchestrator.run_autonomous_cycle() for job processing.

What this solves vs the old orchestrator:
  PROBLEM                              SOLUTION
  Deel applied 7 times                 SQLite checkpoint: thread_id=vjh_{job_id};
                                       skip if status already in terminal states
  87% silent failures                  submit_node captures HTTP response + confirmation_id;
                                       apply_failed status recorded in checkpoint + Telegram
  No rate-limit awareness              outreach_node checks daily cap file before sending;
                                       Resend failures recorded as apply_failed (not silently dropped)
  No stage visibility                  Every node write is checkpointed; query DB to see where each job is
  Human approval impossible            interrupt_before=["submit_node"]; resume() call from Telegram bot

Usage (in orchestrator or standalone):
    from src.langgraph_pipeline.runner import VJHLangGraphRunner
    runner = VJHLangGraphRunner()
    await runner.process_jobs(jobs, cycle_id="2026-04-26-12h")

Human approval (from Telegram bot command handler):
    await runner.resume(job_id="deel_123", approved=True)
    await runner.resume(job_id="deel_123", approved=False)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .state import JobState
from .pipeline import build_graph

logger = logging.getLogger(__name__)

# Terminal statuses — job will not be reprocessed if it has one of these
TERMINAL_STATUSES = {
    "applied", "apply_failed", "discarded", "gated_out",
    "outreach_sent", "outreach_capped", "outreach_no_contact",
    "outreach_invalid_email", "outreach_failed", "completed",
}

# How long before we re-try a failed job (days)
RETRY_FAILED_AFTER_DAYS = 3

CHECKPOINT_DB_PATH = "autonomous_data/vjh_checkpoint.db"


class VJHLangGraphRunner:
    """
    Batch processor that runs the LangGraph pipeline for a list of jobs.
    Uses AsyncSqliteSaver for per-job checkpoint persistence.
    """

    def __init__(self):
        Path("autonomous_data").mkdir(exist_ok=True)

    def _thread_id(self, job_id: str) -> str:
        return f"vjh_{job_id}"

    def _initial_state(self, job: any, cycle_id: str) -> JobState:
        """Convert a JobPosting (or dict) to initial JobState."""
        # Support both model objects and dicts
        if hasattr(job, 'to_dict'):
            job_dict = job.to_dict()
        elif hasattr(job, 'model_dump'):
            job_dict = job.model_dump()
        elif isinstance(job, dict):
            job_dict = job
        else:
            job_dict = job.__dict__

        return {
            # Input
            "job_id":       str(job_dict.get('id') or job_dict.get('job_id', '')),
            "company":      str(job_dict.get('company', '')),
            "title":        str(job_dict.get('title', '')),
            "url":          str(job_dict.get('url', '')),
            "description":  str(job_dict.get('description', '') or '')[:4000],
            "source":       str(job_dict.get('source', '')),
            "is_yc":        bool(job_dict.get('is_yc_company', False)),
            "is_priority":  bool(job_dict.get('priority_flag', False)),
            "score_boost":  int(job_dict.get('score_boost', 0) or 0),
            "raw_job":      {k: str(v)[:500] for k, v in job_dict.items()
                             if v is not None and k != 'description'},

            # Gate / score (will be filled by nodes)
            "gate_passed":  False,
            "gate_reason":  "",
            "score":        0.0,
            "score_reasons": [],

            # Routing
            "route":        "",

            # Human review
            "human_approved":          None,
            "human_review_message_id": None,

            # Application
            "applied":          False,
            "apply_method":     "",
            "apply_error":      None,
            "confirmation_id":  None,

            # Outreach
            "outreach_sent":  False,
            "outreach_email": None,
            "outreach_error": None,

            # Notification
            "telegram_sent": False,

            # Meta
            "status":    "pending",
            "error":     None,
            "cycle_id":  cycle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _is_already_processed(self, checkpointer: AsyncSqliteSaver, thread_id: str) -> bool:
        """
        Check SQLite checkpoint for this thread_id.
        Returns True if the job is in a terminal state and should be skipped.
        This is the deduplication fix for Deel ×7.
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = await checkpointer.aget(config)
            if checkpoint is None:
                return False  # Never seen before

            # Get the last known state values
            channel_values = checkpoint.get("channel_values", {})
            status = channel_values.get("status", "")

            if status in TERMINAL_STATUSES:
                logger.debug(f"[runner] Skipping {thread_id} — already {status}")
                return True

            # Check if it's a stale error we should retry
            if status == "error":
                ts_str = channel_values.get("timestamp", "")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        age_days = (datetime.now(timezone.utc) - ts).days
                        if age_days >= RETRY_FAILED_AFTER_DAYS:
                            logger.info(f"[runner] Retrying {thread_id} — error {age_days}d ago")
                            return False
                    except Exception:
                        pass
                return True  # Recent error, skip

            return False  # Incomplete — run it

        except Exception as e:
            logger.warning(f"[runner] Checkpoint check failed for {thread_id}: {e}")
            return False  # If we can't check, run it (safe default)

    async def process_jobs(self, jobs: List, cycle_id: str) -> dict:
        """
        Run the LangGraph pipeline for each job in the list.
        Skips jobs whose thread is already in a terminal state (deduplication).

        Returns summary dict: counts of applied / outreach / discarded / skipped / errors.
        """
        summary = {
            "total": len(jobs),
            "skipped_dedup": 0,
            "applied": 0,
            "apply_failed": 0,
            "outreach_sent": 0,
            "human_pending": 0,
            "discarded": 0,
            "gated_out": 0,
            "errors": 0,
        }

        async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as checkpointer:
            graph = build_graph(checkpointer)

            for job in jobs:
                try:
                    initial = self._initial_state(job, cycle_id)
                    job_id = initial["job_id"]
                    if not job_id:
                        logger.warning(f"[runner] Job missing ID, skipping: {initial.get('company')}")
                        summary["errors"] += 1
                        continue

                    thread_id = self._thread_id(job_id)
                    config = {"configurable": {"thread_id": thread_id}}

                    # ── DEDUPLICATION CHECK ──────────────────────────────────
                    if await self._is_already_processed(checkpointer, thread_id):
                        summary["skipped_dedup"] += 1
                        continue

                    # ── RUN GRAPH ────────────────────────────────────────────
                    logger.info(f"[runner] Processing: {initial['company']} | {initial['title']}")
                    final_state = await graph.ainvoke(initial, config=config)

                    status = final_state.get("status", "unknown")
                    route = final_state.get("route", "")

                    # If interrupted (human_review), send Telegram ask
                    if route == "human_review" and status not in TERMINAL_STATUSES:
                        await self._send_human_review_request(final_state, config, checkpointer)
                        summary["human_pending"] += 1
                        continue

                    # Tally
                    if status == "applied":
                        summary["applied"] += 1
                    elif status == "apply_failed":
                        summary["apply_failed"] += 1
                    elif status in ("outreach_sent",):
                        summary["outreach_sent"] += 1
                    elif status == "gated_out":
                        summary["gated_out"] += 1
                    elif status == "discarded":
                        summary["discarded"] += 1
                    elif status == "error":
                        summary["errors"] += 1

                except Exception as e:
                    logger.error(f"[runner] Unhandled error for {getattr(job, 'company', '?')}: {e}")
                    summary["errors"] += 1

        return summary

    async def _send_human_review_request(
        self, state: dict, config: dict, checkpointer: AsyncSqliteSaver
    ):
        """
        Send Telegram message asking Elena to approve/reject a human_review job.
        The graph is paused at submit_node; resume() will continue it.
        """
        try:
            from src.notifications import TelegramNotifier
            telegram = TelegramNotifier()

            job_id = state.get("job_id", "?")
            company = state.get("company", "?")
            title = state.get("title", "?")
            score = state.get("score", 0)
            url = state.get("url", "")
            reasons = state.get("score_reasons", [])
            top_reasons = "; ".join(reasons[:3]) if reasons else "N/A"

            msg = (
                f"<b>Apply? Score {score:.0f}/100</b>\n\n"
                f"<b>{company}</b>\n"
                f"{title}\n\n"
                f"Why: {top_reasons}\n\n"
                f"<a href='{url}'>View job</a>\n\n"
                f"/approve_vjh_{job_id}\n"
                f"/reject_vjh_{job_id}"
            )
            await telegram.send_message(msg)
            logger.info(f"[runner] Human review requested for {company} (job_id={job_id})")

        except Exception as e:
            logger.error(f"[runner] Failed to send human review request: {e}")

    async def resume(self, job_id: str, approved: bool):
        """
        Resume a paused human_review job after Elena approves or rejects.
        Called by the Telegram bot command handler for /approve_vjh_{job_id} or /reject_vjh_{job_id}.

        Example in telegram_bot.py:
            if text.startswith("/approve_vjh_"):
                jid = text.split("_vjh_")[1]
                await runner.resume(jid, approved=True)
            elif text.startswith("/reject_vjh_"):
                jid = text.split("_vjh_")[1]
                await runner.resume(jid, approved=False)
        """
        thread_id = self._thread_id(job_id)
        config = {"configurable": {"thread_id": thread_id}}

        async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as checkpointer:
            graph = build_graph(checkpointer)

            # Update state with human decision before resuming
            update = {"human_approved": approved}
            await graph.aupdate_state(config, update)

            # Resume from interrupt (None input = continue from where it paused)
            final_state = await graph.ainvoke(None, config=config)

            status = final_state.get("status", "unknown")
            company = final_state.get("company", "?")
            logger.info(
                f"[runner] Resumed {company} (job_id={job_id}) "
                f"approved={approved} → status={status}"
            )
            return final_state

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Query the checkpoint for a specific job's current state.
        Useful for /status commands in the Telegram bot.
        """
        thread_id = self._thread_id(job_id)
        config = {"configurable": {"thread_id": thread_id}}

        async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH) as checkpointer:
            checkpoint = await checkpointer.aget(config)
            if not checkpoint:
                return None
            return checkpoint.get("channel_values", {})

    async def get_pipeline_summary(self) -> str:
        """
        Return a text summary of all jobs in the checkpoint DB.
        Powers the /pipeline_status Telegram command.
        """
        try:
            import sqlite3
            db_path = CHECKPOINT_DB_PATH
            if not Path(db_path).exists():
                return "No pipeline data yet."

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Count by status across all threads
            cursor.execute(
                "SELECT thread_id, checkpoint FROM checkpoints ORDER BY thread_id"
            )
            rows = cursor.fetchall()
            conn.close()

            status_counts: dict = {}
            for thread_id, checkpoint_blob in rows:
                if not thread_id.startswith("vjh_"):
                    continue
                try:
                    data = json.loads(checkpoint_blob)
                    status = data.get("channel_values", {}).get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                except Exception:
                    pass

            if not status_counts:
                return "Pipeline DB is empty — no jobs processed yet."

            total = sum(status_counts.values())
            lines = [f"<b>Pipeline status ({total} jobs tracked)</b>"]
            for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  {status}: {count}")
            return "\n".join(lines)

        except Exception as e:
            return f"Pipeline status unavailable: {e}"
