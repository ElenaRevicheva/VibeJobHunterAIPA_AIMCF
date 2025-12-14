"""
🤖 AUTONOMOUS ORCHESTRATOR
The brain of the autonomous job hunting engine.
Coordinates all agents and runs the complete workflow 24/7.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..core.models import Profile, JobPosting, ApplicationStatus
from ..core.config import settings
from ..utils.logger import setup_logger

from .job_monitor import JobMonitor
from .company_researcher import CompanyResearcher
from .founder_finder import FounderFinder
from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler

logger = setup_logger(__name__)

# 🔥🔥🔥 MODULE VERSION - Logs on import! 🔥🔥🔥
ORCHESTRATOR_VERSION = "4.2_REAL_APPLICATIONS"
ORCHESTRATOR_BUILD = "2025-12-14_20:00_UTC"
ORCHESTRATOR_COMMIT = "auto_apply_LIVE"

logger.info("💥" * 35)
logger.info("🚨 PHASE 1 COMPLETE - REAL APPLICATIONS ACTIVE! 🚨")
logger.info(f"📦 VERSION: {ORCHESTRATOR_VERSION}")
logger.info(f"🎯 BUILD: {ORCHESTRATOR_BUILD} | COMMIT: {ORCHESTRATOR_COMMIT}")
logger.info(f"🧠 NEW: Auto-Applicator with Elena's Real Resume")
logger.info("💥" * 35)


class AutonomousOrchestrator:
    """
    🚀 THE BRAIN: Coordinates all autonomous agents
    
    Workflow:
    1. Monitor job boards (every hour)
    2. Filter & score new jobs
    3. AUTO-APPLY to best matches (NEW!)
    4. Track in database
    5. Monitor responses
    """
    
    def __init__(self, profile: Profile, telegram_enabled: bool = True):
        logger.info("=" * 80)
        logger.info("🎨🚀 VIBEJOBHUNTER ORCHESTRATOR v4.2 - REAL APPLICATIONS 🚀🎨")
        logger.info("✨ NEW: Auto-Apply with Elena's Real Background ✨")
        logger.info("=" * 80)
        
        self.profile = profile
        self.last_linkedin_post_date = None
        
        # Initialize Telegram notifier
        from ..notifications import TelegramNotifier
        self.telegram = TelegramNotifier()
        
        # Initialize LinkedIn CMO
        logger.info("🔍 Attempting to load LinkedIn CMO...")
        try:
            from ..notifications import LinkedInCMO
            self.linkedin_cmo = LinkedInCMO()
            logger.info("✅ LinkedInCMO initialized successfully")
        except Exception as e:
            logger.error(f"❌ LINKEDIN CMO FAILED TO LOAD: {e}")
            self.linkedin_cmo = None
        
        # Initialize Enhanced Telegram Bot
        logger.info("🤖 Attempting to load Enhanced Telegram Bot...")
        try:
            from ..database.database_models import DatabaseHelper, init_database
            from ..notifications.telegram_bot_enhanced import create_enhanced_bot
            
            init_database()
            self.db_helper = DatabaseHelper()
            logger.info("✅ Database initialized successfully")
            
            self.telegram_bot_enhanced = create_enhanced_bot(db_helper=self.db_helper)
            logger.info("✅ Enhanced Telegram Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Enhanced Telegram Bot failed to load: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.telegram_bot_enhanced = None
            self.db_helper = None
        
        # Initialize Auto-Applicator (REAL APPLICATIONS!)
        logger.info("🎯 Attempting to load Auto-Applicator...")
        try:
            from .auto_applicator import AutoApplicator
            from .email_service import create_email_service
            
            email_service = create_email_service()
            
            self.auto_applicator = AutoApplicator(
                profile=profile,
                db_helper=self.db_helper if hasattr(self, 'db_helper') else None,
                email_service=email_service,
                telegram=self.telegram if hasattr(self, 'telegram') else None
            )
            logger.info("✅ Auto-Applicator initialized - REAL APPLICATIONS ENABLED!")
            
        except Exception as e:
            logger.error(f"❌ Auto-Applicator failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.auto_applicator = None
        
        # Initialize all agents
        self.job_monitor = JobMonitor()
        self.company_researcher = CompanyResearcher()
        self.founder_finder = FounderFinder()
        self.message_generator = MessageGenerator(profile)
        self.multi_channel_sender = MultiChannelSender()
        self.demo_tracker = DemoTracker()
        self.response_handler = ResponseHandler(profile)
        
        # State management
        self.is_running = False
        self.stats = {
            'jobs_found': 0,
            'companies_researched': 0,
            'messages_sent': 0,
            'demo_clicks': 0,
            'responses_received': 0,
            'interviews_scheduled': 0,
            'applications_generated': 0,  # NEW
            'applications_sent': 0,        # NEW
        }
        
        # Storage
        self.data_dir = Path("autonomous_data")
        self.data_dir.mkdir(exist_ok=True)
        
        logger.info("🚀 Autonomous Orchestrator initialized!")
    
    async def run_autonomous_cycle(self):
        """
        Run one complete autonomous cycle
        This is called every hour by the scheduler
        """
        logger.info("=" * 60)
        logger.info("🤖 STARTING AUTONOMOUS CYCLE")
        logger.info("=" * 60)
        
        try:
            # STEP 1: Find new jobs
            logger.info("🔍 [1/8] Monitoring job boards...")
            new_jobs = await self.job_monitor.find_new_jobs(
                target_roles=self.profile.target_roles,
                max_results=50
            )
            logger.info(f"✅ Found {len(new_jobs)} new jobs")
            self.stats['jobs_found'] += len(new_jobs)
            
            if not new_jobs:
                logger.info("No new jobs found. Cycle complete.")
                return
            
            # STEP 2: Filter & prioritize
            logger.info("🎯 [2/8] Filtering & scoring jobs...")
            top_jobs = await self._filter_and_score(new_jobs)
            logger.info(f"✅ {len(top_jobs)} high-priority jobs identified")
            
            # Store jobs in database
            if self.db_helper:
                try:
                    for job in top_jobs:
                        job_id = f"{job.company}_{job.id if hasattr(job, 'id') else job.title}"
                        self.db_helper.add_job_listing({
                            'id': job_id,
                            'company': job.company,
                            'title': job.title,
                            'url': job.url,
                            'description': getattr(job, 'description', ''),
                            'location': getattr(job, 'location', ''),
                            'ats_type': getattr(job, 'ats_type', ''),
                            'match_score': job.match_score / 100.0,
                        })
                    logger.info(f"✅ Stored {len(top_jobs)} jobs in database")
                except Exception as e:
                    logger.error(f"❌ Failed to store jobs in database: {e}")
            
            # STEP 3: AUTO-APPLY TO BEST JOBS! (NEW!)
            if self.auto_applicator and top_jobs:
                logger.info("🚀 [3/8] AUTO-APPLYING TO TOP JOBS...")
                logger.info(f"  Found {len(top_jobs)} high-priority jobs")
                
                # Filter for very high matches only (score >= 80)
                best_jobs = [j for j in top_jobs if j.match_score >= 80]
                
                if best_jobs:
                    logger.info(f"  Applying to {len(best_jobs)} best matches (score >= 80)")
                    
                    # Convert JobPosting objects to dicts
                    job_dicts = []
                    for job in best_jobs:
                        job_dict = {
                            'company': job.company,
                            'title': job.title,
                            'url': job.url,
                            'description': getattr(job, 'description', ''),
                            'location': getattr(job, 'location', ''),
                            'match_score': job.match_score,
                            'source': getattr(job, 'source', 'ats_scraper')
                        }
                        job_dicts.append(job_dict)
                    
                    # Process applications (max 3 per cycle for safety)
                    application_results = await self.auto_applicator.batch_process_jobs(
                        jobs=job_dicts,
                        max_applications=3
                    )
                    
                    # Update stats
                    self.stats['applications_generated'] = application_results.get('materials_generated', 0)
                    self.stats['applications_sent'] = application_results.get('emails_sent', 0)
                    
                    logger.info(f"✅ [AUTO-APPLY] Cycle complete!")
                    logger.info(f"  📝 Materials generated: {application_results['materials_generated']}")
                    logger.info(f"  📧 Emails sent: {application_results['emails_sent']}")
                    
                    # Notify via Telegram
                    if self.telegram:
                        await self.telegram.send_message(
                            f"🎯 Application Update\n"
                            f"📊 Jobs found: {len(top_jobs)}\n"
                            f"✅ Applied to: {application_results['emails_sent']} companies\n"
                            f"📝 Materials: {application_results['materials_generated']}"
                        )
                else:
                    logger.info("  ⏭️ No jobs with score >= 80, skipping applications")
            
            # Notify about hot jobs (score >85)
            for job in top_jobs:
                if job.match_score >= 85:
                    await self.telegram.notify_hot_job(job)
            
            # STEP 4: Research companies (parallel)
            logger.info("🔬 [4/8] Researching companies...")
            company_intel = await self._research_companies_parallel(top_jobs)
            logger.info(f"✅ Researched {len(company_intel)} companies")
            self.stats['companies_researched'] += len(company_intel)
            
            # STEP 5: Find founders
            logger.info("👤 [5/8] Finding founder contacts...")
            founder_contacts = await self._find_founders(company_intel)
            logger.info(f"✅ Found {len(founder_contacts)} founder contacts")
            
            # STEP 6: Generate personalized messages
            logger.info("✍️ [6/8] Generating personalized outreach...")
            messages = await self._generate_messages(founder_contacts, company_intel)
            logger.info(f"✅ Generated {len(messages)} personalized messages")
            
            # STEP 7: Send via multiple channels
            logger.info("📤 [7/8] Sending multi-channel outreach...")
            sent_results = await self._send_messages(messages)
            logger.info(f"✅ Sent {sent_results['total_sent']} messages")
            self.stats['messages_sent'] += sent_results['total_sent']
            
            # STEP 8: Handle responses & follow-ups
            logger.info("📧 [8/8] Checking responses & scheduling follow-ups...")
            responses = await self.response_handler.check_responses()
            logger.info(f"✅ {len(responses)} new responses")
            self.stats['responses_received'] += len(responses)
            
            # Track demo clicks
            demo_clicks = await self.demo_tracker.get_new_clicks()
            logger.info(f"🔥 {len(demo_clicks)} demo link clicks!")
            self.stats['demo_clicks'] += len(demo_clicks)
            
            # Notify about demo clicks
            for click in demo_clicks:
                await self.telegram.notify_demo_click(
                    company=click.get('company', 'Unknown'),
                    founder_name=click.get('founder_name'),
                    source=click.get('source_channel')
                )
            
            # Auto-schedule interviews
            interviews = await self.response_handler.auto_schedule_interviews(responses)
            logger.info(f"📅 {len(interviews)} interviews auto-scheduled!")
            self.stats['interviews_scheduled'] += len(interviews)
            
            # Notify about new responses
            for response in responses:
                await self.telegram.notify_response_received(
                    company=response.get('company', 'Unknown'),
                    founder_name=response.get('founder_name', 'Founder'),
                    sentiment=response.get('sentiment', 'neutral')
                )
            
            # Notify about scheduled interviews
            for interview in interviews:
                await self.telegram.notify_interview_scheduled(
                    company=interview.get('company', 'Unknown'),
                    date=datetime.fromisoformat(interview.get('timestamp', datetime.now().isoformat())),
                    founder_name=interview.get('founder_name')
                )
            
            # Save cycle results
            await self._save_cycle_results({
                'timestamp': datetime.now().isoformat(),
                'new_jobs': len(new_jobs),
                'top_jobs': len(top_jobs),
                'applications_generated': self.stats.get('applications_generated', 0),
                'applications_sent': self.stats.get('applications_sent', 0),
                'messages_sent': sent_results['total_sent'],
                'responses': len(responses),
                'demo_clicks': len(demo_clicks),
                'interviews': len(interviews),
            })
            
            logger.info("=" * 60)
            logger.info("✅ AUTONOMOUS CYCLE COMPLETE!")
            logger.info(f"📊 Session Stats: {self.stats}")
            logger.info("=" * 60)
            
            # Send cycle completion notification
            await self.telegram.notify_cycle_complete(self.stats)
            
        except Exception as e:
            logger.error(f"❌ Error in autonomous cycle: {e}", exc_info=True)
            await self.telegram.notify_error(str(e))
    
    async def _filter_and_score(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """Filter and score jobs by priority"""
        from ..agents.job_matcher import JobMatcher
        from ..filters.criteria_matcher import CriteriaMatcher
        from ..filters.red_flag_detector import RedFlagDetector
        
        matcher = JobMatcher()
        criteria_matcher = CriteriaMatcher()
        red_flag_detector = RedFlagDetector()
        
        scored_jobs = []
        for job in jobs:
            try:
                score, reasons = matcher.calculate_match_score(self.profile, job)
                job.match_score = score
                job.match_reasons = reasons
                
                criteria_match = criteria_matcher.evaluate_job(job)
                job.criteria_match = criteria_match
                
                has_flags, red_flags = red_flag_detector.scan_job(job)
                job.red_flags = red_flags
                
                if score >= 60 and not any('MAJOR' in flag for flag in red_flags):
                    scored_jobs.append(job)
            
            except Exception as e:
                logger.debug(f"Failed to score job {job.title} at {job.company}: {e}")
                continue
        
        scored_jobs.sort(key=lambda x: x.match_score, reverse=True)
        return scored_jobs[:10]
    
    async def _research_companies_parallel(self, jobs: List[JobPosting]) -> Dict[str, Dict[str, Any]]:
        """Research multiple companies in parallel"""
        tasks = [
            self.company_researcher.research_company(job.company, job.url)
            for job in jobs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        company_intel = {}
        for job, result in zip(jobs, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to research {job.company}: {result}")
                continue
            company_intel[job.company] = result
        
        return company_intel
    
    async def _find_founders(self, company_intel: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find founder contacts for each company"""
        founders = []
        
        for company, intel in company_intel.items():
            try:
                founder_info = await self.founder_finder.find_founder(company, intel)
                if founder_info:
                    founders.append({
                        'company': company,
                        'intel': intel,
                        'founder': founder_info
                    })
            except Exception as e:
                logger.error(f"Failed to find founder for {company}: {e}")
        
        return founders
    
    async def _generate_messages(
        self, 
        founder_contacts: List[Dict[str, Any]], 
        company_intel: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate personalized messages for each founder"""
        messages = []
        
        for contact in founder_contacts:
            company = contact['company']
            intel = contact['intel']
            founder = contact['founder']
            
            try:
                message_variants = await self.message_generator.generate_multi_channel_messages(
                    founder_name=founder.get('name', 'Founder'),
                    company=company,
                    company_intel=intel,
                    job_role=intel.get('target_role', 'Founding Engineer')
                )
                
                messages.append({
                    'company': company,
                    'founder': founder,
                    'messages': message_variants
                })
                
            except Exception as e:
                logger.error(f"Failed to generate message for {company}: {e}")
        
        return messages
    
    async def _send_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send messages via multiple channels"""
        results = {
            'total_sent': 0,
            'linkedin': 0,
            'email': 0,
            'twitter': 0,
            'failed': 0
        }
        
        for message_data in messages:
            try:
                send_results = await self.multi_channel_sender.send_multi_channel(
                    founder=message_data['founder'],
                    messages=message_data['messages'],
                    company=message_data['company']
                )
                
                for channel, success in send_results.items():
                    if success:
                        results[channel] += 1
                        results['total_sent'] += 1
                    else:
                        results['failed'] += 1
                        
            except Exception as e:
                logger.error(f"Failed to send messages for {message_data['company']}: {e}")
                results['failed'] += 1
        
        return results
    
    async def _save_cycle_results(self, cycle_data: Dict[str, Any]):
        """Save cycle results for tracking"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.data_dir / f"cycle_{timestamp}.json"
        
        import json
        with open(results_file, 'w') as f:
            json.dump(cycle_data, f, indent=2)
    
    async def check_linkedin_schedule(self):
        """Check if it's time to post to LinkedIn"""
        if not self.linkedin_cmo or not self.linkedin_cmo.enabled:
            return
        
        now = datetime.now()
        today = now.date()
        day_number = now.weekday()
        hour = now.hour
        
        if self.last_linkedin_post_date == today:
            return
        
        if hour == 21:
            language = "en" if day_number % 2 == 0 else "es"
            
            await self.linkedin_cmo.post_to_linkedin(
                post_type="random",
                language=language
            )
            
            self.last_linkedin_post_date = today
    
    async def start_autonomous_mode(self, interval_hours: int = 1):
        """🚀 START AUTONOMOUS MODE"""
        self.is_running = True
        logger.info(f"🚀 AUTONOMOUS MODE STARTED (every {interval_hours} hour)")
        
        if self.telegram.enabled:
            await self.telegram.notify_startup_success()
            import asyncio as aio
            aio.create_task(self.telegram.start_polling())
        
        if self.telegram_bot_enhanced:
            async def start_enhanced_bot():
                try:
                    await self.telegram_bot_enhanced.app.initialize()
                    await self.telegram_bot_enhanced.app.start()
                    logger.info("✅ Enhanced Telegram Bot started polling")
                    await self.telegram_bot_enhanced.app.updater.start_polling()
                except Exception as e:
                    logger.error(f"❌ Failed to start enhanced bot: {e}")
            
            asyncio.create_task(start_enhanced_bot())
        
        async def check_linkedin_frequently():
            while self.is_running:
                await self.check_linkedin_schedule()
                await asyncio.sleep(10 * 60)
        
        asyncio.create_task(check_linkedin_frequently())
        
        while self.is_running:
            try:
                await self.run_autonomous_cycle()
                logger.info(f"😴 Sleeping for {interval_hours} hour(s)...")
                await asyncio.sleep(interval_hours * 3600)
                
            except KeyboardInterrupt:
                logger.info("⏸️ Autonomous mode stopped by user")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in autonomous mode: {e}", exc_info=True)
                await asyncio.sleep(300)
    
    def stop(self):
        """Stop autonomous mode"""
        self.is_running = False
        logger.info("🛑 Stopping autonomous mode...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()