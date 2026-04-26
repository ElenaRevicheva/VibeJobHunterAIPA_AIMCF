"""
🤖 AUTONOMOUS ORCHESTRATOR - Production v3.0
The brain of the autonomous job hunting engine.
Coordinates all agents and runs the complete workflow 24/7.

CHANGES (2024-12-18):
✅ Evidence-based threshold tuning (60/58/55)
✅ Multi-channel routing (ATS + Outreach + Review)
✅ Integrated bias compensation from JobMatcher v3.0
✅ Enhanced logging for transparency
✅ Founder finder integrated into routing flow
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from zoneinfo import ZoneInfo

# LinkedIn CMO: one post per **Panama calendar day** at **20:00 local** (America/Panama = UTC−5, no DST).
PANAMA_TZ = ZoneInfo("America/Panama")
LINKEDIN_POST_PANAMA_HOUR = 20

from ..core.models import Profile, JobPosting
from ..utils.logger import setup_logger

from .job_monitor import JobMonitor, SEEN_TTL_DAYS
from .company_researcher import CompanyResearcher
from .founder_finder_v2 import FounderFinderV2  # UPGRADED: Real email discovery
from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler
from .follow_up_engine import FollowUpEngine
from .warm_intro_queue import WarmIntroQueue, seed_contacts_if_empty

logger = setup_logger(__name__)

# Module version
ORCHESTRATOR_VERSION = "4.3_AUTONOMOUS_CYCLE_v3.0"
logger.info(f"📦 Orchestrator v{ORCHESTRATOR_VERSION} loaded")

# ════════════════════════════════════════════════════════════
# EVIDENCE-BASED THRESHOLDS (2024-12-18 tuning)
# Rationale: Top real matches scored 62-64, threshold 65 = 0% hit rate
# ════════════════════════════════════════════════════════════
AUTO_APPLY_THRESHOLD = 60   # Unblocks Webflow (73), GitLab (67) after bias compensation
OUTREACH_THRESHOLD = 58     # Founder finder for near-matches
REVIEW_THRESHOLD = 55       # Human review queue for edge cases
MAX_DAILY_OUTREACH = 2      # Cap founder/CEO outreach at 1-2 per day (quality over spam)


class CycleStats:
    """Track actions per autonomous cycle"""
    def __init__(self):
        self.jobs_found = 0
        self.jobs_scored = 0
        self.auto_applied = 0
        self.outreach_sent = 0
        self.review_queued = 0
        self.discarded = 0
        self.errors = 0
        self.top_matches = []
        # Priority companies visibility (additive — Feb 2026)
        self.priority_matches_found = 0
        self.priority_outreach_sent = 0
        self.priority_applied = 0


class AutonomousOrchestrator:
    """
    🚀 THE BRAIN: Coordinates all autonomous agents
    """

    def __init__(self, profile: Profile, telegram_enabled: bool = True):
        if profile is None:
            raise RuntimeError("❌ PROFILE IS REQUIRED — REFUSING SILENT STARTUP")

        self.profile = profile
        self.is_running = False
        self.last_linkedin_post_date = self._load_last_linkedin_post_date()
        self._outreach_today = 0
        self._outreach_today_date = None

        logger.info("=" * 60)
        logger.info("🚀 VIBEJOBHUNTER ORCHESTRATOR INITIALIZING")
        logger.info("=" * 60)

        # ─────────────────────────────
        # Notifications
        # ─────────────────────────────
        from ..notifications import TelegramNotifier, LinkedInCMO

        self.telegram = TelegramNotifier() if telegram_enabled else None

        try:
            self.linkedin_cmo = LinkedInCMO(profile=self.profile)
            if self.linkedin_cmo.enabled:
                logger.info("=" * 50)
                logger.info("✅ LinkedIn CMO INITIALIZED & ENABLED")
                logger.info(f"   📅 Daily posts: {LINKEDIN_POST_PANAMA_HOUR}:00 America/Panama (UTC−5)")
                logger.info("   🔗 Webhook: configured ✓")
                logger.info("=" * 50)
            else:
                logger.warning("=" * 50)
                logger.warning("⚠️ LinkedIn CMO INITIALIZED but DISABLED!")
                logger.warning("   Missing: MAKE_WEBHOOK_URL_LINKEDIN env var")
                logger.warning("   Daily LinkedIn posts will NOT be sent")
                logger.warning("=" * 50)
        except Exception as e:
            logger.error(f"❌ LinkedIn CMO failed to initialize: {e}")
            self.linkedin_cmo = None

        # ─────────────────────────────
        # Database & Enhanced Bot
        # ─────────────────────────────
        try:
            from ..database.database_models import DatabaseHelper, init_database
            from ..notifications.telegram_bot_enhanced import create_enhanced_bot

            init_database()
            self.db_helper = DatabaseHelper()
            self.telegram_bot_enhanced = create_enhanced_bot(db_helper=self.db_helper)

            logger.info("✅ Database + Enhanced Telegram Bot ready")
        except Exception as e:
            logger.error(f"❌ Database / Enhanced bot failed: {e}", exc_info=True)
            self.db_helper = None
            self.telegram_bot_enhanced = None

        # ─────────────────────────────
        # Auto-Applicator
        # ─────────────────────────────
        try:
            from .auto_applicator import AutoApplicator
            from .email_service import create_email_service

            self.auto_applicator = AutoApplicator(
                profile=self.profile,
                db_helper=self.db_helper,
                email_service=create_email_service(),
                telegram=self.telegram
            )
            logger.info("✅ Auto-Applicator ENABLED")
        except Exception as e:
            logger.error(f"❌ Auto-Applicator failed: {e}", exc_info=True)
            self.auto_applicator = None

        # ─────────────────────────────
        # Core agents
        # ─────────────────────────────
        self.job_monitor = JobMonitor()
        self.company_researcher = CompanyResearcher()
        self.founder_finder = FounderFinderV2()  # UPGRADED: Hunter.io + real email discovery
        self.message_generator = MessageGenerator(self.profile)
        self.multi_channel_sender = MultiChannelSender()
        self.demo_tracker = DemoTracker()
        self.response_handler = ResponseHandler(self.profile)

        # ─────────────────────────────
        # Stats
        # ─────────────────────────────
        self.stats = {
            "jobs_found": 0,
            "companies_researched": 0,
            "messages_sent": 0,
            "demo_clicks": 0,
            "responses_received": 0,
            "interviews_scheduled": 0,
            "applications_generated": 0,
            "applications_sent": 0,
            "applications_today": 0,
            "founder_outreach": 0,
            "founders_found": 0,
        }

        self.data_dir = Path("autonomous_data")
        self.data_dir.mkdir(exist_ok=True)

        # Track consecutive zero-result cycles for alerting (added 2026-02-08)
        self._consecutive_zero_cycles = 0

        # ─────────────────────────────
        # Follow-Up Engine (added 2026-02-08)
        # ─────────────────────────────
        self.follow_up_engine = FollowUpEngine()

        # ─────────────────────────────
        # Warm Intro Queue (added 2026-02-09)
        # ─────────────────────────────
        try:
            self.warm_intro_queue = WarmIntroQueue()
            seed_contacts_if_empty(self.warm_intro_queue)
            logger.info("✅ Warm Intro Queue ready")
        except Exception as e:
            logger.error(f"❌ Warm Intro Queue failed: {e}")
            self.warm_intro_queue = None

        # ─────────────────────────────
        # Daily Summary tracking (added 2026-02-08)
        # ─────────────────────────────
        self._daily_stats = {
            "date": datetime.utcnow().date().isoformat(),
            "cycles_run": 0,
            "total_jobs_found": 0,
            "total_jobs_scored": 0,
            "total_auto_applied": 0,
            "total_outreach_sent": 0,
            "total_review_queued": 0,
            "total_discarded": 0,
            "total_errors": 0,
            "follow_ups_sent": 0,
            "top_companies": [],
        }
        self._last_daily_summary_date = None

        logger.info("🚀 Autonomous Orchestrator READY")

    # ─────────────────────────────
    # LINKEDIN CMO SCHEDULER — 20:00 America/Panama (UTC−5)
    # ─────────────────────────────
    async def check_linkedin_schedule(self):
        """
        One LinkedIn/Buffer post per **Panama local calendar day**, at 20:00 (8 PM) Panama City time.

        `linkedin_cmo_data/last_post_date.txt` stores an ISO **Panama** date so the window stays
        correct when 8 PM Panama is already the next calendar day in UTC.
        """
        # Check if LinkedIn CMO is available and enabled
        if not self.linkedin_cmo:
            logger.debug("📣 LinkedIn CMO: Not initialized (skipping)")
            return
        
        if not self.linkedin_cmo.enabled:
            now_pa = datetime.now(PANAMA_TZ)
            if now_pa.minute == 0:
                logger.warning("📣 LinkedIn CMO: DISABLED - check MAKE_WEBHOOK_URL_LINKEDIN env var")
            return

        now_pa = datetime.now(PANAMA_TZ)
        today_pa = now_pa.date()

        if self.last_linkedin_post_date == today_pa:
            return

        # First successful check during the 8 PM Panama hour (linkedin_loop checks every ~3 min).
        if now_pa.hour != LINKEDIN_POST_PANAMA_HOUR:
            return

        logger.info("=" * 50)
        logger.info("📣 LINKEDIN CMO: TRIGGERING DAILY POST")
        logger.info(f"   🕐 America/Panama: {now_pa.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("   🌍 Language: random → LinkedInCMO EN↔ES alternation file")
        logger.info("=" * 50)
        
        try:
            ok = await self.linkedin_cmo.post_to_linkedin(
                post_type="random",
                language="random",
            )
            if ok:
                self.last_linkedin_post_date = today_pa
                self._save_last_linkedin_post_date(today_pa)
                logger.info("📣 LinkedIn CMO: Post completed successfully ✅")
            else:
                logger.error(
                    "📣 LinkedIn CMO: Make.com/webhook did not confirm success — "
                    "last_post_date NOT updated; will retry while still in the 8 PM Panama window"
                )
        except Exception as e:
            logger.error(f"📣 LinkedIn CMO: Post FAILED - {e}", exc_info=True)

    # ─────────────────────────────
    # AUTONOMOUS MODE
    # ─────────────────────────────
    async def start_autonomous_mode(self, interval_hours: int = 1):
        self.is_running = True
        logger.info(f"🚀 AUTONOMOUS MODE STARTED (every {interval_hours}h)")

        # Send startup notification
        if self.telegram:
            await self.telegram.notify_startup_success()

        # Start ONLY ONE telegram polling instance to avoid conflicts
        # Priority: Enhanced bot (more features) > Basic notifier
        if self.telegram_bot_enhanced:
            logger.info("📱 Starting Enhanced Telegram Bot (with commands)")
            asyncio.create_task(self.telegram_bot_enhanced.start())
        elif self.telegram:
            logger.info("📱 Starting basic Telegram polling")
            asyncio.create_task(self.telegram.start_polling())

        async def linkedin_loop():
            while self.is_running:
                await self.check_linkedin_schedule()
                # 3 min cadence so a restart or a failed webhook rarely misses the full 8 PM Panama hour
                await asyncio.sleep(180)

        asyncio.create_task(linkedin_loop())

        # Daily summary at 20:00 UTC (3pm Panama)
        async def daily_summary_loop():
            while self.is_running:
                await self._check_daily_summary_schedule()
                await asyncio.sleep(600)  # Check every 10 minutes

        asyncio.create_task(daily_summary_loop())

        while self.is_running:
            try:
                await self.run_autonomous_cycle()
                await asyncio.sleep(interval_hours * 3600)
            except Exception as e:
                logger.error(f"❌ Autonomous loop error: {e}", exc_info=True)
                await asyncio.sleep(300)

    def stop(self):
        self.is_running = False
        logger.info("🛑 Autonomous mode stopped")

    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()

    # ─────────────────────────────
    # PERSIST LINKEDIN POST DATE (survives reboot)
    # ─────────────────────────────
    def _load_last_linkedin_post_date(self):
        """Load last LinkedIn post date from disk so we don't double-post after reboot."""
        marker = Path("linkedin_cmo_data/last_post_date.txt")
        try:
            if marker.exists():
                text = marker.read_text(encoding="utf-8").strip()
                if text:
                    from datetime import date
                    return date.fromisoformat(text)
        except Exception as e:
            logger.warning(f"⚠️ Could not load last LinkedIn post date: {e}")
        return None

    def _save_last_linkedin_post_date(self, post_date):
        """Persist last LinkedIn post date to disk."""
        marker = Path("linkedin_cmo_data/last_post_date.txt")
        try:
            marker.parent.mkdir(exist_ok=True)
            marker.write_text(post_date.isoformat(), encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️ Could not save last LinkedIn post date: {e}")

    # ─────────────────────────────
    # OUTREACH DAILY CAP (1-2/day)
    # ─────────────────────────────
    def _check_outreach_cap(self) -> bool:
        """Return True if we can still send outreach today."""
        today = datetime.utcnow().date()
        if self._outreach_today_date != today:
            self._outreach_today = 0
            self._outreach_today_date = today
        return self._outreach_today < MAX_DAILY_OUTREACH

    def _record_outreach_sent(self):
        """Increment daily outreach counter."""
        today = datetime.utcnow().date()
        if self._outreach_today_date != today:
            self._outreach_today = 0
            self._outreach_today_date = today
        self._outreach_today += 1

    # ─────────────────────────────
    # CORE AUTONOMOUS CYCLE - PRODUCTION v3.0
    # ─────────────────────────────
    async def run_autonomous_cycle(self):
        """
        🔥 THE MAIN JOB HUNTING CYCLE 🔥
        
        This runs every hour and:
        1. Fetches new jobs from ATS APIs
        2. Scores and filters them (with bias compensation)
        3. Routes to channels: AUTO_APPLY / OUTREACH / REVIEW
        4. Generates application materials
        5. Sends applications (if auto_apply enabled)
        6. Notifies via Telegram
        """
        logger.info("=" * 60)
        logger.info("🔄 AUTONOMOUS CYCLE STARTED")
        logger.info("=" * 60)
        
        cycle_stats = CycleStats()
        
        try:
            # ═════════════════════════════════════════════════════
            # STEP 0: Sync priority companies from YC export (additive, non-blocking)
            # Cron on Oracle runs job-list pipeline every 6h; we sync from the file each cycle.
            # ═════════════════════════════════════════════════════
            if self.db_helper:
                import os
                path = os.getenv("PRIORITY_YC_EXPORT_PATH")
                if not path:
                    base = os.getenv("OPENCLAW_JOB_LIST_PATH", ".")
                    path = os.path.join(base, "priority_companies_for_vibejob.json")
                if not os.path.isabs(path):
                    path = os.path.join(os.getcwd(), path)
                if not os.path.exists(path) and os.path.exists("/home/ubuntu/job-list-filter"):
                    path = "/home/ubuntu/job-list-filter/priority_companies_for_vibejob.json"
                if os.path.exists(path):
                    try:
                        added, skipped = self.db_helper.sync_priority_from_yc_file(path)
                        if added > 0 or skipped > 0:
                            logger.info(f"🎯 Priority sync: {added} added, {skipped} skipped (from YC export)")
                    except Exception as e:
                        logger.warning(f"⚠️ Priority sync skipped: {e}")
            
            # ═════════════════════════════════════════════════════
            # STEP 1: Find new jobs
            # ═════════════════════════════════════════════════════
            logger.info("🔍 Step 1: Finding new jobs...")
            
            new_jobs = await self.job_monitor.find_new_jobs(
                target_roles=self.profile.target_roles,
                max_results=50
            )
            
            cycle_stats.jobs_found = len(new_jobs)
            self.stats["jobs_found"] += len(new_jobs)
            logger.info(f"✅ Found {len(new_jobs)} new jobs")

            # Reset zero-cycle counter when we find jobs
            if new_jobs:
                self._consecutive_zero_cycles = 0
            
            if not new_jobs:
                self._consecutive_zero_cycles += 1
                logger.info(f"📭 No new jobs this cycle ({self._consecutive_zero_cycles} consecutive) - waiting for next run")

                # Alert via Telegram every 12 cycles (12h) of zero new jobs
                if self._consecutive_zero_cycles > 0 and self._consecutive_zero_cycles % 12 == 0:
                    days = self._consecutive_zero_cycles // 24
                    hours = (self._consecutive_zero_cycles % 24)
                    alert = (
                        f"🚨 <b>ALERT: 0 new jobs for {days}d {hours}h</b>\n"
                        f"({self._consecutive_zero_cycles} consecutive cycles)\n\n"
                        f"Seen jobs in DB: {len(self.job_monitor.seen_jobs_db)}\n"
                        f"Skipped (not expired): {len(self.job_monitor.seen_jobs)}\n"
                        f"TTL: {SEEN_TTL_DAYS}d\n\n"
                        f"Engine is running but not sending any applications."
                    )
                    try:
                        if self.telegram:
                            await self.telegram.send_message(alert)
                    except Exception:
                        pass
                return
            
            # ═════════════════════════════════════════════════════
            # STEP 2 + 3: LangGraph pipeline (score + route + apply)
            # Replaces: _score_and_route_jobs + _process_jobs_with_routing
            #
            # What changed:
            #   - Each job gets thread_id=vjh_{job_id} in SQLite checkpoint
            #   - Already-processed jobs are SKIPPED (fixes Deel x7 deduplication)
            #   - submit_node captures real HTTP response + confirmation_id
            #   - Score 60-69 → interrupt_before submit → Telegram ask → Elena approves
            #   - All stage transitions visible in autonomous_data/vjh_checkpoint.db
            # ═════════════════════════════════════════════════════
            logger.info("📊 Step 2+3: LangGraph pipeline (gate → score → route → apply)...")

            try:
                from ..langgraph_pipeline import VJHLangGraphRunner
                runner = VJHLangGraphRunner()
                cycle_id = datetime.utcnow().strftime("%Y-%m-%d-%Hh")
                lg_summary = await runner.process_jobs(new_jobs, cycle_id=cycle_id)

                # Mirror into CycleStats so _send_cycle_summary still works
                cycle_stats.auto_applied   = lg_summary.get("applied", 0)
                cycle_stats.outreach_sent  = lg_summary.get("outreach_sent", 0)
                cycle_stats.review_queued  = lg_summary.get("human_pending", 0)
                cycle_stats.discarded      = (
                    lg_summary.get("discarded", 0) + lg_summary.get("gated_out", 0)
                )
                cycle_stats.errors         = lg_summary.get("errors", 0)
                skipped = lg_summary.get("skipped_dedup", 0)

                self.stats["applications_sent"] += cycle_stats.auto_applied
                self.stats["founder_outreach"]  += cycle_stats.outreach_sent

                logger.info(
                    f"LangGraph cycle done | applied={cycle_stats.auto_applied} "
                    f"outreach={cycle_stats.outreach_sent} "
                    f"human_pending={cycle_stats.review_queued} "
                    f"discarded={cycle_stats.discarded} "
                    f"skipped_dedup={skipped} "
                    f"errors={cycle_stats.errors}"
                )

            except Exception as lg_err:
                logger.error(f"LangGraph pipeline error: {lg_err}", exc_info=True)
                # Fallback: run old pipeline so cycle never goes completely dark
                logger.warning("Falling back to legacy _score_and_route_jobs")
                scored_jobs = await self._score_and_route_jobs(new_jobs, cycle_stats)
                if scored_jobs:
                    scored_jobs.sort(key=lambda j: j.match_score, reverse=True)
                    await self._process_jobs_with_routing(scored_jobs, cycle_stats)
            
            # ═════════════════════════════════════════════════════
            # STEP 4: Send comprehensive cycle summary
            # ═════════════════════════════════════════════════════
            await self._send_cycle_summary(cycle_stats)
            
            logger.info("=" * 60)
            logger.info(f"✅ AUTONOMOUS CYCLE COMPLETE")
            logger.info(f"   Jobs found: {cycle_stats.jobs_found}")
            logger.info(f"   Auto-applied: {cycle_stats.auto_applied}")
            logger.info(f"   Outreach sent: {cycle_stats.outreach_sent}")
            logger.info(f"   Review queued: {cycle_stats.review_queued}")
            logger.info("=" * 60)
            
            # ═════════════════════════════════════════════════════
            # STEP 5: Send pending follow-ups (added 2026-02-08)
            # ═════════════════════════════════════════════════════
            try:
                await self._send_pending_follow_ups()
            except Exception as fu_err:
                logger.warning(f"⚠️ Follow-up check failed: {fu_err}")

            # ═════════════════════════════════════════════════════
            # STEP 5b: Process warm intro queue (added 2026-02-09)
            # ═════════════════════════════════════════════════════
            try:
                await self._process_warm_intros()
            except Exception as wi_err:
                logger.warning(f"⚠️ Warm intro check failed: {wi_err}")

            # ═════════════════════════════════════════════════════
            # STEP 6: Check for responses (GENIUS FEATURE)
            # This is OPTIONAL and wrapped in try/except - won't break cycle
            # ═════════════════════════════════════════════════════
            try:
                await self._check_for_responses()
            except Exception as resp_err:
                logger.warning(f"⚠️ Response detection skipped: {resp_err}")

            # ═════════════════════════════════════════════════════
            # STEP 7: Accumulate daily stats (for daily summary)
            # ═════════════════════════════════════════════════════
            self._accumulate_daily_stats(cycle_stats)
            
        except Exception as e:
            logger.error(f"❌ Autonomous cycle failed: {e}", exc_info=True)
            
            if self.telegram:
                await self.telegram.notify_error(f"Cycle failed: {str(e)[:200]}")

    async def _score_and_route_jobs(self, jobs: List[JobPosting], stats: CycleStats) -> List[JobPosting]:
        """
        Score all jobs using JobMatcher v3.0 (with bias compensation)
        Returns scored jobs with match_score and match_reasons
        
        🏆 PREMIUM SOURCE BOOST:
        - YC companies get +15 score boost
        - Other premium sources get +5
        
        🎯 PRIORITY COMPANIES (additive — Feb 2026):
        - Companies in priority list get +15 boost and priority_flag=True
        """
        from ..agents.job_matcher import JobMatcher
        from ..database.database_models import is_priority_company
        matcher = JobMatcher()

        # Load priority company slugs (empty set if no DB — backward compatible)
        priority_slugs = set()
        if self.db_helper:
            try:
                priority_slugs = self.db_helper.get_priority_company_slugs()
                if priority_slugs:
                    logger.info(f"🎯 Priority companies loaded: {len(priority_slugs)}")
            except Exception as e:
                logger.debug(f"Priority list not available: {e}")

        scored_jobs = []
        score_distribution = {"0-30": 0, "30-50": 0, "50-60": 0, "60-70": 0, "70+": 0}
        yc_jobs_found = 0
        premium_jobs_found = 0
        
        sample_logged = 0
        
        for job in jobs:
            try:
                # JobMatcher.calculate_match_score now includes bias compensation!
                score, reasons = matcher.calculate_match_score(self.profile, job)
                
                # 🏆 PREMIUM SOURCE BOOST - YC Advantage & Remote-First Radar
                # Check for score_boost in job dict (from YC/DynamiteJobs)
                job_dict = job.to_dict() if hasattr(job, 'to_dict') else (job.model_dump() if hasattr(job, 'model_dump') else {})
                score_boost = job_dict.get('score_boost', 0) or getattr(job, 'score_boost', 0)
                is_yc = job_dict.get('is_yc_company', False) or getattr(job, 'is_yc_company', False)
                is_premium = job_dict.get('is_premium_source', False) or getattr(job, 'is_premium_source', False)
                
                if score_boost > 0:
                    original_score = score
                    score += score_boost
                    score = min(score, 100)  # Cap at 100
                    
                    if is_yc:
                        yc_jobs_found += 1
                        reasons.append(f"🏆 YC Company (+{score_boost})")
                        logger.info(f"🏆 YC BOOST: {job.company} {original_score:.0f} → {score:.0f}")
                    elif is_premium:
                        premium_jobs_found += 1
                        reasons.append(f"⭐ Premium Source (+{score_boost})")

                # 🎯 PRIORITY COMPANIES: additive +15 boost (do not modify base logic)
                job.priority_flag = False
                if priority_slugs and is_priority_company(getattr(job, 'company', '') or '', priority_slugs):
                    job.priority_flag = True
                    stats.priority_matches_found += 1
                    original_score = score
                    score += 15
                    score = min(score, 100)
                    reasons.append("🎯 Priority Company (+15)")
                    logger.info(f"🎯 PRIORITY BOOST: {job.company} {original_score:.0f} → {score:.0f}")
                
                job.match_score = score
                job.match_reasons = reasons
                
                # Store YC flag for outreach messaging
                if is_yc:
                    job.is_yc_company = True
                
                scored_jobs.append(job)
                stats.jobs_scored += 1
                
                # Track distribution
                if score >= 70:
                    score_distribution["70+"] += 1
                elif score >= 60:
                    score_distribution["60-70"] += 1
                elif score >= 50:
                    score_distribution["50-60"] += 1
                elif score >= 30:
                    score_distribution["30-50"] += 1
                else:
                    score_distribution["0-30"] += 1
                
                # Log first few samples for visibility
                if sample_logged < 3:
                    yc_badge = " 🏆YC" if is_yc else ""
                    logger.info(f"📋 Sample score: {job.company}{yc_badge} - {job.title[:40]}... = {score:.0f}")
                    sample_logged += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ Scoring failed for {getattr(job, 'company', 'unknown')}: {e}")
                stats.errors += 1
        
        # Log score distribution + premium sources
        logger.info(f"📊 Score distribution: {score_distribution}")
        if yc_jobs_found > 0:
            logger.info(f"🏆 YC companies found: {yc_jobs_found} (+15 boost applied)")
        if premium_jobs_found > 0:
            logger.info(f"⭐ Premium source jobs: {premium_jobs_found}")
        
        return scored_jobs

    async def _process_jobs_with_routing(self, scored_jobs: List[JobPosting], stats: CycleStats):
        """
        Route jobs to appropriate channels based on score:
        ≥60: AUTO_APPLY (ATS application)
        ≥58: OUTREACH (founder finder + warm intro)
        ≥55: REVIEW_QUEUE (save for human review)
        <55: DISCARD
        """
        # ─────────────────────────────────────────────────────
        # CHECK DAILY/TOTAL CAPS (Golden Roadmap compliance)
        # ─────────────────────────────────────────────────────
        from ..core.config import get_settings
        settings = get_settings()
        
        daily_cap = settings.max_daily_applications  # Default: 5
        total_cap = settings.max_total_applications  # Default: 30
        
        today_applications = self.stats.get("applications_today", 0)
        total_applications = self.stats.get("applications_sent", 0)
        
        remaining_today = max(0, daily_cap - today_applications)
        remaining_total = max(0, total_cap - total_applications)
        
        if remaining_today == 0:
            logger.info(f"🛑 Daily cap reached ({daily_cap}/day) - saving jobs for tomorrow")
            if self.telegram:
                await self.telegram.send_message(
                    f"🛑 <b>Daily Cap Reached</b>\n\n"
                    f"Applied to {today_applications} jobs today (max {daily_cap}).\n"
                    f"Precision over volume. ✨"
                )
            return
        
        if remaining_total <= 0:
            logger.warning(f"⚠️ TOTAL CAP REACHED ({total_cap} applications)")
            if self.telegram:
                await self.telegram.send_message(
                    f"⚠️ <b>Total Cap Reached ({total_cap})</b>\n\n"
                    f"Per Golden Roadmap: Reassess strategy."
                )
            return
        
        # ─────────────────────────────────────────────────────
        # DEDUPLICATE & DIVERSIFY
        # ─────────────────────────────────────────────────────
        seen_jobs = set()
        unique_jobs = []
        for job in scored_jobs:
            job_key = f"{job.company}::{job.title}".lower()
            if job_key not in seen_jobs:
                seen_jobs.add(job_key)
                unique_jobs.append(job)
        
        if len(unique_jobs) < len(scored_jobs):
            logger.info(f"🔄 Deduplicated: {len(scored_jobs)} → {len(unique_jobs)} unique jobs")
        
        # Diversify: max 1 job per company per cycle
        MAX_PER_COMPANY = 1
        company_counts = {}
        diverse_jobs = []
        
        for job in unique_jobs:
            company_key = job.company.lower().strip()
            if company_counts.get(company_key, 0) < MAX_PER_COMPANY:
                diverse_jobs.append(job)
                company_counts[company_key] = company_counts.get(company_key, 0) + 1
        
        if len(diverse_jobs) < len(unique_jobs):
            logger.info(f"🏢 Diversified: {len(unique_jobs)} → {len(diverse_jobs)} jobs across {len(company_counts)} companies")
        
        # ═════════════════════════════════════════════════════
        # MULTI-CHANNEL ROUTING (THE KEY INNOVATION)
        # ═════════════════════════════════════════════════════
        
        logger.info("🔀 Starting multi-channel routing...")
        
        PRIORITY_OUTREACH_THRESHOLD = 50  # Safe override: priority companies eligible at 50+

        for job in diverse_jobs:
            final_score = job.match_score
            priority_flag = getattr(job, 'priority_flag', False)
            outreach_eligible = (
                final_score >= OUTREACH_THRESHOLD or
                (priority_flag and final_score >= PRIORITY_OUTREACH_THRESHOLD)
            )

            try:
                # ─────────────────────────────────────────────────
                # ROUTE 1: AUTO-APPLY (≥60)
                # ─────────────────────────────────────────────────
                if final_score >= AUTO_APPLY_THRESHOLD:
                    # Check if we have capacity
                    if stats.auto_applied >= remaining_today:
                        logger.info(f"⏸️ Daily cap reached, queuing remaining jobs for review")
                        await self._save_for_review(job)
                        stats.review_queued += 1
                        continue
                    
                    logger.info(f"🎯 AUTO-APPLY ({final_score:.0f}): {job.company} - {job.title[:50]}")
                    
                    # Research company first
                    company_intel = await self._research_company(job)
                    
                    # Apply through ATS
                    success = await self._apply_to_job(job, company_intel)
                    
                    if success:
                        stats.auto_applied += 1
                        if priority_flag:
                            stats.priority_applied += 1
                        self.stats["applications_today"] += 1
                        self.stats["applications_sent"] += 1
                        logger.info(f"✅ Application cycle completed for {job.company} (see delivery log above)")
                        
                        # Add to top matches
                        if len(stats.top_matches) < 5:
                            stats.top_matches.append(job)
                    else:
                        logger.error(f"❌ Application failed for {job.company}")
                        stats.errors += 1
                    
                    # ─────────────────────────────────────────────
                    # PARALLEL: Also send founder outreach if strong
                    # (or priority company with score ≥50)
                    # Capped at MAX_DAILY_OUTREACH (1-2/day)
                    # ─────────────────────────────────────────────
                    if outreach_eligible and self.founder_finder and self._check_outreach_cap():
                        try:
                            result = await self.founder_finder.find_and_message(job, self.profile)
                            if result.get('success'):
                                stats.outreach_sent += 1
                                if priority_flag:
                                    stats.priority_outreach_sent += 1
                                self.stats["founder_outreach"] += 1
                                self._record_outreach_sent()
                                logger.info(f"🤝 Outreach sent for {job.company} (score: {final_score:.0f}) [{self._outreach_today}/{MAX_DAILY_OUTREACH} today]")
                                # Record for follow-up
                                outreach_email = result.get('email', '')
                                if outreach_email and hasattr(self, 'follow_up_engine'):
                                    self.follow_up_engine.record_sent(
                                        company=job.company,
                                        title=job.title,
                                        email=outreach_email,
                                        channel="outreach",
                                    )
                        except Exception as e:
                            logger.warning(f"⚠️ Outreach failed for {job.company}: {e}")
                    elif outreach_eligible and not self._check_outreach_cap():
                        logger.info(f"⏸️ Outreach cap reached ({MAX_DAILY_OUTREACH}/day) - skipping outreach for {job.company}")
                
                # ─────────────────────────────────────────────────
                # ROUTE 2: OUTREACH ONLY (≥58 or priority ≥50)
                # For jobs that don't quite make auto-apply but worth warm intro
                # ─────────────────────────────────────────────────
                elif outreach_eligible:
                    if not self._check_outreach_cap():
                        logger.info(f"⏸️ Outreach cap reached ({MAX_DAILY_OUTREACH}/day) - saving {job.company} for review instead")
                        await self._save_for_review(job)
                        stats.review_queued += 1
                        continue

                    logger.info(f"🤝 OUTREACH ({final_score:.0f}): {job.company} - {job.title[:50]}")
                    
                    if self.founder_finder:
                        try:
                            result = await self.founder_finder.find_and_message(job, self.profile)
                            if result.get('success'):
                                stats.outreach_sent += 1
                                if priority_flag:
                                    stats.priority_outreach_sent += 1
                                self.stats["founder_outreach"] += 1
                                self._record_outreach_sent()
                                logger.info(f"✅ Outreach sent to {job.company} [{self._outreach_today}/{MAX_DAILY_OUTREACH} today]")
                                # Record for follow-up
                                outreach_email = result.get('email', '')
                                if outreach_email and hasattr(self, 'follow_up_engine'):
                                    self.follow_up_engine.record_sent(
                                        company=job.company,
                                        title=job.title,
                                        email=outreach_email,
                                        channel="outreach",
                                    )
                        except Exception as e:
                            logger.warning(f"⚠️ Outreach failed for {job.company}: {e}")
                
                # ─────────────────────────────────────────────────
                # ROUTE 3: REVIEW QUEUE (55-57)
                # Save for human review
                # ─────────────────────────────────────────────────
                elif final_score >= REVIEW_THRESHOLD:
                    await self._save_for_review(job)
                    stats.review_queued += 1
                    logger.info(f"📋 REVIEW ({final_score:.0f}): {job.company} - {job.title[:50]}")
                
                # ─────────────────────────────────────────────────
                # ROUTE 4: DISCARD (<55)
                # ─────────────────────────────────────────────────
                else:
                    stats.discarded += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to process {job.company}: {e}")
                stats.errors += 1
        
        # Log near-misses if no auto-applies
        if stats.auto_applied == 0 and scored_jobs:
            logger.info("📊 Top 5 near-misses:")
            for job in scored_jobs[:5]:
                logger.info(f"   {job.match_score:.0f}: {job.company} - {job.title[:40]}")

    async def _research_company(self, job: JobPosting) -> Dict:
        """Research company before applying"""
        try:
            company_intel = await self.company_researcher.research_company(
                job.company, 
                job.url
            )
            self.stats["companies_researched"] += 1
            return company_intel
        except Exception as e:
            logger.warning(f"⚠️ Company research failed for {job.company}: {e}")
            return {}

    async def _apply_to_job(self, job: JobPosting, company_intel: Dict) -> bool:
        """Generate and send application materials"""
        if not self.auto_applicator:
            logger.warning("⚠️ Auto-applicator not available")
            return False
        
        try:
            job_dict = {
                'company': job.company,
                'title': job.title,
                'description': job.description,
                'url': job.url,
                'match_score': job.match_score,
                'source': str(job.source),
                'location': job.location,
                'company_intel': company_intel,
            }
            
            result = await self.auto_applicator.process_job(job_dict)
            
            if result.get('materials_generated'):
                self.stats["applications_generated"] += 1
                logger.info(f"✅ Application materials ready for {job.company}")
            
            applied = bool(result.get('application_delivered'))
            
            if applied:
                parts = []
                if result.get('ats_live_submitted'):
                    parts.append(f"ATS:{result.get('ats_type', '?')}")
                if result.get('email_sent'):
                    parts.append('email')
                logger.info(
                    f"✅ Application delivered for {job.company} ({', '.join(parts) if parts else 'channel'})"
                )
            elif result.get('materials_generated'):
                logger.warning(
                    f"📄 Materials only for {job.company} — no live ATS submit and no application email"
                )
            
            # Mark as applied in seen_jobs so it's never retried (TTL-proof)
            if applied and hasattr(self, 'job_monitor') and self.job_monitor:
                job_id = f"{job.company}::{job.title}".lower()
                self.job_monitor.mark_applied(job_id, company=job.company, title=job.title)
            
            # Record for follow-up if we have an email
            if applied and hasattr(self, 'follow_up_engine'):
                email_used = result.get('email_sent_to', '') or result.get('recipient_email', '')
                if email_used:
                    self.follow_up_engine.record_sent(
                        company=job.company,
                        title=job.title,
                        email=email_used,
                        channel="application",
                    )
            
            return applied
            
        except Exception as e:
            logger.error(f"❌ Auto-applicator error for {job.company}: {e}")
            return False

    async def _save_for_review(self, job: JobPosting):
        """Save job to review queue in database"""
        try:
            if not self.db_helper:
                logger.debug("No database helper, skipping review queue save")
                return
                
            job_data = {
                'job_id': getattr(job, 'id', None) or f"{job.company}_{job.title}",
                'company': job.company,
                'title': job.title,
                'score': job.match_score,
                'reasons': getattr(job, 'match_reasons', []),
                'status': 'review_queue',
                'url': getattr(job, 'url', ''),
                'posted_date': getattr(job, 'posted_date', None),
                'saved_at': datetime.utcnow().isoformat()
            }
            
            # Save to database (adjust based on your DB implementation)
            # await self.db_helper.save_job_for_review(job_data)
            
            logger.debug(f"💾 Saved {job.company} to review queue")
        except Exception as e:
            logger.warning(f"Failed to save job for review: {e}")

    async def _send_cycle_summary(self, stats: CycleStats):
        """Send comprehensive cycle summary to Telegram"""
        if not self.telegram:
            return
        
        try:
            summary = f"""🔄 <b>Autonomous Cycle Complete</b>

📊 <b>Results:</b>
• {stats.jobs_found} jobs found
• {stats.jobs_scored} jobs scored
• {stats.auto_applied} applications sent
• {stats.outreach_sent} founder outreach sent
• {stats.review_queued} saved for review
• {stats.discarded} jobs discarded"""

            if stats.errors > 0:
                summary += f"\n⚠️ {stats.errors} errors occurred"
            
            # Priority companies visibility (additive — Feb 2026)
            if stats.priority_matches_found or stats.priority_outreach_sent or stats.priority_applied:
                summary += f"\n\n🎯 <b>Priority:</b> {stats.priority_matches_found} found, {stats.priority_outreach_sent} outreach, {stats.priority_applied} applied"
            
            if stats.top_matches:
                summary += f"\n\n🏆 <b>Top Matches:</b>"
                for i, job in enumerate(stats.top_matches[:3], 1):
                    summary += f"\n{i}. {job.company} ({job.match_score:.0f}/100)"
                    summary += f"\n   {job.title[:50]}"
            
            # Add daily progress
            today_total = self.stats.get("applications_today", 0)
            summary += f"\n\n📅 <b>Today:</b> {today_total}/5 applications"
            
            await self.telegram.send_message(summary)
            
        except Exception as e:
            logger.error(f"Failed to send cycle summary: {e}")
    
    async def _check_for_responses(self):
        """
        🧠 GENIUS FEATURE: AI-Powered Response Detection
        
        Scans inbox for responses to job applications and alerts on hot leads.
        This runs AFTER each cycle completes (safe, won't break main flow).
        """
        try:
            from .response_detector import ResponseDetector, ResponseType, save_response_to_db
            
            logger.info("🧠 Step 5: Checking for responses (AI-powered)...")
            
            detector = ResponseDetector()
            responses = await detector.scan_for_responses(hours_back=24)
            
            # Process hot leads (positive responses and questions)
            hot_leads = [r for r in responses if r.response_type in [ResponseType.POSITIVE, ResponseType.QUESTION]]
            
            if hot_leads:
                logger.info(f"🔥 Found {len(hot_leads)} hot leads!")
                
                for lead in hot_leads:
                    # Save to database for success prediction model
                    save_response_to_db(lead)
                    
                    # Send Telegram alert for interview requests
                    if self.telegram and lead.response_type == ResponseType.POSITIVE:
                        alert = f"""🔥🔥🔥 <b>INTERVIEW REQUEST DETECTED!</b>

<b>From:</b> {lead.from_name}
<b>Company:</b> {lead.company_name or 'Unknown'}
<b>Subject:</b> {lead.subject}

<b>AI Analysis:</b> {lead.ai_analysis}

<b>Action:</b> {lead.suggested_action}

⚡ <b>RESPOND WITHIN 24 HOURS!</b>"""
                        await self.telegram.send_message(alert)
                    
                    elif self.telegram and lead.response_type == ResponseType.QUESTION:
                        alert = f"""❓ <b>Question from Recruiter</b>

<b>From:</b> {lead.from_name}
<b>Company:</b> {lead.company_name or 'Unknown'}
<b>Subject:</b> {lead.subject}

<b>AI Analysis:</b> {lead.ai_analysis}

<b>Action:</b> {lead.suggested_action}"""
                        await self.telegram.send_message(alert)
            
            # Also save rejections for learning
            rejections = [r for r in responses if r.response_type == ResponseType.REJECTION]
            for rejection in rejections:
                save_response_to_db(rejection)
            
            # Log summary
            positive_count = sum(1 for r in responses if r.response_type == ResponseType.POSITIVE)
            question_count = sum(1 for r in responses if r.response_type == ResponseType.QUESTION)
            rejection_count = len(rejections)
            
            if positive_count or question_count:
                logger.info(f"📊 Response summary: {positive_count} interviews, {question_count} questions, {rejection_count} rejections")
            else:
                logger.info(f"📊 Response check complete: No hot leads (found {rejection_count} rejections)")
            
            detector.disconnect()
            
        except ImportError:
            logger.debug("Response detector not available - skipping")
        except Exception as e:
            logger.warning(f"⚠️ Response detection error (non-fatal): {e}")

    # ─────────────────────────────────────────────────────
    # FOLLOW-UP ENGINE (added 2026-02-08)
    # ─────────────────────────────────────────────────────
    async def _send_pending_follow_ups(self):
        """Check and send any due follow-ups."""
        if not hasattr(self, 'follow_up_engine'):
            return

        logger.info("📬 Step 5: Checking for pending follow-ups...")

        # We need the email service
        email_service = None
        if self.auto_applicator and hasattr(self.auto_applicator, 'email_service'):
            email_service = self.auto_applicator.email_service
        else:
            try:
                from .email_service import create_email_service
                email_service = create_email_service()
            except Exception:
                pass

        if not email_service:
            logger.warning("⚠️ No email service available for follow-ups")
            return

        fu_stats = await self.follow_up_engine.check_and_send_follow_ups(email_service)

        if fu_stats["sent"] > 0:
            self._daily_stats["follow_ups_sent"] += fu_stats["sent"]
            logger.info(
                f"📬 Follow-ups: {fu_stats['sent']} sent, "
                f"{fu_stats['skipped']} skipped, {fu_stats['errors']} errors"
            )
            # Notify via Telegram
            if self.telegram:
                await self.telegram.send_message(
                    f"📬 <b>Follow-ups sent: {fu_stats['sent']}</b>\n"
                    f"Checked {fu_stats['checked']} tracked applications"
                )
        else:
            logger.info(f"📬 No follow-ups due (checked {fu_stats['checked']})")

    # ─────────────────────────────────────────────────────
    # WARM INTRO PROCESSING (added 2026-02-09)
    # ─────────────────────────────────────────────────────
    async def _process_warm_intros(self):
        """Check warm intro queue and send messages to available contacts."""
        if not self.warm_intro_queue:
            return

        # Only process once per day (at first cycle)
        today = datetime.utcnow().date()
        if getattr(self, '_warm_intro_date', None) == today:
            return
        
        # Check outreach cap (warm intros share the daily outreach budget)
        if not self._check_outreach_cap():
            logger.info(f"⏸️ Outreach cap reached - skipping warm intros today")
            return

        available = self.warm_intro_queue.get_available_contacts(limit=1)
        if not available:
            logger.info("🤝 Warm intros: No contacts available (all on cooldown or none active)")
            self._warm_intro_date = today
            return

        contact = available[0]
        logger.info(f"🤝 Processing warm intro for: {contact['name']} ({contact['network']})")

        # Generate message
        message = self.warm_intro_queue.generate_warm_message(contact)

        # Record the outreach
        self.warm_intro_queue.record_outreach(
            contact_id=contact["id"],
            channel="linkedin",
            message_preview=message[:200],
            message_type="warm_intro",
        )
        self._record_outreach_sent()
        self._warm_intro_date = today

        # Notify via Telegram so Elena can copy/send the message
        if self.telegram:
            network_label = {
                "cursor_meetup": "Cursor Meetup",
                "panama_ecosystem": "Panama/ISD",
                "online_community": "Online Community",
                "linkedin_connection": "LinkedIn",
                "conference": "Conference",
                "referral": "Referral",
                "other": "Network",
            }.get(contact["network"], contact["network"])

            alert = (
                f"🤝 <b>Warm Intro Ready</b> [{network_label}]\n\n"
                f"<b>Contact:</b> {contact['name']}\n"
                f"<b>Company:</b> {contact.get('company', 'N/A')}\n"
                f"<b>LinkedIn:</b> {contact.get('linkedin_url', 'N/A')}\n\n"
                f"<b>Message:</b>\n<pre>{message[:500]}</pre>\n\n"
                f"📋 Copy and send via LinkedIn/email.\n"
                f"Outreach today: {self._outreach_today}/{MAX_DAILY_OUTREACH}"
            )
            await self.telegram.send_message(alert)

        logger.info(f"✅ Warm intro queued for {contact['name']} [{self._outreach_today}/{MAX_DAILY_OUTREACH} today]")

    # ─────────────────────────────────────────────────────
    # DAILY STATS ACCUMULATION (added 2026-02-08)
    # ─────────────────────────────────────────────────────
    def _accumulate_daily_stats(self, cycle_stats: CycleStats):
        """Accumulate cycle stats into daily totals."""
        today = datetime.utcnow().date().isoformat()

        # Reset if new day
        if self._daily_stats.get("date") != today:
            self._daily_stats = {
                "date": today,
                "cycles_run": 0,
                "total_jobs_found": 0,
                "total_jobs_scored": 0,
                "total_auto_applied": 0,
                "total_outreach_sent": 0,
                "total_review_queued": 0,
                "total_discarded": 0,
                "total_errors": 0,
                "follow_ups_sent": 0,
                "top_companies": [],
            }
            # Also reset daily application counter
            self.stats["applications_today"] = 0

        self._daily_stats["cycles_run"] += 1
        self._daily_stats["total_jobs_found"] += cycle_stats.jobs_found
        self._daily_stats["total_jobs_scored"] += cycle_stats.jobs_scored
        self._daily_stats["total_auto_applied"] += cycle_stats.auto_applied
        self._daily_stats["total_outreach_sent"] += cycle_stats.outreach_sent
        self._daily_stats["total_review_queued"] += cycle_stats.review_queued
        self._daily_stats["total_discarded"] += cycle_stats.discarded
        self._daily_stats["total_errors"] += cycle_stats.errors

        # Track top companies applied to
        for job in cycle_stats.top_matches[:3]:
            self._daily_stats["top_companies"].append(
                f"{job.company} ({job.match_score:.0f})"
            )

    # ─────────────────────────────────────────────────────
    # DAILY SUMMARY SCHEDULER (added 2026-02-08)
    # Sends once per day at 20:00 UTC (3:00 PM Panama)
    # ─────────────────────────────────────────────────────
    async def _check_daily_summary_schedule(self):
        """Check if it's time to send the daily summary."""
        now_utc = datetime.utcnow()
        today = now_utc.date()

        # Already sent today?
        if self._last_daily_summary_date == today:
            return

        # Send at 20:00 UTC (3pm Panama)
        if now_utc.hour == 20 and now_utc.minute >= 0:
            await self._send_daily_digest()
            self._last_daily_summary_date = today

    async def _send_daily_digest(self):
        """Send comprehensive daily digest to Telegram."""
        if not self.telegram:
            return

        try:
            ds = self._daily_stats
            today_str = datetime.utcnow().strftime("%B %d, %Y")

            # Warm intro summary
            wi_summary = ""
            if self.warm_intro_queue:
                wi = self.warm_intro_queue.get_stats()
                wi_summary = (
                    f"\n\n🤝 <b>Warm Intro Network:</b>\n"
                    f"• {wi['total_contacts']} contacts in database\n"
                    f"• {wi['available_today']} available for outreach\n"
                    f"• {wi['total_outreach_sent']} total warm intros sent\n"
                    f"• {wi['responses_received']} responses ({wi['response_rate']})"
                )

            # Follow-up engine summary
            fu_summary = ""
            if hasattr(self, 'follow_up_engine'):
                fu = self.follow_up_engine.get_summary()
                fu_summary = (
                    f"\n\n📬 <b>Follow-Up Pipeline:</b>\n"
                    f"• {fu['total_tracked']} applications tracked\n"
                    f"• {fu['awaiting_first_followup']} awaiting first follow-up\n"
                    f"• {fu['followed_up_once']} followed up once\n"
                    f"• {fu['followed_up_twice']} completed (2 follow-ups)\n"
                    f"• {fu['got_response']} got responses"
                )

            # Seen jobs summary
            seen_info = ""
            if hasattr(self, 'job_monitor'):
                seen_info = (
                    f"\n\n🗄️ <b>Job Database:</b>\n"
                    f"• {len(self.job_monitor.seen_jobs_db)} total jobs tracked\n"
                    f"• {len(self.job_monitor.seen_jobs)} in skip set\n"
                    f"• TTL: {SEEN_TTL_DAYS} days"
                )

            # Top companies
            top_companies_str = ""
            if ds.get("top_companies"):
                top_companies_str = "\n\n🏆 <b>Applied Today:</b>\n"
                for c in ds["top_companies"][:5]:
                    top_companies_str += f"• {c}\n"

            message = (
                f"📊 <b>DAILY DIGEST — {today_str}</b>\n\n"
                f"<b>Today's Activity ({ds['cycles_run']} cycles):</b>\n"
                f"🔍 Jobs found: {ds['total_jobs_found']}\n"
                f"📊 Jobs scored: {ds['total_jobs_scored']}\n"
                f"🎯 Auto-applied: {ds['total_auto_applied']}\n"
                f"🤝 Outreach sent: {ds['total_outreach_sent']}\n"
                f"📋 Review queued: {ds['total_review_queued']}\n"
                f"📬 Follow-ups sent: {ds['follow_ups_sent']}\n"
                f"❌ Discarded: {ds['total_discarded']}"
                f"{top_companies_str}"
                f"{wi_summary}"
                f"{fu_summary}"
                f"{seen_info}"
                f"\n\n🤖 <i>VibeJobHunter running 24/7 on Oracle</i>"
            )

            if ds["total_errors"] > 0:
                message += f"\n\n⚠️ {ds['total_errors']} errors today"

            await self.telegram.send_message(message)
            logger.info("📊 Daily digest sent to Telegram")

        except Exception as e:
            logger.error(f"Failed to send daily digest: {e}")
