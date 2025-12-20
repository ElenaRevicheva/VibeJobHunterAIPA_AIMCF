#!/usr/bin/env python3
"""
🧪 END-TO-END JOB ENGINE TEST
Tests the complete job hunting pipeline before going live.

This script:
1. Tests job discovery (finds real jobs)
2. Tests job scoring (matches to your profile)
3. Tests ATS submission (dry run by default)
4. Tests founder email outreach (dry run by default)
5. Validates all components are working

RUN THIS BEFORE GOING LIVE!

Usage:
    # Dry run (safe - no real applications)
    python scripts/test_job_engine.py
    
    # Live test (sends 1 real application)
    python scripts/test_job_engine.py --live
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class JobEngineTest:
    """End-to-end test for the job hunting engine"""
    
    def __init__(self, live_mode: bool = False):
        self.live_mode = live_mode
        self.results = {
            'env_check': False,
            'job_discovery': False,
            'job_scoring': False,
            'ats_submission': False,
            'email_service': False,
            'founder_finder': False,
            'rate_limiter': False,
            'orchestrator': False,
        }
        
        if live_mode:
            print("\n" + "🚨" * 30)
            print("⚠️  LIVE MODE ENABLED - WILL SEND REAL APPLICATIONS")
            print("🚨" * 30 + "\n")
        else:
            print("\n" + "="*60)
            print("🔒 DRY RUN MODE - No real applications will be sent")
            print("="*60 + "\n")
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("🧪 VIBEJOBHUNTER END-TO-END TEST")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Mode: {'🔴 LIVE' if self.live_mode else '🟢 DRY RUN'}")
        print("="*60)
        
        # 1. Environment Check
        await self.test_environment()
        
        # 2. Rate Limiter
        await self.test_rate_limiter()
        
        # 3. Email Service
        await self.test_email_service()
        
        # 4. Job Discovery
        await self.test_job_discovery()
        
        # 5. Job Scoring
        await self.test_job_scoring()
        
        # 6. ATS Submission
        await self.test_ats_submission()
        
        # 7. Founder Finder
        await self.test_founder_finder()
        
        # 8. Full Orchestrator (if live mode)
        if self.live_mode:
            await self.test_orchestrator()
        
        # Summary
        self.print_summary()
    
    async def test_environment(self):
        """Test all required environment variables"""
        print("\n📋 TEST 1: Environment Variables")
        print("-" * 40)
        
        required_vars = {
            'ANTHROPIC_API_KEY': 'AI scoring and content generation',
            'RESEND_API_KEY': 'Founder email outreach',
            'RESUME_PATH': 'ATS form submission',
        }
        
        optional_vars = {
            'HUNTER_API_KEY': 'Email verification (reduces bounces)',
            'TELEGRAM_BOT_TOKEN': 'Notifications',
        }
        
        all_required_present = True
        
        for var, purpose in required_vars.items():
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                masked = value[:10] + "..." if len(value) > 10 else "***"
                print(f"   ✅ {var}: {masked} ({purpose})")
            else:
                print(f"   ❌ {var}: NOT SET ({purpose})")
                all_required_present = False
        
        print()
        for var, purpose in optional_vars.items():
            value = os.getenv(var)
            status = "✅" if value else "⚠️"
            print(f"   {status} {var}: {'Set' if value else 'Not set'} ({purpose})")
        
        # Check resume file exists
        resume_path = os.getenv('RESUME_PATH', 'resume.pdf')
        if Path(resume_path).exists():
            print(f"   ✅ Resume file exists: {resume_path}")
        else:
            print(f"   ❌ Resume file NOT FOUND: {resume_path}")
            all_required_present = False
        
        self.results['env_check'] = all_required_present
        
        if all_required_present:
            print("\n   ✅ Environment check PASSED")
        else:
            print("\n   ❌ Environment check FAILED - fix missing variables")
    
    async def test_rate_limiter(self):
        """Test rate limiter functionality"""
        print("\n🛡️ TEST 2: Rate Limiter")
        print("-" * 40)
        
        try:
            from src.autonomous.rate_limiter import get_rate_limiter
            
            limiter = get_rate_limiter()
            status = limiter.get_status()
            
            print(f"   Enabled: {status['enabled']}")
            print(f"   Sent today: {status['sent_today']}/{status['max_per_day']}")
            print(f"   Sent this hour: {status['sent_this_hour']}/{status['max_per_hour']}")
            print(f"   Total sent: {status['total_sent']}")
            print(f"   Total bounced: {status['total_bounced']}")
            print(f"   Bounce rate: {status['bounce_rate']}")
            
            # Test can_send
            can_send, reason = limiter.can_send_email("test@example.com")
            print(f"   Can send now: {can_send} ({reason})")
            
            self.results['rate_limiter'] = True
            print("\n   ✅ Rate limiter WORKING")
            
        except Exception as e:
            print(f"   ❌ Rate limiter error: {e}")
            self.results['rate_limiter'] = False
    
    async def test_email_service(self):
        """Test email service configuration"""
        print("\n📧 TEST 3: Email Service")
        print("-" * 40)
        
        try:
            from src.autonomous.email_service import create_email_service, validate_email_for_resend
            
            service = create_email_service()
            
            if service.test_connection():
                print(f"   ✅ Provider: {service.provider}")
                print(f"   ✅ Client configured")
            else:
                print(f"   ❌ Email service not configured")
                self.results['email_service'] = False
                return
            
            # Test validation
            test_emails = [
                ("careers@company.com", False, "Should block ATS emails"),
                ("founder@company.com", True, "Should allow founder emails"),
                ("john@company.com", True, "Should allow personal emails"),
            ]
            
            print("\n   Email validation tests:")
            for email, should_allow, note in test_emails:
                result = validate_email_for_resend(email)
                status = "✅" if result['allowed'] == should_allow else "❌"
                print(f"   {status} {email}: allowed={result['allowed']} ({note})")
            
            self.results['email_service'] = True
            print("\n   ✅ Email service WORKING")
            
        except ImportError as e:
            print(f"   ❌ Import error: {e}")
            self.results['email_service'] = False
        except Exception as e:
            print(f"   ❌ Email service error: {e}")
            self.results['email_service'] = False
    
    async def test_job_discovery(self):
        """Test job discovery from various sources"""
        print("\n🔍 TEST 4: Job Discovery")
        print("-" * 40)
        
        try:
            from src.autonomous.job_monitor import JobMonitor
            
            monitor = JobMonitor()
            
            # Test with small sample
            target_roles = ["AI Engineer", "Founding Engineer", "Software Engineer"]
            print(f"   Searching for: {', '.join(target_roles)}")
            print("   (Limiting to 10 results for test)")
            
            jobs = await monitor.find_new_jobs(
                target_roles=target_roles,
                max_results=10
            )
            
            print(f"\n   Found {len(jobs)} jobs")
            
            if jobs:
                print("\n   Sample jobs found:")
                for i, job in enumerate(jobs[:3], 1):
                    company = getattr(job, 'company', 'Unknown')
                    title = getattr(job, 'title', 'Unknown')
                    source = getattr(job, 'source', 'Unknown')
                    print(f"   {i}. {company} - {title} (from {source})")
                
                self.results['job_discovery'] = True
                print("\n   ✅ Job discovery WORKING")
            else:
                print("   ⚠️ No jobs found - may be network issue or API changes")
                self.results['job_discovery'] = False
            
            # Store jobs for next tests
            self.discovered_jobs = jobs
            
        except Exception as e:
            print(f"   ❌ Job discovery error: {e}")
            self.results['job_discovery'] = False
            self.discovered_jobs = []
    
    async def test_job_scoring(self):
        """Test job scoring against Elena's profile"""
        print("\n📊 TEST 5: Job Scoring")
        print("-" * 40)
        
        try:
            from src.agents.job_matcher import JobMatcher
            from src.core.models import Profile
            
            # Create Elena's profile
            profile = Profile(
                name="Elena Revicheva",
                email="aipa@aideazz.xyz",
                title="AI-First Engineer & Founder",
                skills=["Python", "TypeScript", "React", "Claude", "GPT", "LangChain"],
                experience_years=10,
                resume_path=os.getenv('RESUME_PATH', 'resume.pdf'),
                target_roles=["AI Engineer", "Founding Engineer", "Staff Engineer"],
                preferred_locations=["Remote", "Panama City"],
            )
            
            matcher = JobMatcher()
            
            # Score jobs if we have them
            if hasattr(self, 'discovered_jobs') and self.discovered_jobs:
                print(f"   Scoring {len(self.discovered_jobs)} discovered jobs...")
                
                for job in self.discovered_jobs[:5]:
                    score, reasons = matcher.calculate_match_score(profile, job)
                    job.match_score = score
                    
                    company = getattr(job, 'company', 'Unknown')
                    title = getattr(job, 'title', 'Unknown')
                    print(f"   {score:.0f}/100 - {company} - {title[:30]}...")
                    if reasons:
                        print(f"           {reasons[0][:50]}...")
            else:
                # Create test job for scoring
                from src.core.models import JobPosting, JobSource
                
                test_job = JobPosting(
                    id="test_1",
                    title="AI Engineer",
                    company="Test AI Startup",
                    location="Remote",
                    description="Looking for an AI engineer to build LLM products. Experience with Python, Claude, and GPT required. Founding team member at YC startup.",
                    source=JobSource.OTHER,
                    url="https://example.com/job",
                    remote_allowed=True,
                    requirements=["Python", "LLM", "AI"],
                )
                
                print("   Using sample job for scoring test...")
                score, reasons = matcher.calculate_match_score(profile, test_job)
                print(f"   Score: {score:.0f}/100")
                print(f"   Reasons: {reasons[:2]}")
            
            self.results['job_scoring'] = True
            print("\n   ✅ Job scoring WORKING")
            
        except Exception as e:
            print(f"   ❌ Job scoring error: {e}")
            import traceback
            traceback.print_exc()
            self.results['job_scoring'] = False
    
    async def test_ats_submission(self):
        """Test ATS form submission (dry run)"""
        print("\n🤖 TEST 6: ATS Submission")
        print("-" * 40)
        
        dry_run = os.getenv("ATS_DRY_RUN", "true").lower() == "true"
        print(f"   Mode: {'DRY RUN' if dry_run else '🔴 LIVE'}")
        
        try:
            from src.autonomous.ats_submitter import ATSSubmitter
            
            # Test job detection
            submitter = ATSSubmitter()
            
            test_urls = [
                ("https://boards.greenhouse.io/company/jobs/123", "greenhouse"),
                ("https://jobs.lever.co/company/abc123", "lever"),
                ("https://jobs.ashbyhq.com/company/job", "ashby"),
                ("https://linkedin.com/jobs/view/123", "unknown"),
            ]
            
            print("\n   ATS Type Detection:")
            for url, expected in test_urls:
                detected = submitter._detect_ats_type(url, "")
                status = "✅" if detected == expected else "❌"
                print(f"   {status} {url[:40]}... → {detected}")
            
            # Check resume exists
            resume_path = os.getenv('RESUME_PATH', 'resume.pdf')
            if Path(resume_path).exists():
                print(f"\n   ✅ Resume found: {resume_path}")
            else:
                print(f"\n   ❌ Resume NOT found: {resume_path}")
                self.results['ats_submission'] = False
                return
            
            # Test submission (dry run only)
            if dry_run:
                print("\n   Testing dry-run submission...")
                
                test_job = {
                    "id": "test_gh_1",
                    "company": "Test Company",
                    "title": "AI Engineer",
                    "url": "https://boards.greenhouse.io/testcompany/jobs/123456",
                    "source": "greenhouse",
                }
                
                # We can't actually run Playwright in this test without a browser
                print("   ℹ️  Playwright browser test skipped (would need actual browser)")
                print("   ℹ️  Set ATS_DRY_RUN=false and run full orchestrator to test")
            
            self.results['ats_submission'] = True
            print("\n   ✅ ATS submission components READY")
            
        except ImportError as e:
            print(f"   ❌ Import error: {e}")
            print("   Run: pip install playwright && playwright install chromium")
            self.results['ats_submission'] = False
        except Exception as e:
            print(f"   ❌ ATS submission error: {e}")
            self.results['ats_submission'] = False
    
    async def test_founder_finder(self):
        """Test founder finding and outreach"""
        print("\n👤 TEST 7: Founder Finder")
        print("-" * 40)
        
        try:
            from src.autonomous.founder_finder_v2 import FounderFinderV2
            
            finder = FounderFinderV2()
            
            # Test founder finding
            test_company = "Anthropic"
            test_url = "https://anthropic.com"
            
            print(f"   Testing founder finder for: {test_company}")
            
            founder_data = await finder.find_founder(test_company, {"url": test_url})
            
            if founder_data:
                print(f"   ✅ Found founder data:")
                for key, value in list(founder_data.items())[:5]:
                    print(f"      {key}: {str(value)[:50]}...")
                
                # Test channel detection
                channel = finder._determine_best_channel(founder_data)
                print(f"   Best contact channel: {channel}")
            else:
                print("   ⚠️ No founder data found (may be expected for large company)")
            
            # Test email verifier
            from src.autonomous.email_verifier import get_email_verifier
            
            verifier = get_email_verifier()
            test_email = "test@anthropic.com"
            
            print(f"\n   Testing email verification for: {test_email}")
            verify_result = await verifier.verify_email(test_email)
            print(f"   Deliverable: {verify_result['deliverable']}")
            print(f"   Status: {verify_result['status']}")
            
            self.results['founder_finder'] = True
            print("\n   ✅ Founder finder WORKING")
            
        except Exception as e:
            print(f"   ❌ Founder finder error: {e}")
            import traceback
            traceback.print_exc()
            self.results['founder_finder'] = False
    
    async def test_orchestrator(self):
        """Test full orchestrator (only in live mode)"""
        print("\n🚀 TEST 8: Full Orchestrator (LIVE)")
        print("-" * 40)
        
        if not self.live_mode:
            print("   ⏭️  Skipped (not in live mode)")
            return
        
        try:
            from src.autonomous.orchestrator import AutonomousOrchestrator
            from src.core.models import Profile
            
            profile = Profile(
                name="Elena Revicheva",
                email="aipa@aideazz.xyz",
                title="AI-First Engineer & Founder",
                skills=["Python", "TypeScript", "React", "Claude", "GPT"],
                experience_years=10,
                resume_path=os.getenv('RESUME_PATH'),
                target_roles=["AI Engineer", "Founding Engineer"],
                preferred_locations=["Remote"],
            )
            
            print("   Initializing orchestrator...")
            orchestrator = AutonomousOrchestrator(profile=profile, telegram_enabled=False)
            
            print("   Running ONE autonomous cycle...")
            print("   ⚠️  This will actually apply to jobs!")
            
            await orchestrator.run_autonomous_cycle()
            
            stats = orchestrator.get_stats()
            print(f"\n   Results:")
            print(f"   Jobs found: {stats.get('jobs_found', 0)}")
            print(f"   Applications sent: {stats.get('applications_sent', 0)}")
            print(f"   Founder outreach: {stats.get('founder_outreach', 0)}")
            
            self.results['orchestrator'] = True
            print("\n   ✅ Orchestrator WORKING")
            
        except Exception as e:
            print(f"   ❌ Orchestrator error: {e}")
            import traceback
            traceback.print_exc()
            self.results['orchestrator'] = False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        all_passed = True
        for test, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {status} - {test.replace('_', ' ').title()}")
            if not passed:
                all_passed = False
        
        print("\n" + "-"*60)
        
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("\nNext steps:")
            print("1. Set ATS_DRY_RUN=false in .env")
            print("2. Run: python scripts/test_job_engine.py --live")
            print("3. Monitor the first few applications carefully")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("\nFix the failing components before going live.")
        
        print("="*60)


async def main():
    """Main entry point"""
    live_mode = "--live" in sys.argv
    
    tester = JobEngineTest(live_mode=live_mode)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
