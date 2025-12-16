"""
🤖 AUTONOMOUS ORCHESTRATOR
The brain of the autonomous job hunting engine.
Coordinates all agents and runs the complete workflow 24/7.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from ..core.models import Profile, JobPosting
from ..utils.logger import setup_logger

from .job_monitor import JobMonitor
from .company_researcher import CompanyResearcher
from .founder_finder import FounderFinder
from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler

logger = setup_logger(__name__)

# 🔥 MODULE VERSION — LOGS ON IMPORT
ORCHESTRATOR_VERSION = "4.2_REAL_APPLICATIONS"
ORCHESTRATOR_BUILD = "2025-12-14_20:00_UTC"
ORCHESTRATOR_COMMIT = "auto_apply_LIVE"

logger.info("💥" * 35)
logger.info("🚨 PHASE 1 COMPLETE - REAL APPLICATIONS ACTIVE! 🚨")
logger.info(f"📦 VERSION: {ORCHESTRATOR_VERSION}")
logger.info(f"🎯 BUILD: {ORCHESTRATOR_BUILD} | COMMIT: {ORCHESTRATOR_COMMIT}")
logger.info("🧠 NEW: Auto-Applicator with Elena's Real Resume")
logger.info("💥" * 35)


class AutonomousOrchestrator:
    """
    🚀 THE BRAIN: Coordinates all autonomous agents
    """

    def __init__(self, profile: Profile, telegram_enabled: bool = True):
        if profile is None:
            raise RuntimeError("❌ PROFILE IS REQUIRED — REFUSING SILENT STARTUP")

        self.profile = profile
        self.is_running = False
        self.last_linkedin_post_date = None

        logger.info("=" * 80)
        logger.info("🎨🚀 VIBEJOBHUNTER ORCHESTRATOR v4.2 — REAL APPLICATIONS 🚀🎨")
        logger.info("=" * 80)

        # ─────────────────────────────
        # Notifications
        # ─────────────────────────────
        from ..notifications import TelegramNotifier, LinkedInCMO

        self.telegram = TelegramNotifier() if telegram_enabled else None

        try:
            self.linkedin_cmo = LinkedInCMO(profile=self.profile)
            logger.info("✅ LinkedIn CMO initialized")
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
        self.founder_finder = FounderFinder()
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
        }

        self.data_dir = Path("autonomous_data")
        self.data_dir.mkdir(exist_ok=True)

        logger.info("🚀 Autonomous Orchestrator READY")

    # ─────────────────────────────
    # LINKEDIN CMO SCHEDULER (FIXED)
    # ─────────────────────────────
    async def check_linkedin_schedule(self):
        if not self.linkedin_cmo or not self.linkedin_cmo.enabled:
            return

        now = datetime.now()
        today = now.date()

        if self.last_linkedin_post_date == today:
            return

        if now.hour == 21:
            language = "en" if now.weekday() % 2 == 0 else "es"

            logger.info("📣 Triggering LinkedIn CMO post")
            await self.linkedin_cmo.post_to_linkedin(
                post_type="random",
                language=language
            )

            self.last_linkedin_post_date = today

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
                await asyncio.sleep(600)

        asyncio.create_task(linkedin_loop())

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
