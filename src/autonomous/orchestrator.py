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

# Module version
ORCHESTRATOR_VERSION = "4.3_AUTONOMOUS_CYCLE"
logger.info(f"📦 Orchestrator v{ORCHESTRATOR_VERSION} loaded")


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

    # ─────────────────────────────
    # CORE AUTONOMOUS CYCLE (THE MISSING PIECE!)
    # ─────────────────────────────
    async def run_autonomous_cycle(self):
        """
        🔥 THE MAIN JOB HUNTING CYCLE 🔥
        
        This runs every hour and:
        1. Fetches new jobs from ATS APIs
        2. Scores and filters them
        3. Generates application materials
        4. Sends applications (if auto_apply enabled)
        5. Notifies via Telegram
        """
        logger.info("=" * 60)
        logger.info("🔄 AUTONOMOUS CYCLE STARTED")
        logger.info("=" * 60)
        
        try:
            # ─────────────────────────────
            # STEP 1: Find new jobs
            # ─────────────────────────────
            logger.info("🔍 Step 1: Finding new jobs...")
            
            new_jobs = await self.job_monitor.find_new_jobs(
                target_roles=self.profile.target_roles,
                max_results=50
            )
            
            self.stats["jobs_found"] += len(new_jobs)
            logger.info(f"✅ Found {len(new_jobs)} new jobs")
            
            if not new_jobs:
                logger.info("📭 No new jobs this cycle - waiting for next run")
                return
            
            # ─────────────────────────────
            # STEP 2: Score and filter jobs
            # ─────────────────────────────
            logger.info("📊 Step 2: Scoring jobs against Elena's profile...")
            
            from ..agents.job_matcher import JobMatcher
            matcher = JobMatcher()
            
            scored_jobs = []
            score_distribution = {"0-30": 0, "30-50": 0, "50-60": 0, "60-70": 0, "70+": 0}
            
            for job in new_jobs:
                try:
                    score, reasons = matcher.calculate_match_score(self.profile, job)
                    job.match_score = score
                    job.match_reasons = reasons
                    scored_jobs.append(job)
                    
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
                    
                    if score >= 65:
                        logger.info(f"🎯 GOOD MATCH ({score:.0f}): {job.company} - {job.title}")
                except Exception as e:
                    logger.warning(f"⚠️ Scoring failed for {job.company}: {e}")
            
            # Log score distribution
            logger.info(f"📊 Score distribution: {score_distribution}")
            
            # Filter to quality matches (lowered to >= 55 to capture more relevant jobs)
            MIN_SCORE = 55
            qualified_jobs = [j for j in scored_jobs if j.match_score >= MIN_SCORE]
            logger.info(f"✅ {len(qualified_jobs)} jobs passed quality threshold (≥{MIN_SCORE} score)")
            
            if not qualified_jobs:
                logger.info("📭 No jobs met quality threshold this cycle")
                
                # Still notify about what was found
                if self.telegram and len(scored_jobs) > 0:
                    top_job = max(scored_jobs, key=lambda j: j.match_score)
                    await self.telegram.send_message(
                        f"🔍 <b>Cycle Complete</b>\n\n"
                        f"Found {len(new_jobs)} jobs, but none met quality threshold.\n"
                        f"Best match: {top_job.company} ({top_job.match_score:.0f}/100)"
                    )
                return
            
            # ─────────────────────────────
            # STEP 3: Process top jobs
            # ─────────────────────────────
            logger.info("📝 Step 3: Processing top qualified jobs...")
            
            # Sort by score and take top 5
            qualified_jobs.sort(key=lambda j: j.match_score, reverse=True)
            top_jobs = qualified_jobs[:5]
            
            applications_generated = 0
            
            for job in top_jobs:
                try:
                    logger.info(f"📋 Processing: {job.company} - {job.title} ({job.match_score:.0f}/100)")
                    
                    # Research company
                    company_intel = {}
                    try:
                        company_intel = await self.company_researcher.research_company(
                            job.company, 
                            job.url
                        )
                        self.stats["companies_researched"] += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Company research failed: {e}")
                    
                    # Generate application materials
                    if self.auto_applicator:
                        job_dict = {
                            'company': job.company,
                            'title': job.title,
                            'description': job.description,
                            'url': job.url,
                            'match_score': job.match_score,
                            'source': str(job.source),
                            'location': job.location,
                        }
                        
                        result = await self.auto_applicator.process_job(job_dict)
                        
                        if result.get('materials_generated'):
                            applications_generated += 1
                            self.stats["applications_generated"] += 1
                            logger.info(f"✅ Application materials ready for {job.company}")
                        
                        if result.get('email_sent'):
                            self.stats["applications_sent"] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process {job.company}: {e}")
            
            # ─────────────────────────────
            # STEP 4: Notify via Telegram
            # ─────────────────────────────
            if self.telegram:
                summary = f"""🔄 <b>Autonomous Cycle Complete!</b>

📊 <b>This Cycle:</b>
• Jobs found: {len(new_jobs)}
• Qualified (≥70 score): {len(qualified_jobs)}
• Applications generated: {applications_generated}

🎯 <b>Top Matches:</b>
"""
                for i, job in enumerate(top_jobs[:3], 1):
                    summary += f"{i}. {job.company} - {job.title} ({job.match_score:.0f}/100)\n"
                
                summary += f"\n📁 Materials saved to autonomous_data/applications/"
                
                await self.telegram.send_message(summary)
            
            logger.info("=" * 60)
            logger.info(f"✅ AUTONOMOUS CYCLE COMPLETE")
            logger.info(f"   Jobs found: {len(new_jobs)}")
            logger.info(f"   Qualified: {len(qualified_jobs)}")
            logger.info(f"   Applications: {applications_generated}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Autonomous cycle failed: {e}", exc_info=True)
            
            if self.telegram:
                await self.telegram.notify_error(f"Cycle failed: {str(e)[:200]}")
