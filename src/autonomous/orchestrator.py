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
        self.profile = profile
        
        # Initialize Telegram notifier
        from ..notifications import TelegramNotifier
        self.telegram = TelegramNotifier()
        
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
        
        # Send startup notification and start polling
        if self.telegram.enabled:
            async def startup_tasks():
                await self.telegram.notify_startup_success()
                # Start polling in background for Railway logs
                asyncio.create_task(self.telegram.start_polling())
            
            asyncio.create_task(startup_tasks())
    
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
                from datetime import datetime
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
        
        matcher = JobMatcher(self.profile)
        criteria_matcher = CriteriaMatcher()
        red_flag_detector = RedFlagDetector()
        
        scored_jobs = []
        for job in jobs:
            # Score the job
            score, reasons = await matcher.calculate_match_score(job, self.profile)
            job.match_score = score
            job.match_reasons = reasons
            
            # Check criteria
            criteria_match = criteria_matcher.evaluate_job(job)
            job.criteria_match = criteria_match
            
            # Check red flags
            red_flags = red_flag_detector.detect_red_flags(job)
            job.red_flags = red_flags
            
            # Only keep high-scoring jobs without major red flags
            if score >= 70 and not any('MAJOR' in flag for flag in red_flags):
                scored_jobs.append(job)
        
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
    
    async def start_autonomous_mode(self, interval_hours: int = 1):
        """
        🚀 START AUTONOMOUS MODE
        
        Runs continuously, executing cycles every N hours
        """
        self.is_running = True
        logger.info(f"🚀 AUTONOMOUS MODE STARTED (running every {interval_hours} hour(s))")
        
        # Schedule daily summary at 8pm
        import asyncio
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
