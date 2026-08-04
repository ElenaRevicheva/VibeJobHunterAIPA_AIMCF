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
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
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
    # human_pending IS terminal in LEAD mode (added 2026-07-29): submit_node has
    # already surfaced the job to Telegram + HubSpot, so re-running the thread
    # can only produce a duplicate ping. resume() does not consult this set, so
    # /approve_vjh_<id> and /reject_vjh_<id> still work.
    "human_pending",
}

# How long before we re-try a failed job (days)
RETRY_FAILED_AFTER_DAYS = 3

# ─────────────────────────────────────────────────────────────────────────────
# CONTENT-FINGERPRINT DEDUP (added 2026-07-29)
#
# thread_id dedup is keyed on the SOURCE's job id, so a board that re-posts a
# listing under a new id defeats it completely. Real case:
# "Appspring — Senior Python Developer" arrived as torre_7628333 (Jun 23,
# Jul 8) and then torre_8156916 (Jul 28) — three separate HubSpot deals and
# Telegram pings for ONE listing. The fingerprint is normalised company+title,
# so it survives new ids, changed URLs, and cross-source duplicates.
#
# Marked ONLY when a job actually surfaces to Elena. A job dropped by the judge
# or by an AI outage is deliberately left unmarked so a later, better-informed
# cycle can still pick it up.
# ─────────────────────────────────────────────────────────────────────────────
FINGERPRINT_DB_PATH = "autonomous_data/surfaced_fingerprints.json"
# Same company+title will not be surfaced again within this window.
FP_TTL_DAYS = int(os.getenv("VJH_FP_TTL_DAYS", "60"))
FP_MAX_ENTRIES = 3000

# Max jobs to SURFACE (Telegram "Apply yourself" + HubSpot) per cycle — prevents a
# message-by-message flood when the backlog is large (e.g. after a dedup reset). Excess
# right-fit jobs simply surface on later cycles. Override with VJH_SURFACE_CAP.
import os as _os_cap
_SURFACE_CAP = int(_os_cap.getenv("VJH_SURFACE_CAP", "6"))

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

    # ------------------------------------------------------------------
    # Content-fingerprint dedup (survives job-id churn across re-posts)
    # ------------------------------------------------------------------

    @staticmethod
    def _fingerprint(company: str, title: str) -> str:
        """Stable id for a LISTING (not a posting): normalised company + title."""
        def norm(s: str) -> str:
            return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
        return hashlib.md5(f"{norm(company)}|{norm(title)}".encode("utf-8")).hexdigest()[:16]

    def _load_fingerprints(self) -> dict:
        path = Path(FINGERPRINT_DB_PATH)
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text())
            db = raw.get("surfaced_v1", {})
            return db if isinstance(db, dict) else {}
        except Exception as e:
            logger.warning(f"[runner] Fingerprint DB unreadable ({e}) — treating as empty")
            return {}

    def _save_fingerprints(self, db: dict) -> None:
        try:
            if len(db) > FP_MAX_ENTRIES:
                newest = sorted(db, key=lambda k: db[k].get("last_surfaced", ""), reverse=True)
                db = {k: db[k] for k in newest[:FP_MAX_ENTRIES]}
            path = Path(FINGERPRINT_DB_PATH)
            path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({"surfaced_v1": db}))
        except Exception as e:
            logger.warning(f"[runner] Could not persist fingerprint DB: {e}")

    def _fp_recently_surfaced(self, db: dict, fp: str) -> Optional[str]:
        """Return the ISO timestamp of the last surface inside the TTL, else None."""
        rec = db.get(fp)
        if not rec:
            return None
        last = rec.get("last_surfaced") or rec.get("first_surfaced", "")
        try:
            when = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
        except Exception:
            return None  # unparseable → let it through rather than suppress forever
        if datetime.now(timezone.utc) - when < timedelta(days=FP_TTL_DAYS):
            return last
        return None

    def _mark_surfaced(self, db: dict, fp: str, company: str, title: str, job_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        rec = db.get(fp) or {"first_surfaced": now, "company": company, "title": title, "job_ids": []}
        rec["last_surfaced"] = now
        rec["count"] = int(rec.get("count", 0)) + 1
        ids = rec.get("job_ids") or []
        if job_id not in ids:
            ids.append(job_id)
        rec["job_ids"] = ids[-10:]
        db[fp] = rec
        self._save_fingerprints(db)

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

        # Stable job identifier. Some sources omit 'id'/'job_id' entirely, which
        # previously left job_id="" → "[runner] Job missing ID, skipping" → EVERY
        # accepted job dropped as an error (PATH A pushed 0 deals since May 21 2026).
        # Fall back to a deterministic content hash so the job is processable AND
        # dedup-stable across cycles.
        _jid = str(job_dict.get('id') or job_dict.get('job_id') or '').strip()
        if not _jid:
            _key = '|'.join([
                str(job_dict.get('company', '')),
                str(job_dict.get('title', '')),
                str(job_dict.get('url', '') or job_dict.get('location', '')),
            ]).lower()
            _jid = 'h' + hashlib.md5(_key.encode('utf-8')).hexdigest()[:16]

        return {
            # Input
            "job_id":       _jid,
            "company":      str(job_dict.get('company', '')),
            "title":        str(job_dict.get('title', '')),
            "url":          str(job_dict.get('url', '')),
            "description":  str(job_dict.get('description', '') or '')[:4000],
            "location":     str(job_dict.get('location', '')),   # WAS MISSING → iron_clad saw empty region → discarded every job
            "source":       str(job_dict.get('source', '')),
            "is_yc":        bool(job_dict.get('is_yc_company', False)),
            "is_priority":  bool(job_dict.get('priority_flag', False)),
            "score_boost":  int(job_dict.get('score_boost', 0) or 0),
            "raw_job":      {
                # Keep dicts/lists as-is so process_job can call .get() on founder_info etc.
                # Only stringify primitives (avoids 'str' object has no attribute 'get' crash).
                k: (v if isinstance(v, (dict, list, bool, int, float)) else str(v)[:500])
                for k, v in job_dict.items()
                if v is not None and k != 'description'
            },

            # Gate / score (will be filled by nodes)
            "gate_passed":  False,
            "gate_reason":  "",
            "unverified":   False,
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
            "skipped_fingerprint": 0,
            "applied": 0,
            "apply_failed": 0,
            "outreach_sent": 0,
            "human_pending": 0,
            "discarded": 0,
            "gated_out": 0,
            "errors": 0,
        }

        fp_db = self._load_fingerprints()

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

                    # ── DEDUPLICATION CHECK 1: same posting id ───────────────
                    if await self._is_already_processed(checkpointer, thread_id):
                        summary["skipped_dedup"] += 1
                        continue

                    # ── DEDUPLICATION CHECK 2: same listing, new posting id ──
                    fp = self._fingerprint(initial["company"], initial["title"])
                    prior = self._fp_recently_surfaced(fp_db, fp)
                    if prior:
                        logger.info(
                            f"[runner] Skipping {initial['company']} | {initial['title']} — "
                            f"already surfaced {prior[:10]} (fingerprint dedup; "
                            f"new posting id {job_id})"
                        )
                        summary["skipped_fingerprint"] += 1
                        continue

                    # ── RUN GRAPH ────────────────────────────────────────────
                    logger.info(f"[runner] Processing: {initial['company']} | {initial['title']}")
                    final_state = await graph.ainvoke(initial, config=config)

                    status = final_state.get("status", "unknown")
                    route = final_state.get("route", "")

                    # If interrupted before submit_node (auto-apply mode only), send the
                    # approval ask. In LEAD mode there's NO interrupt — submit_node already
                    # surfaced via notify_node (status=human_pending) — so skip the extra ask.
                    if route == "human_review" and status not in TERMINAL_STATUSES and status != "human_pending":
                        if summary["human_pending"] >= _SURFACE_CAP:
                            summary["discarded"] += 1  # per-cycle surface cap reached — defer to a later cycle (no flood)
                            continue
                        # LLM JUDGE precision veto on the human-review surface path (the path jobs
                        # actually take in LEAD mode) — so wrong-fit jobs never reach Telegram/HubSpot.
                        try:
                            if final_state.get('unverified'):
                                # Same rule as the gate and submit_node: don't ask an
                                # LLM to rule on text we already know is incomplete.
                                _jf, _jr = True, "unverified — judge skipped, surfaced for human review"
                            else:
                                from src.core.llm_judge import judge_fit
                                _jf, _jr = judge_fit(final_state.get('title', ''), final_state.get('company', ''),
                                                     final_state.get('location', ''), final_state.get('description', ''))
                        except Exception as _je:
                            _jf, _jr = True, f"judge import failed ({_je})"
                        if not _jf:
                            logger.info(f"[runner] judge VETO ({_jr}) → discard: {final_state.get('company')} | {final_state.get('title')}")
                            summary["discarded"] += 1
                            continue
                        logger.info(f"[runner] judge OK ({_jr}) → surface: {final_state.get('company')} | {final_state.get('title')}")
                        await self._send_human_review_request(final_state, config, checkpointer)
                        self._mark_surfaced(fp_db, fp, initial["company"], initial["title"], job_id)
                        summary["human_pending"] += 1
                        continue

                    # Anything that reached Elena (Telegram ping / HubSpot deal / ATS
                    # submission) gets fingerprinted so a re-post under a new id can't
                    # duplicate it. Discards and gate-outs stay unmarked on purpose.
                    if status in ("applied", "human_pending", "outreach_sent"):
                        self._mark_surfaced(fp_db, fp, initial["company"], initial["title"], job_id)

                    # Tally
                    if status == "applied":
                        summary["applied"] += 1
                    elif status == "apply_failed":
                        summary["apply_failed"] += 1
                    elif status in ("outreach_sent",):
                        summary["outreach_sent"] += 1
                    elif status == "human_pending":          # LEAD-mode surface ("Apply yourself")
                        summary["human_pending"] += 1
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
