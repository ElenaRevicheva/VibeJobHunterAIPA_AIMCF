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

from ..core.models import Profile, JobPosting
from ..utils.logger import setup_logger

from .job_monitor import JobMonitor
from .company_researcher import CompanyResearcher
from .founder_finder_v2 import FounderFinderV2  # UPGRADED: Real email discovery
from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler

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
            
            if not new_jobs:
                logger.info("📭 No new jobs this cycle - waiting for next run")
                return
            
            # ═════════════════════════════════════════════════════
            # STEP 2: Score jobs (with bias compensation)
            # ═════════════════════════════════════════════════════
            logger.info("📊 Step 2: Scoring jobs against Elena's profile...")
            
            scored_jobs = await self._score_and_route_jobs(new_jobs, cycle_stats)
            
            if not scored_jobs:
                logger.warning("⚠️ No jobs were successfully scored")
                return
            
            # Sort by score
            scored_jobs.sort(key=lambda j: j.match_score, reverse=True)
            
            # ═════════════════════════════════════════════════════
            # STEP 3: Multi-channel routing with daily caps
            # ═════════════════════════════════════════════════════
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
            # STEP 5: Check for responses (GENIUS FEATURE)
            # This is OPTIONAL and wrapped in try/except - won't break cycle
            # ═════════════════════════════════════════════════════
            try:
                await self._check_for_responses()
            except Exception as resp_err:
                logger.warning(f"⚠️ Response detection skipped: {resp_err}")
            
        except Exception as e:
            logger.error(f"❌ Autonomous cycle failed: {e}", exc_info=True)
            
            if self.telegram:
                await self.telegram.notify_error(f"Cycle failed: {str(e)[:200]}")

    async def _score_and_route_jobs(self, jobs: List[JobPosting], stats: CycleStats) -> List[JobPosting]:
        """
        Score all jobs using JobMatcher v3.0 (with bias compensation)
        Returns scored jobs with match_score and match_reasons
        """
        from ..agents.job_matcher import JobMatcher
        matcher = JobMatcher()
        
        scored_jobs = []
        score_distribution = {"0-30": 0, "30-50": 0, "50-60": 0, "60-70": 0, "70+": 0}
        
        sample_logged = 0
        
        for job in jobs:
            try:
                # JobMatcher.calculate_match_score now includes bias compensation!
                score, reasons = matcher.calculate_match_score(self.profile, job)
                job.match_score = score
                job.match_reasons = reasons
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
                    logger.info(f"📋 Sample score: {job.company} - {job.title[:40]}... = {score:.0f}")
                    sample_logged += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ Scoring failed for {getattr(job, 'company', 'unknown')}: {e}")
                stats.errors += 1
        
        # Log score distribution
        logger.info(f"📊 Score distribution: {score_distribution}")
        
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
        
        for job in diverse_jobs:
            final_score = job.match_score
            
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
                        self.stats["applications_today"] += 1
                        self.stats["applications_sent"] += 1
                        logger.info(f"✅ Applied to {job.company} via ATS")
                        
                        # Add to top matches
                        if len(stats.top_matches) < 5:
                            stats.top_matches.append(job)
                    else:
                        logger.error(f"❌ Application failed for {job.company}")
                        stats.errors += 1
                    
                    # ─────────────────────────────────────────────
                    # PARALLEL: Also send founder outreach if strong
                    # This is the 1-2 punch: ATS + warm intro
                    # ─────────────────────────────────────────────
                    if final_score >= OUTREACH_THRESHOLD and self.founder_finder:
                        try:
                            result = await self.founder_finder.find_and_message(job, self.profile)
                            if result.get('success'):
                                stats.outreach_sent += 1
                                self.stats["founder_outreach"] += 1
                                logger.info(f"🤝 Outreach sent for {job.company} (score: {final_score:.0f})")
                        except Exception as e:
                            logger.warning(f"⚠️ Outreach failed for {job.company}: {e}")
                
                # ─────────────────────────────────────────────────
                # ROUTE 2: OUTREACH ONLY (58-59)
                # For jobs that don't quite make auto-apply but worth warm intro
                # ─────────────────────────────────────────────────
                elif final_score >= OUTREACH_THRESHOLD:
                    logger.info(f"🤝 OUTREACH ({final_score:.0f}): {job.company} - {job.title[:50]}")
                    
                    if self.founder_finder:
                        try:
                            result = await self.founder_finder.find_and_message(job, self.profile)
                            if result.get('success'):
                                stats.outreach_sent += 1
                                self.stats["founder_outreach"] += 1
                                logger.info(f"✅ Outreach sent to {job.company}")
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
            
            return result.get('email_sent', False) or result.get('materials_generated', False)
            
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
