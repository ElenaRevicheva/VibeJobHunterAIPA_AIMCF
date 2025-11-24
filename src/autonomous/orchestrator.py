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
ORCHESTRATOR_VERSION = "4.0_AI_COFOUNDER_FULL_STRATEGIC"
ORCHESTRATOR_BUILD = "2025-11-23_21:36_UTC"
ORCHESTRATOR_COMMIT = "bf5e131"

print("\n" + "💥"*40)
print("🚨 EMERGENCY DEPLOY: FULL AI CO-FOUNDER STRATEGIC CAPABILITIES! 🚨")
print(f"📦 VERSION: {ORCHESTRATOR_VERSION}")
print(f"🎯 BUILD: {ORCHESTRATOR_BUILD} | COMMIT: {ORCHESTRATOR_COMMIT}")
print(f"🧠 ALL 4 CAPABILITIES: Performance + Learning + Strategy + Market")
print("💥"*40 + "\n")

logger.info("💥" * 35)
logger.info("🚨🚨🚨 ORCHESTRATOR MODULE IMPORTING - FULL CAPABILITIES! 🚨🚨🚨")
logger.info(f"📦 VERSION: {ORCHESTRATOR_VERSION}")
logger.info(f"🎯 BUILD: {ORCHESTRATOR_BUILD} | COMMIT: {ORCHESTRATOR_COMMIT}")
logger.info(f"🧠 INCLUDES: LinkedIn CMO v4 with FULL AI Co-Founder capabilities")
logger.info(f"🔥 IF YOU SEE THIS = Railway loaded FRESH orchestrator.py file!")
logger.info("💥" * 35)


class AutonomousOrchestrator:
    """
    🚀 THE BRAIN: Coordinates all autonomous agents
    
    Workflow:
    1. Monitor job boards (every hour)
    2. Filter & score new jobs
    3. Research companies (AI-powered)
    4. Find founder contacts
    5. Generate personalized messages
    6. Send via multiple channels
    7. Track responses & demo clicks
    8. Schedule interviews automatically
    9. Follow up intelligently
    """
    
    def __init__(self, profile: Profile, telegram_enabled: bool = True):
        # 🔥🔥🔥 DEPLOYMENT TEST v3.0 - If you see this, Railway deployed latest code! 🔥🔥🔥
        logger.info("=" * 80)
        logger.info("🎨🚀 VIBEJOBHUNTER ORCHESTRATOR v3.0 - LINKEDIN CMO EDITION 🚀🎨")
        logger.info("🔥 GIT COMMIT: 324436a | 📅 BUILD: Nov 23, 2025")
        logger.info("✨ NEW FEATURE: LinkedIn CMO with ASCII Art Banner! ✨")
        logger.info("=" * 80)
        
        self.profile = profile
        self.last_linkedin_post_date = None  # Track last posting date to prevent duplicates
        
        # Initialize Telegram notifier (job search notifications)
        from ..notifications import TelegramNotifier
        self.telegram = TelegramNotifier()
        
        # Initialize LinkedIn CMO (separate from job search)
        logger.info("🔍 Attempting to load LinkedIn CMO...")
        try:
            from ..notifications import LinkedInCMO
            logger.info("✅ LinkedInCMO class imported successfully")
            self.linkedin_cmo = LinkedInCMO()
            logger.info("✅ LinkedInCMO initialized successfully")
        except Exception as e:
            logger.error(f"❌❌❌ LINKEDIN CMO FAILED TO LOAD: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            self.linkedin_cmo = None
        
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
            logger.info("🔍 [1/7] Monitoring job boards...")
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
            logger.info("🎯 [2/7] Filtering & scoring jobs...")
            top_jobs = await self._filter_and_score(new_jobs)
            logger.info(f"✅ {len(top_jobs)} high-priority jobs identified")
            
            # Notify about hot jobs (score >85)
            for job in top_jobs:
                if job.match_score >= 85:
                    await self.telegram.notify_hot_job(job)
            
            # STEP 3: Research companies (parallel)
            logger.info("🔬 [3/7] Researching companies...")
            company_intel = await self._research_companies_parallel(top_jobs)
            logger.info(f"✅ Researched {len(company_intel)} companies")
            self.stats['companies_researched'] += len(company_intel)
            
            # STEP 4: Find founders
            logger.info("👤 [4/7] Finding founder contacts...")
            founder_contacts = await self._find_founders(company_intel)
            logger.info(f"✅ Found {len(founder_contacts)} founder contacts")
            
            # STEP 5: Generate personalized messages
            logger.info("✍️ [5/7] Generating personalized outreach...")
            messages = await self._generate_messages(founder_contacts, company_intel)
            logger.info(f"✅ Generated {len(messages)} personalized messages")
            
            # STEP 6: Send via multiple channels
            logger.info("📤 [6/7] Sending multi-channel outreach...")
            sent_results = await self._send_messages(messages)
            logger.info(f"✅ Sent {sent_results['total_sent']} messages")
            self.stats['messages_sent'] += sent_results['total_sent']
            
            # STEP 7: Handle responses & follow-ups
            logger.info("📧 [7/7] Checking responses & scheduling follow-ups...")
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
            # Notify about errors
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
                # Score the job (note: profile comes FIRST, then job, and it's NOT async)
                score, reasons = matcher.calculate_match_score(self.profile, job)
                job.match_score = score
                job.match_reasons = reasons
                
                # Check criteria
                criteria_match = criteria_matcher.evaluate_job(job)
                job.criteria_match = criteria_match
                
                # Check red flags
                has_flags, red_flags = red_flag_detector.scan_job(job)
                job.red_flags = red_flags
                
                # Only keep decent-scoring jobs without major red flags (lowered to 60 for more matches!)
                if score >= 60 and not any('MAJOR' in flag for flag in red_flags):
                    scored_jobs.append(job)
            
            except Exception as e:
                logger.debug(f"Failed to score job {job.title} at {job.company}: {e}")
                # Skip jobs that fail scoring
                continue
        
        # Sort by score
        scored_jobs.sort(key=lambda x: x.match_score, reverse=True)
        
        # Return top 10
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
                # Generate multi-channel messages
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
                
                # Track results
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
        """
        Check if it's time to post to LinkedIn
        
        Posts DAILY at 3 PM Panama time (UTC-5)
        Railway runs in UTC, so we post at 20:00 UTC = 3:00 PM Panama
        
        Alternates EN/ES by day:
        - Even days (Mon/Wed/Fri/Sun) = English + image_1.png
        - Odd days (Tue/Thu/Sat) = Spanish + image_1.1.png
        """
        if not self.linkedin_cmo or not self.linkedin_cmo.enabled:
            return
        
        now = datetime.now()
        today = now.date()
        day_name = now.strftime("%A")
        day_number = now.weekday()  # Monday=0, Sunday=6
        hour = now.hour
        minute = now.minute
        
        # Check if already posted today
        if self.last_linkedin_post_date == today:
            logger.debug(f"⏭️ LinkedIn CMO: Already posted today ({today}), skipping")
            return
        
        # Post EVERY DAY at 20:00 UTC = 3:00 PM Panama time (UTC-5)
        # Allow posting during 20:00-20:59 window (in case we miss exact minute)
        if hour == 20:
            # Alternate language by day number
            # Even days (0,2,4,6) = EN, Odd days (1,3,5) = ES
            language = "en" if day_number % 2 == 0 else "es"
            image_name = "image_1.png" if language == "en" else "image_1.1.png"
            
            logger.info(f"📱 LinkedIn CMO: DAILY POST TRIGGERED! 🚀")
            logger.info(f"📅 Date: {today} ({day_name})")
            logger.info(f"🕐 Time: {hour:02d}:{minute:02d} UTC (3 PM Panama)")
            logger.info(f"🌍 Language: {language.upper()}")
            logger.info(f"🖼️ Image: {image_name}")
            
            await self.linkedin_cmo.post_to_linkedin(
                post_type="random",
                language=language
            )
            
            # Mark as posted today
            self.last_linkedin_post_date = today
            logger.info(f"✅ LinkedIn post completed! Next post: tomorrow at 20:00 UTC (3 PM Panama)")
    
    async def start_autonomous_mode(self, interval_hours: int = 1):
        """
        🚀 START AUTONOMOUS MODE
        
        Runs continuously, executing cycles every N hours
        """
        self.is_running = True
        logger.info(f"🚀 AUTONOMOUS MODE STARTED (running every {interval_hours} hour(s))")
        
        # Send startup notification and start polling (now that event loop is running!)
        if self.telegram.enabled:
            await self.telegram.notify_startup_success()
            # Start polling in background for Railway logs
            import asyncio as aio
            aio.create_task(self.telegram.start_polling())
        
        # Schedule daily summary at 8pm
        from datetime import datetime, time as dt_time
        
        async def send_daily_summary_at_8pm():
            """Send daily summary at 8pm"""
            while self.is_running:
                now = datetime.now()
                target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
                
                # If past 8pm today, schedule for tomorrow
                if now.hour >= 20:
                    target_time += timedelta(days=1)
                
                # Sleep until 8pm
                wait_seconds = (target_time - now).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                # Send summary
                await self.telegram.send_daily_summary(self.stats)
                
                # Wait a bit to avoid sending again immediately
                await asyncio.sleep(60)
        
        # Start daily summary task
        asyncio.create_task(send_daily_summary_at_8pm())
        
        # Start separate LinkedIn posting check (runs every 10 minutes)
        async def check_linkedin_frequently():
            """Check LinkedIn schedule every 10 minutes to never miss posting window"""
            while self.is_running:
                await self.check_linkedin_schedule()
                await asyncio.sleep(10 * 60)  # Check every 10 minutes
        
        asyncio.create_task(check_linkedin_frequently())
        logger.info("🕒 LinkedIn posting check: Every 10 minutes (catches 20:00 UTC window)")
        
        while self.is_running:
            try:
                # Run one cycle
                await self.run_autonomous_cycle()
                
                # Wait for next cycle
                logger.info(f"😴 Sleeping for {interval_hours} hour(s)...")
                await asyncio.sleep(interval_hours * 3600)
                
            except KeyboardInterrupt:
                logger.info("⏸️ Autonomous mode stopped by user")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ Error in autonomous mode: {e}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop autonomous mode"""
        self.is_running = False
        logger.info("🛑 Stopping autonomous mode...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()
