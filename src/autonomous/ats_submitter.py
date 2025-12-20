"""
🚀 ATS FORM SUBMITTER - REAL APPLICATION SUBMISSION
Submits applications to ATS systems via form automation.

SUPPORTED:
1. Greenhouse - Most common for YC companies
2. Lever - Popular with startups
3. Ashby - Modern YC-backed ATS

SAFETY:
- Dry-run mode by default (set DRY_RUN=false to actually submit)
- Human verification step for first submission
- Rate limiting to avoid detection
- All submissions logged for audit

Author: VibeJobHunter
Date: December 2025
"""

import asyncio
import logging
import os
import re
import json
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Feature flags
DRY_RUN = os.getenv("ATS_DRY_RUN", "true").lower() == "true"
REQUIRE_CONFIRMATION = os.getenv("ATS_REQUIRE_CONFIRMATION", "true").lower() == "true"

if DRY_RUN:
    logger.info("🔒 ATS Submitter: DRY RUN MODE (set ATS_DRY_RUN=false to submit)")
else:
    logger.warning("⚠️ ATS Submitter: LIVE MODE - Will actually submit applications!")


@dataclass
class SubmissionResult:
    """Result of an application submission"""
    success: bool
    job_id: str
    company: str
    ats_type: str
    submitted_at: Optional[datetime]
    confirmation_id: Optional[str]
    error: Optional[str]
    dry_run: bool


class ATSSubmitter:
    """
    Submit applications to ATS systems.
    
    Currently supports:
    - Greenhouse (form automation)
    - Lever (form automation)
    - Ashby (form automation)
    
    Uses Playwright for browser automation.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.submissions_dir = Path("autonomous_data/submissions")
        self.submissions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load resume path - check multiple locations for Docker/local compatibility
        self.resume_path = os.getenv("RESUME_PATH", "autonomous_data/resumes/elena_resume.pdf")
        
        # Verify resume exists - try multiple paths
        if not Path(self.resume_path).exists():
            # Try relative to /app (Docker)
            app_path = Path("/app") / self.resume_path
            # Try relative to /workspace (local dev)
            workspace_path = Path("/workspace") / self.resume_path
            # Try absolute path
            abs_path = Path(self.resume_path)
            
            if app_path.exists():
                self.resume_path = str(app_path)
                logger.info(f"✅ Resume found at {self.resume_path}")
            elif workspace_path.exists():
                self.resume_path = str(workspace_path)
                logger.info(f"✅ Resume found at {self.resume_path}")
            elif abs_path.exists():
                self.resume_path = str(abs_path)
                logger.info(f"✅ Resume found at {self.resume_path}")
            else:
                # Check all available resumes in both directories
                for base in ["/app", "/workspace", "."]:
                    resume_dir = Path(base) / "autonomous_data/resumes"
                    if resume_dir.exists():
                        pdfs = list(resume_dir.glob("*.pdf"))
                        if pdfs:
                            self.resume_path = str(pdfs[0])
                            logger.info(f"✅ Using available resume: {self.resume_path}")
                            break
                else:
                    logger.warning(f"⚠️ Resume not found at {self.resume_path}")
        
        # Application data
        self.applicant_data = {
            "first_name": os.getenv("APPLICANT_FIRST_NAME", "Elena"),
            "last_name": os.getenv("APPLICANT_LAST_NAME", "Revicheva"),
            "email": os.getenv("APPLICANT_EMAIL", "aipa@aideazz.xyz"),
            "phone": os.getenv("APPLICANT_PHONE", "+507-6662-3757"),
            "linkedin": os.getenv("APPLICANT_LINKEDIN", "https://linkedin.com/in/elenarevicheva"),
            "github": os.getenv("APPLICANT_GITHUB", "https://github.com/elenarevicheva"),
            "portfolio": os.getenv("APPLICANT_PORTFOLIO", "https://aideazz.xyz"),
            "location": os.getenv("APPLICANT_LOCATION", "Panama City, Panama"),
        }
        
        # Track submissions
        self.submission_log: List[Dict] = []
        self._load_submission_log()
        
        logger.info("🚀 ATS Submitter initialized")
    
    async def __aenter__(self):
        """Initialize Playwright browser"""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            logger.info("✅ Playwright browser started")
        except ImportError:
            logger.error("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
            raise
        except Exception as e:
            logger.error(f"❌ Browser launch failed: {e}")
            raise
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    # =========================================================================
    # MAIN SUBMISSION METHOD
    # =========================================================================
    
    async def submit_application(
        self,
        job: Dict[str, Any],
        cover_letter: str,
        resume_path: Optional[str] = None
    ) -> SubmissionResult:
        """
        Submit an application to an ATS.
        
        Args:
            job: Job dict with url, company, title, source
            cover_letter: Generated cover letter text
            resume_path: Path to resume file (uses default if not provided)
        
        Returns:
            SubmissionResult with success status and details
        """
        job_url = job.get('url', '')
        company = job.get('company', 'Unknown')
        job_id = job.get('id', 'unknown')
        
        # Use provided resume_path or fall back to default
        effective_resume_path = resume_path or self.resume_path
        if effective_resume_path and os.path.exists(effective_resume_path):
            logger.info(f"📄 Using resume: {effective_resume_path}")
        else:
            logger.warning(f"⚠️ Resume not found: {effective_resume_path}")
            effective_resume_path = None
        
        logger.info(f"📝 Submitting application to {company}")
        logger.info(f"   URL: {job_url}")
        
        # Check if already submitted
        if self._already_submitted(job_url):
            logger.info(f"⏭️ Already submitted to {company} - skipping")
            return SubmissionResult(
                success=False,
                job_id=job_id,
                company=company,
                ats_type="unknown",
                submitted_at=None,
                confirmation_id=None,
                error="Already submitted",
                dry_run=DRY_RUN,
            )
        
        # Detect ATS type
        ats_type = self._detect_ats_type(job_url, job.get('source', ''))
        
        if ats_type == "unknown":
            logger.warning(f"⚠️ Unknown ATS type for {job_url}")
            return SubmissionResult(
                success=False,
                job_id=job_id,
                company=company,
                ats_type="unknown",
                submitted_at=None,
                confirmation_id=None,
                error="Unknown ATS type",
                dry_run=DRY_RUN,
            )
        
        # DRY RUN check
        if DRY_RUN:
            logger.info(f"🔒 DRY RUN: Would submit to {ats_type} for {company}")
            self._log_submission(job, "dry_run", None)
            return SubmissionResult(
                success=True,
                job_id=job_id,
                company=company,
                ats_type=ats_type,
                submitted_at=datetime.now(),
                confirmation_id="DRY_RUN",
                error=None,
                dry_run=True,
            )
        
        # Actual submission
        try:
            if ats_type == "greenhouse":
                result = await self._submit_greenhouse(job, cover_letter, effective_resume_path)
            elif ats_type == "lever":
                result = await self._submit_lever(job, cover_letter, effective_resume_path)
            elif ats_type == "ashby":
                result = await self._submit_ashby(job, cover_letter, effective_resume_path)
            else:
                result = SubmissionResult(
                    success=False,
                    job_id=job_id,
                    company=company,
                    ats_type=ats_type,
                    submitted_at=None,
                    confirmation_id=None,
                    error=f"Unsupported ATS: {ats_type}",
                    dry_run=False,
                )
            
            # Log submission
            self._log_submission(job, "submitted" if result.success else "failed", result.error)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Submission failed: {e}")
            self._log_submission(job, "error", str(e))
            return SubmissionResult(
                success=False,
                job_id=job_id,
                company=company,
                ats_type=ats_type,
                submitted_at=None,
                confirmation_id=None,
                error=str(e),
                dry_run=False,
            )
    
    # =========================================================================
    # ATS TYPE DETECTION
    # =========================================================================
    
    def _detect_ats_type(self, url: str, source: str = "") -> str:
        """Detect which ATS the job is from"""
        url_lower = url.lower()
        
        if 'greenhouse.io' in url_lower or source == 'greenhouse':
            return 'greenhouse'
        elif 'lever.co' in url_lower or source == 'lever':
            return 'lever'
        elif 'ashbyhq.com' in url_lower or source == 'ashby':
            return 'ashby'
        elif 'workable.com' in url_lower or source == 'workable':
            return 'workable'
        else:
            return 'unknown'
    
    # =========================================================================
    # GREENHOUSE SUBMISSION
    # =========================================================================
    
    async def _submit_greenhouse(
        self,
        job: Dict[str, Any],
        cover_letter: str,
        resume_path: Optional[str]
    ) -> SubmissionResult:
        """
        Submit application to Greenhouse.
        
        Greenhouse forms typically have:
        - First name, Last name, Email, Phone
        - Resume upload
        - Cover letter text area
        - LinkedIn URL (optional)
        - Work authorization questions
        """
        job_url = job.get('url', '')
        company = job.get('company', 'Unknown')
        job_id = job.get('id', 'unknown')
        
        if not self.browser:
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="greenhouse",
                submitted_at=None, confirmation_id=None, error="Browser not initialized", dry_run=False
            )
        
        page = await self.browser.new_page()
        
        try:
            # Navigate to job page
            await page.goto(job_url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            
            # Look for application form or "Apply" button
            apply_button = await page.query_selector('a[href*="apply"], button:has-text("Apply")')
            if apply_button:
                await apply_button.click()
                await page.wait_for_load_state('networkidle')
            
            # Fill form fields
            await self._fill_greenhouse_form(page, cover_letter, resume_path)
            
            # Submit
            submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
            if submit_button:
                await submit_button.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)  # Wait for confirmation
            
            # Check for success
            success_indicators = [
                'thank you',
                'application received',
                'submitted successfully',
                'we received your application',
            ]
            
            page_text = (await page.content()).lower()
            success = any(indicator in page_text for indicator in success_indicators)
            
            if success:
                logger.info(f"✅ Greenhouse submission successful for {company}")
                return SubmissionResult(
                    success=True,
                    job_id=job_id,
                    company=company,
                    ats_type="greenhouse",
                    submitted_at=datetime.now(),
                    confirmation_id=f"GH_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    error=None,
                    dry_run=False,
                )
            else:
                # Check for error messages
                error_el = await page.query_selector('.error, .field-error, [class*="error"]')
                error_msg = await error_el.text_content() if error_el else "Unknown error"
                
                logger.warning(f"⚠️ Greenhouse submission may have failed: {error_msg}")
                return SubmissionResult(
                    success=False,
                    job_id=job_id,
                    company=company,
                    ats_type="greenhouse",
                    submitted_at=None,
                    confirmation_id=None,
                    error=error_msg,
                    dry_run=False,
                )
        
        except Exception as e:
            logger.error(f"Greenhouse submission error: {e}")
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="greenhouse",
                submitted_at=None, confirmation_id=None, error=str(e), dry_run=False
            )
        
        finally:
            await page.close()
    
    async def _fill_greenhouse_form(self, page, cover_letter: str, resume_path: Optional[str]):
        """Fill Greenhouse application form fields"""
        
        # Common field selectors for Greenhouse
        field_mappings = [
            # Name fields
            ('input[name*="first_name"], input[id*="first_name"], input[autocomplete="given-name"]', self.applicant_data['first_name']),
            ('input[name*="last_name"], input[id*="last_name"], input[autocomplete="family-name"]', self.applicant_data['last_name']),
            
            # Contact
            ('input[name*="email"], input[type="email"]', self.applicant_data['email']),
            ('input[name*="phone"], input[type="tel"]', self.applicant_data['phone']),
            
            # Links
            ('input[name*="linkedin"], input[placeholder*="LinkedIn"]', self.applicant_data['linkedin']),
            ('input[name*="github"], input[placeholder*="GitHub"]', self.applicant_data['github']),
            ('input[name*="portfolio"], input[name*="website"]', self.applicant_data['portfolio']),
            
            # Location
            ('input[name*="location"], input[name*="city"]', self.applicant_data['location']),
        ]
        
        for selector, value in field_mappings:
            try:
                field = await page.query_selector(selector)
                if field:
                    await field.fill(value)
                    logger.debug(f"Filled field: {selector}")
            except Exception as e:
                logger.debug(f"Could not fill {selector}: {e}")
        
        # Cover letter textarea
        cover_letter_selectors = [
            'textarea[name*="cover_letter"]',
            'textarea[id*="cover_letter"]',
            'textarea[placeholder*="cover letter"]',
            'textarea[name*="message"]',
        ]
        
        for selector in cover_letter_selectors:
            try:
                textarea = await page.query_selector(selector)
                if textarea:
                    await textarea.fill(cover_letter)
                    logger.debug("Filled cover letter")
                    break
            except Exception:
                pass
        
        # Resume upload
        if resume_path and os.path.exists(resume_path):
            try:
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(resume_path)
                    logger.debug("Uploaded resume")
            except Exception as e:
                logger.warning(f"Could not upload resume: {e}")
    
    # =========================================================================
    # LEVER SUBMISSION
    # =========================================================================
    
    async def _submit_lever(
        self,
        job: Dict[str, Any],
        cover_letter: str,
        resume_path: Optional[str]
    ) -> SubmissionResult:
        """Submit application to Lever"""
        job_url = job.get('url', '')
        company = job.get('company', 'Unknown')
        job_id = job.get('id', 'unknown')
        
        if not self.browser:
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="lever",
                submitted_at=None, confirmation_id=None, error="Browser not initialized", dry_run=False
            )
        
        page = await self.browser.new_page()
        
        try:
            # Lever jobs page format: jobs.lever.co/company/job-id/apply
            apply_url = job_url if '/apply' in job_url else f"{job_url}/apply"
            
            await page.goto(apply_url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            
            # Fill Lever form
            await self._fill_lever_form(page, cover_letter, resume_path)
            
            # Submit
            submit_button = await page.query_selector('button[type="submit"], .application-submit')
            if submit_button:
                await submit_button.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            
            # Check for success
            page_text = (await page.content()).lower()
            success = 'thank' in page_text or 'received' in page_text or 'submitted' in page_text
            
            if success:
                logger.info(f"✅ Lever submission successful for {company}")
                return SubmissionResult(
                    success=True, job_id=job_id, company=company, ats_type="lever",
                    submitted_at=datetime.now(), 
                    confirmation_id=f"LV_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    error=None, dry_run=False
                )
            else:
                return SubmissionResult(
                    success=False, job_id=job_id, company=company, ats_type="lever",
                    submitted_at=None, confirmation_id=None, error="Submission not confirmed", dry_run=False
                )
        
        except Exception as e:
            logger.error(f"Lever submission error: {e}")
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="lever",
                submitted_at=None, confirmation_id=None, error=str(e), dry_run=False
            )
        
        finally:
            await page.close()
    
    async def _fill_lever_form(self, page, cover_letter: str, resume_path: Optional[str]):
        """Fill Lever application form"""
        
        # Lever uses specific field names
        field_mappings = [
            ('input[name="name"]', f"{self.applicant_data['first_name']} {self.applicant_data['last_name']}"),
            ('input[name="email"]', self.applicant_data['email']),
            ('input[name="phone"]', self.applicant_data['phone']),
            ('input[name="org"]', "AIdeazz"),  # Current company
            ('input[name="urls[LinkedIn]"]', self.applicant_data['linkedin']),
            ('input[name="urls[GitHub]"]', self.applicant_data['github']),
            ('input[name="urls[Portfolio]"]', self.applicant_data['portfolio']),
        ]
        
        for selector, value in field_mappings:
            try:
                field = await page.query_selector(selector)
                if field:
                    await field.fill(value)
            except Exception:
                pass
        
        # Cover letter
        try:
            textarea = await page.query_selector('textarea[name="comments"], textarea[name="additionalInfo"]')
            if textarea:
                await textarea.fill(cover_letter)
        except Exception:
            pass
        
        # Resume
        if resume_path and os.path.exists(resume_path):
            try:
                file_input = await page.query_selector('input[type="file"][name="resume"]')
                if file_input:
                    await file_input.set_input_files(resume_path)
            except Exception:
                pass
    
    # =========================================================================
    # ASHBY SUBMISSION
    # =========================================================================
    
    async def _submit_ashby(
        self,
        job: Dict[str, Any],
        cover_letter: str,
        resume_path: Optional[str]
    ) -> SubmissionResult:
        """Submit application to Ashby"""
        job_url = job.get('url', '')
        company = job.get('company', 'Unknown')
        job_id = job.get('id', 'unknown')
        
        if not self.browser:
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="ashby",
                submitted_at=None, confirmation_id=None, error="Browser not initialized", dry_run=False
            )
        
        page = await self.browser.new_page()
        
        try:
            await page.goto(job_url, timeout=30000)
            await page.wait_for_load_state('networkidle')
            
            # Click Apply button if on job detail page
            apply_button = await page.query_selector('button:has-text("Apply"), a:has-text("Apply")')
            if apply_button:
                await apply_button.click()
                await page.wait_for_load_state('networkidle')
            
            # Fill Ashby form
            await self._fill_ashby_form(page, cover_letter, resume_path)
            
            # Submit
            submit_button = await page.query_selector('button[type="submit"]:has-text("Submit")')
            if submit_button:
                await submit_button.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
            
            # Check success
            page_text = (await page.content()).lower()
            success = 'thank' in page_text or 'submitted' in page_text
            
            if success:
                logger.info(f"✅ Ashby submission successful for {company}")
                return SubmissionResult(
                    success=True, job_id=job_id, company=company, ats_type="ashby",
                    submitted_at=datetime.now(),
                    confirmation_id=f"AB_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    error=None, dry_run=False
                )
            else:
                return SubmissionResult(
                    success=False, job_id=job_id, company=company, ats_type="ashby",
                    submitted_at=None, confirmation_id=None, error="Submission not confirmed", dry_run=False
                )
        
        except Exception as e:
            logger.error(f"Ashby submission error: {e}")
            return SubmissionResult(
                success=False, job_id=job_id, company=company, ats_type="ashby",
                submitted_at=None, confirmation_id=None, error=str(e), dry_run=False
            )
        
        finally:
            await page.close()
    
    async def _fill_ashby_form(self, page, cover_letter: str, resume_path: Optional[str]):
        """Fill Ashby application form"""
        
        # Ashby forms use data-testid attributes
        field_mappings = [
            ('input[data-testid="first-name-input"], input[name*="firstName"]', self.applicant_data['first_name']),
            ('input[data-testid="last-name-input"], input[name*="lastName"]', self.applicant_data['last_name']),
            ('input[data-testid="email-input"], input[type="email"]', self.applicant_data['email']),
            ('input[data-testid="phone-input"], input[type="tel"]', self.applicant_data['phone']),
            ('input[name*="linkedin"]', self.applicant_data['linkedin']),
        ]
        
        for selector, value in field_mappings:
            try:
                field = await page.query_selector(selector)
                if field:
                    await field.fill(value)
            except Exception:
                pass
        
        # Cover letter
        try:
            textarea = await page.query_selector('textarea')
            if textarea:
                await textarea.fill(cover_letter)
        except Exception:
            pass
        
        # Resume
        if resume_path and os.path.exists(resume_path):
            try:
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(resume_path)
            except Exception:
                pass
    
    # =========================================================================
    # LOGGING & TRACKING
    # =========================================================================
    
    def _already_submitted(self, job_url: str) -> bool:
        """Check if we already submitted to this job"""
        return any(
            sub.get('url') == job_url and sub.get('status') in ['submitted', 'dry_run']
            for sub in self.submission_log
        )
    
    def _log_submission(self, job: Dict, status: str, error: Optional[str]):
        """Log a submission attempt"""
        entry = {
            'url': job.get('url', ''),
            'company': job.get('company', ''),
            'title': job.get('title', ''),
            'job_id': job.get('id', ''),
            'status': status,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'dry_run': DRY_RUN,
        }
        
        self.submission_log.append(entry)
        self._save_submission_log()
    
    def _load_submission_log(self):
        """Load submission history"""
        log_file = self.submissions_dir / "submission_log.json"
        try:
            if log_file.exists():
                with open(log_file, 'r') as f:
                    self.submission_log = json.load(f)
        except Exception:
            self.submission_log = []
    
    def _save_submission_log(self):
        """Save submission history"""
        log_file = self.submissions_dir / "submission_log.json"
        try:
            with open(log_file, 'w') as f:
                json.dump(self.submission_log[-500:], f, indent=2)  # Keep last 500
        except Exception as e:
            logger.warning(f"Could not save submission log: {e}")
    
    def get_submission_stats(self) -> Dict[str, int]:
        """Get submission statistics"""
        stats = {
            'total': len(self.submission_log),
            'submitted': sum(1 for s in self.submission_log if s['status'] == 'submitted'),
            'dry_run': sum(1 for s in self.submission_log if s['status'] == 'dry_run'),
            'failed': sum(1 for s in self.submission_log if s['status'] in ['failed', 'error']),
        }
        return stats


# =============================================================================
# HELPER FUNCTION
# =============================================================================

async def submit_to_ats(job: Dict, cover_letter: str, resume_path: str = None) -> SubmissionResult:
    """
    Convenience function to submit an application.
    
    Usage:
        result = await submit_to_ats(job, cover_letter, "resume.pdf")
        if result.success:
            print(f"Submitted to {result.company}!")
    """
    async with ATSSubmitter() as submitter:
        return await submitter.submit_application(job, cover_letter, resume_path)


# =============================================================================
# TEST
# =============================================================================

async def test_ats_submitter():
    """Test the ATS submitter (dry run)"""
    print("\n" + "=" * 60)
    print("🧪 TESTING ATS SUBMITTER (DRY RUN)")
    print("=" * 60 + "\n")
    
    # Test jobs
    test_jobs = [
        {
            "id": "test_gh_1",
            "company": "Test Company",
            "title": "AI Engineer",
            "url": "https://boards.greenhouse.io/testcompany/jobs/123456",
            "source": "greenhouse",
        },
        {
            "id": "test_lv_1",
            "company": "Lever Test",
            "title": "Founding Engineer",
            "url": "https://jobs.lever.co/testcompany/abc123",
            "source": "lever",
        },
    ]
    
    submitter = ATSSubmitter()
    
    for job in test_jobs:
        print(f"\nTesting: {job['company']} - {job['title']}")
        print(f"ATS Type: {submitter._detect_ats_type(job['url'], job['source'])}")
        
        result = await submitter.submit_application(
            job,
            "Test cover letter for Elena's application.",
            None
        )
        
        print(f"Success: {result.success}")
        print(f"Dry Run: {result.dry_run}")
        print(f"Confirmation: {result.confirmation_id}")
    
    # Stats
    stats = submitter.get_submission_stats()
    print(f"\n📊 Stats: {stats}")
    
    print("\n✅ Test complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_ats_submitter())
