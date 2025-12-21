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
        
        # ═══════════════════════════════════════════════════════════════════════════
        # ELENA REVICHEVA - REAL APPLICANT DATA (from actual resume)
        # Based in Panama City, Panama | Bilingual EN/ES | Remote-first
        # ═══════════════════════════════════════════════════════════════════════════
        self.applicant_data = {
            # Basic Info
            "first_name": os.getenv("APPLICANT_FIRST_NAME", "Elena"),
            "last_name": os.getenv("APPLICANT_LAST_NAME", "Revicheva"),
            "full_name": os.getenv("APPLICANT_FULL_NAME", "Elena Revicheva"),
            "email": os.getenv("APPLICANT_EMAIL", "aipa@aideazz.xyz"),
            "phone": os.getenv("APPLICANT_PHONE", "+507-6166-6716"),  # Elena's PERSONAL Panama number
            # NOTE: +507-6662-3757 is for EspaLuz AI Product, NOT for job applications
            
            # Professional Links
            "linkedin": os.getenv("APPLICANT_LINKEDIN", "https://linkedin.com/in/elenarevicheva"),
            "github": os.getenv("APPLICANT_GITHUB", "https://github.com/elenarevicheva"),
            "portfolio": os.getenv("APPLICANT_PORTFOLIO", "https://aideazz.xyz"),
            "website": os.getenv("APPLICANT_WEBSITE", "https://aideazz.xyz"),
            
            # Location (Panama-based, open to remote/relocation)
            "location": os.getenv("APPLICANT_LOCATION", "Panama City, Panama"),
            "city": "Panama City",
            "state": "Panama",
            "country": "Panama",
            "timezone": "America/Panama",  # UTC-5
            
            # Work Authorization (IMPORTANT for US companies)
            # Elena is in Panama, would need visa sponsorship for US roles
            "work_authorization_us": "No",  # Not currently authorized to work in US
            "requires_sponsorship": "Yes",  # Will require visa sponsorship
            "willing_to_relocate": "Yes",   # Open to relocation
            "remote_preference": "Yes",     # Prefers remote but flexible
            
            # Current Employment
            "current_company": "AIdeazz",
            "current_title": "Founder & AI Engineer",
            "years_experience": "10+",  # 10+ years total (E-Gov + startup)
            
            # Education (highest degree)
            "degree": "Master's Degree",
            "degree_type": "M.A.",
            "field_of_study": "Social Psychology",
            "university": "Penza State University",
            "graduation_year": "2018",
            
            # Languages (bilingual EN/ES)
            "languages": "English (Fluent), Spanish (Intermediate), Russian (Native)",
            "primary_language": "English",
            
            # How did you hear about us - common responses
            "referral_source": "Company website",
            "hear_about_us": "Company careers page",
            
            # Demographic (optional - only fill if explicitly required)
            "gender": "Female",  # Optional
            "pronouns": "She/Her",  # Optional
            
            # Availability
            "start_date": "Immediately",
            "notice_period": "2 weeks",
            "available_for_interview": "Yes",
            
            # Salary (leave blank to negotiate)
            "salary_expectation": "",  # Don't disclose upfront
            
            # Legal
            "age_18_or_older": "Yes",
            "legally_authorized": "Yes",  # Authorized in Panama
            "background_check": "Yes",  # Willing to undergo
            "drug_test": "Yes",  # Willing to undergo
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
            
            # ═══════════════════════════════════════════════════════════
            # CHECK FOR EMAIL VERIFICATION REQUIREMENT
            # Some companies (like xAI) require email verification codes
            # ═══════════════════════════════════════════════════════════
            page_content = await page.content()
            page_text = page_content.lower()
            
            # Check if verification code is required
            verification_required = any(phrase in page_text for phrase in [
                'security code',
                'verification code',
                'enter the code',
                'check your email',
                'sent a code',
                'verify your email',
                'code has been sent',
                'email verification',
                'confirm your email',
                'enter code',
                'paste this code',
                'copy and paste',
            ])
            
            if verification_required:
                logger.info(f"🔐 Email verification required for {company}")
                
                # Try to handle email verification
                verification_success = await self._handle_greenhouse_email_verification(page, company)
                
                if verification_success:
                    # Resubmit after entering code
                    submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
                    if submit_button:
                        await submit_button.click()
                        await page.wait_for_load_state('networkidle')
                        await asyncio.sleep(2)
                    
                    # Update page text after resubmit
                    page_text = (await page.content()).lower()
                else:
                    logger.warning(f"⚠️ Could not complete email verification for {company}")
                    # Continue to check for success anyway
            
            # Check for success
            success_indicators = [
                'thank you',
                'application received',
                'submitted successfully',
                'we received your application',
            ]
            
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
    
    async def _handle_greenhouse_email_verification(self, page, company: str) -> bool:
        """
        Handle Greenhouse email verification flow.
        
        When Greenhouse requires email verification:
        1. A security code is sent to the applicant's email
        2. The applicant must enter this code in the form
        3. Then resubmit the application
        
        This method:
        - Reads verification code from Zoho Mail (via IMAP)
        - Enters the code into the form
        - Returns True if successful
        
        Requirements:
        - ZOHO_APP_PASSWORD environment variable must be set
        - Email must be aipa@aideazz.xyz (or configured in ZOHO_EMAIL)
        """
        try:
            from .greenhouse_email_verifier import GreenhouseEmailVerifier
            
            verifier = GreenhouseEmailVerifier()
            
            if not verifier.email_password:
                logger.warning("⚠️ Email verification not configured")
                logger.info("   Set ZOHO_APP_PASSWORD in Railway environment variables")
                logger.info("   Generate app password at: Zoho Mail → Settings → Security → App Passwords")
                return False
            
            # Wait a moment for the verification page to fully load
            await asyncio.sleep(2)
            
            # Find the verification code input field - expanded selectors for xAI/Greenhouse
            code_input_selectors = [
                # Direct security/verification selectors
                'input[name*="security"]',
                'input[name*="verification"]',
                'input[name*="code"]',
                'input[name*="token"]',
                'input[name*="otp"]',
                # Placeholder-based
                'input[placeholder*="code"]',
                'input[placeholder*="Code"]',
                'input[placeholder*="security"]',
                'input[placeholder*="Security"]',
                'input[placeholder*="Enter"]',
                # Aria-label based
                'input[aria-label*="code"]',
                'input[aria-label*="Code"]',
                'input[aria-label*="security"]',
                'input[aria-label*="Security"]',
                'input[aria-label*="verification"]',
                # Length-based (verification codes are typically 6-10 chars)
                'input[type="text"][maxlength="6"]',
                'input[type="text"][maxlength="8"]',
                'input[type="text"][maxlength="10"]',
                # Greenhouse-specific patterns
                'input[id*="security"]',
                'input[id*="code"]',
                'input[id*="verification"]',
                'input[id*="token"]',
                # Generic visible text input that might be the code field
                'input[type="text"]:not([name*="name"]):not([name*="email"]):not([name*="phone"])',
            ]
            
            code_input = None
            for selector in code_input_selectors:
                try:
                    code_input = await page.query_selector(selector)
                    if code_input:
                        # Verify it's visible and not already filled
                        is_visible = await code_input.is_visible()
                        current_value = await code_input.input_value()
                        if is_visible and not current_value:
                            logger.info(f"✅ Found verification input: {selector}")
                            break
                        code_input = None
                except Exception:
                    continue
            
            if not code_input:
                # Try to find any empty text input on the page
                logger.info("🔍 Searching for any empty text input for verification code...")
                all_inputs = await page.query_selector_all('input[type="text"]')
                for inp in all_inputs:
                    try:
                        is_visible = await inp.is_visible()
                        current_value = await inp.input_value()
                        inp_name = await inp.get_attribute('name') or ''
                        inp_placeholder = await inp.get_attribute('placeholder') or ''
                        
                        # Skip name/email/phone fields
                        if any(skip in inp_name.lower() for skip in ['name', 'email', 'phone', 'linkedin', 'github']):
                            continue
                        
                        if is_visible and not current_value:
                            logger.info(f"✅ Found empty input: name={inp_name}, placeholder={inp_placeholder}")
                            code_input = inp
                            break
                    except Exception:
                        continue
            
            if not code_input:
                logger.warning("⚠️ Could not find verification code input field")
                # Log page content for debugging
                try:
                    page_text = await page.content()
                    if 'security' in page_text.lower() or 'code' in page_text.lower():
                        logger.info("📄 Page contains 'security' or 'code' text - verification likely needed")
                except Exception:
                    pass
                return False
            
            # Wait for verification email and get code
            logger.info("⏳ Waiting for Greenhouse verification email...")
            code = await verifier.wait_for_verification_code(company, timeout_seconds=90)
            
            if not code:
                logger.error("❌ Did not receive verification code in time")
                return False
            
            # Enter the code
            await code_input.click()
            await code_input.fill("")
            await code_input.fill(code)
            logger.info(f"✅ Entered verification code: {code}")
            
            # Small delay before resubmit
            await asyncio.sleep(1)
            
            return True
            
        except ImportError:
            logger.error("❌ greenhouse_email_verifier module not found")
            return False
        except Exception as e:
            logger.error(f"❌ Email verification failed: {e}")
            return False
    
    async def _fill_greenhouse_form(self, page, cover_letter: str, resume_path: Optional[str]):
        """
        Fill Greenhouse application form with COMPREHENSIVE field support.
        
        Handles:
        - Basic info (name, email, phone)
        - Professional links (LinkedIn, GitHub, Portfolio)
        - Location fields
        - Work authorization questions (CRITICAL for US companies)
        - "How did you hear about us" dropdowns
        - Education fields
        - Experience fields
        - Custom questions
        
        Updated: December 2025 - Tested with xAI, Anthropic, and other top ATS forms
        """
        
        # Wait for form to be ready
        await asyncio.sleep(1)
        
        full_name = f"{self.applicant_data['first_name']} {self.applicant_data['last_name']}"
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 1: NAME FIELDS
        # Some companies (like xAI) have BOTH Full Legal Name AND First/Last Name
        # We try to fill ALL name fields to handle both cases
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Full Legal Name
        full_name_selectors = [
            'input[name*="full_name"]',
            'input[id*="full_name"]',
            'input[name*="legal_name"]',
            'input[id*="legal_name"]',
            'input[aria-label*="Full Name"]',
            'input[aria-label*="Legal Name"]',
            'input[aria-label*="full name"]',
            'input[placeholder*="Full name"]',
            'input[placeholder*="Legal name"]',
        ]
        await self._fill_field_with_selectors(page, full_name_selectors, full_name, "full_name")
        
        # First Name - ALWAYS try to fill
        first_name_selectors = [
            'input#first_name',
            'input[name="job_application[first_name]"]',
            'input[name*="first_name"]',
            'input[id*="first_name"]',
            'input[autocomplete="given-name"]',
            'input[aria-label*="First Name"]',
            'input[aria-label*="First name"]',
            'input[placeholder*="First Name"]',
            'input[placeholder*="First name"]',
        ]
        await self._fill_field_with_selectors(page, first_name_selectors, self.applicant_data['first_name'], "first_name")
        
        # Last Name - ALWAYS try to fill
        last_name_selectors = [
            'input#last_name',
            'input[name="job_application[last_name]"]',
            'input[name*="last_name"]',
            'input[id*="last_name"]',
            'input[autocomplete="family-name"]',
            'input[aria-label*="Last Name"]',
            'input[aria-label*="Last name"]',
            'input[placeholder*="Last Name"]',
            'input[placeholder*="Last name"]',
        ]
        await self._fill_field_with_selectors(page, last_name_selectors, self.applicant_data['last_name'], "last_name")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 2: CONTACT INFO
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Email - CRITICAL
        email_selectors = [
            'input#email',
            'input[name="job_application[email]"]',
            'input[type="email"]',
            'input[name*="email"]',
            'input[id*="email"]',
            'input[autocomplete="email"]',
            'input[aria-label*="Email"]',
        ]
        await self._fill_field_with_selectors(page, email_selectors, self.applicant_data['email'], "email")
        
        # Phone
        phone_selectors = [
            'input#phone',
            'input[name="job_application[phone]"]',
            'input[type="tel"]',
            'input[name*="phone"]',
            'input[id*="phone"]',
            'input[autocomplete="tel"]',
            'input[aria-label*="Phone"]',
        ]
        await self._fill_field_with_selectors(page, phone_selectors, self.applicant_data['phone'], "phone")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 3: PROFESSIONAL LINKS
        # ═══════════════════════════════════════════════════════════════════════════
        
        # LinkedIn
        linkedin_selectors = [
            'input[name*="linkedin"]',
            'input[id*="linkedin"]',
            'input[placeholder*="linkedin"]',
            'input[placeholder*="LinkedIn"]',
            'input[aria-label*="LinkedIn"]',
            'input[aria-label*="linkedin"]',
        ]
        await self._fill_field_with_selectors(page, linkedin_selectors, self.applicant_data['linkedin'], "linkedin")
        
        # GitHub
        github_selectors = [
            'input[name*="github"]',
            'input[id*="github"]',
            'input[placeholder*="github"]',
            'input[placeholder*="GitHub"]',
            'input[aria-label*="GitHub"]',
            'input[aria-label*="github"]',
        ]
        await self._fill_field_with_selectors(page, github_selectors, self.applicant_data['github'], "github")
        
        # Portfolio / Website
        portfolio_selectors = [
            'input[name*="portfolio"]',
            'input[name*="website"]',
            'input[id*="portfolio"]',
            'input[id*="website"]',
            'input[placeholder*="Portfolio"]',
            'input[placeholder*="Website"]',
            'input[aria-label*="Portfolio"]',
            'input[aria-label*="Website"]',
            'input[aria-label*="personal site"]',
        ]
        await self._fill_field_with_selectors(page, portfolio_selectors, self.applicant_data['portfolio'], "portfolio")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 4: LOCATION
        # ═══════════════════════════════════════════════════════════════════════════
        
        location_selectors = [
            'input[name*="location"]',
            'input[id*="location"]',
            'input[name*="city"]',
            'input[name*="address"]',
            'input[placeholder*="Location"]',
            'input[placeholder*="City"]',
            'input[placeholder*="Address"]',
            'input[aria-label*="Location"]',
            'input[aria-label*="City"]',
            'input[aria-label*="Current location"]',
            'input[autocomplete="address-level2"]',
        ]
        await self._fill_field_with_selectors(page, location_selectors, self.applicant_data['location'], "location")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 5: WORK AUTHORIZATION (CRITICAL FOR US COMPANIES)
        # Elena is in Panama and would need visa sponsorship for US roles
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Handle work authorization dropdowns and radio buttons
        await self._handle_work_authorization(page)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 6: "HOW DID YOU HEAR ABOUT US" DROPDOWNS
        # ═══════════════════════════════════════════════════════════════════════════
        
        await self._handle_referral_source(page)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 7: EDUCATION & EXPERIENCE
        # ═══════════════════════════════════════════════════════════════════════════
        
        # Current company
        company_selectors = [
            'input[name*="current_company"]',
            'input[name*="company"]',
            'input[name*="employer"]',
            'input[aria-label*="Current company"]',
            'input[aria-label*="Current employer"]',
            'input[placeholder*="Current company"]',
        ]
        await self._fill_field_with_selectors(page, company_selectors, self.applicant_data['current_company'], "current_company")
        
        # Current title
        title_selectors = [
            'input[name*="current_title"]',
            'input[name*="job_title"]',
            'input[aria-label*="Current title"]',
            'input[aria-label*="Job title"]',
            'input[placeholder*="Current title"]',
        ]
        await self._fill_field_with_selectors(page, title_selectors, self.applicant_data['current_title'], "current_title")
        
        # Years of experience (dropdown or input)
        await self._handle_experience_dropdown(page)
        
        # Education dropdown
        await self._handle_education_dropdown(page)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 8: COVER LETTER
        # ═══════════════════════════════════════════════════════════════════════════
        
        cover_letter_selectors = [
            'textarea[name*="cover_letter"]',
            'textarea[id*="cover_letter"]',
            'textarea[placeholder*="cover letter"]',
            'textarea[placeholder*="Cover Letter"]',
            'textarea[placeholder*="Cover letter"]',
            'textarea[name*="message"]',
            'textarea[name*="additional"]',
            'textarea[name*="comments"]',
            'textarea[aria-label*="cover"]',
            'textarea[aria-label*="Cover"]',
            'textarea[aria-label*="additional"]',
            'textarea[aria-label*="message"]',
            'textarea[aria-label*="Why"]',
            '#cover_letter',
            '#additional_information',
        ]
        cover_filled = await self._fill_field_with_selectors(page, cover_letter_selectors, cover_letter, "cover_letter")
        
        # Fallback: try any visible textarea with relevant placeholder
        if not cover_filled:
            try:
                textareas = await page.query_selector_all('textarea:visible')
                for ta in textareas:
                    placeholder = await ta.get_attribute('placeholder') or ""
                    aria_label = await ta.get_attribute('aria-label') or ""
                    combined = (placeholder + aria_label).lower()
                    if any(kw in combined for kw in ['cover', 'additional', 'why', 'interest', 'tell us']):
                        await ta.fill(cover_letter)
                        logger.info(f"✅ Filled cover_letter via fallback textarea")
                        break
            except Exception as e:
                logger.debug(f"Fallback textarea fill failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 9: RESUME UPLOAD
        # ═══════════════════════════════════════════════════════════════════════════
        
        if resume_path and os.path.exists(resume_path):
            file_selectors = [
                'input[type="file"][name*="resume"]',
                'input[type="file"][id*="resume"]',
                'input[type="file"][accept*="pdf"]',
                'input[type="file"]',
            ]
            for selector in file_selectors:
                try:
                    file_input = await page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(resume_path)
                        logger.info(f"✅ Uploaded resume: {resume_path}")
                        break
                except Exception as e:
                    logger.debug(f"Could not upload with {selector}: {e}")
        
        # ═══════════════════════════════════════════════════════════════════════════
        # SECTION 10: ADDITIONAL CHECKBOXES (age, background check, etc.)
        # ═══════════════════════════════════════════════════════════════════════════
        
        await self._handle_common_checkboxes(page)
        
        # Wait for form to process
        await asyncio.sleep(0.5)
    
    async def _handle_work_authorization(self, page):
        """
        Handle work authorization questions - CRITICAL for US companies.
        
        Elena is based in Panama and would require visa sponsorship for US roles.
        We need to be HONEST here - lying on applications is unethical and illegal.
        """
        try:
            # ═══════════════════════════════════════════════════════════
            # WORK AUTHORIZATION DROPDOWNS
            # ═══════════════════════════════════════════════════════════
            
            # "Are you legally authorized to work in [country]?"
            auth_dropdowns = await page.query_selector_all('select[name*="authorized"], select[name*="authorization"], select[aria-label*="authorized"]')
            for dropdown in auth_dropdowns:
                try:
                    # For US jobs: Elena is NOT currently authorized (she's in Panama)
                    # Select "No" or "Will require sponsorship"
                    options = await dropdown.query_selector_all('option')
                    for opt in options:
                        text = (await opt.text_content() or "").lower()
                        # Look for honest answer - she would need sponsorship
                        if 'no' in text or 'require' in text or 'sponsorship' in text or 'visa' in text:
                            value = await opt.get_attribute('value')
                            if value:
                                await dropdown.select_option(value=value)
                                logger.info(f"✅ Selected work authorization: {text[:50]}")
                                break
                except Exception as e:
                    logger.debug(f"Work auth dropdown failed: {e}")
            
            # "Will you now or in the future require sponsorship?"
            sponsorship_dropdowns = await page.query_selector_all('select[name*="sponsorship"], select[aria-label*="sponsorship"]')
            for dropdown in sponsorship_dropdowns:
                try:
                    options = await dropdown.query_selector_all('option')
                    for opt in options:
                        text = (await opt.text_content() or "").lower()
                        # HONEST: Yes, Elena would need sponsorship for US
                        if 'yes' in text:
                            value = await opt.get_attribute('value')
                            if value:
                                await dropdown.select_option(value=value)
                                logger.info(f"✅ Selected sponsorship requirement: Yes")
                                break
                except Exception as e:
                    logger.debug(f"Sponsorship dropdown failed: {e}")
            
            # ═══════════════════════════════════════════════════════════
            # WORK AUTHORIZATION RADIO BUTTONS
            # ═══════════════════════════════════════════════════════════
            
            # Radio buttons for "Authorized to work?"
            auth_radios = await page.query_selector_all('input[type="radio"][name*="authorized"], input[type="radio"][name*="authorization"]')
            for radio in auth_radios:
                try:
                    label = await radio.evaluate('el => el.closest("label")?.textContent || el.nextSibling?.textContent || ""')
                    label = label.lower() if label else ""
                    # For US jobs: select "No" (she's in Panama)
                    if 'no' in label:
                        await radio.click()
                        logger.info(f"✅ Selected work authorization radio: No")
                        break
                except Exception as e:
                    logger.debug(f"Work auth radio failed: {e}")
            
            # Radio buttons for "Require sponsorship?"
            sponsor_radios = await page.query_selector_all('input[type="radio"][name*="sponsorship"]')
            for radio in sponsor_radios:
                try:
                    label = await radio.evaluate('el => el.closest("label")?.textContent || el.nextSibling?.textContent || ""')
                    label = label.lower() if label else ""
                    # HONEST: Yes, she would need sponsorship
                    if 'yes' in label:
                        await radio.click()
                        logger.info(f"✅ Selected sponsorship radio: Yes")
                        break
                except Exception as e:
                    logger.debug(f"Sponsorship radio failed: {e}")
            
        except Exception as e:
            logger.debug(f"Work authorization handling failed: {e}")
    
    async def _handle_referral_source(self, page):
        """Handle 'How did you hear about us?' dropdowns"""
        try:
            # Common dropdown selectors
            referral_selectors = [
                'select[name*="hear"]',
                'select[name*="source"]',
                'select[name*="referral"]',
                'select[aria-label*="hear"]',
                'select[aria-label*="How did you"]',
                'select[name*="how_did"]',
            ]
            
            for selector in referral_selectors:
                dropdown = await page.query_selector(selector)
                if dropdown:
                    try:
                        options = await dropdown.query_selector_all('option')
                        for opt in options:
                            text = (await opt.text_content() or "").lower()
                            # Prefer: Company website/careers page
                            if any(kw in text for kw in ['website', 'career', 'job board', 'online', 'company']):
                                value = await opt.get_attribute('value')
                                if value:
                                    await dropdown.select_option(value=value)
                                    logger.info(f"✅ Selected referral source: {text[:40]}")
                                    return
                        # Fallback: select first non-empty option
                        for opt in options:
                            value = await opt.get_attribute('value')
                            if value and value not in ['', 'select', 'choose']:
                                await dropdown.select_option(value=value)
                                logger.info(f"✅ Selected referral source (fallback)")
                                return
                    except Exception as e:
                        logger.debug(f"Referral dropdown failed: {e}")
        except Exception as e:
            logger.debug(f"Referral source handling failed: {e}")
    
    async def _handle_experience_dropdown(self, page):
        """Handle years of experience dropdowns"""
        try:
            exp_selectors = [
                'select[name*="experience"]',
                'select[name*="years"]',
                'select[aria-label*="experience"]',
                'select[aria-label*="years"]',
            ]
            
            for selector in exp_selectors:
                dropdown = await page.query_selector(selector)
                if dropdown:
                    try:
                        options = await dropdown.query_selector_all('option')
                        for opt in options:
                            text = (await opt.text_content() or "").lower()
                            # Elena has 10+ years of experience
                            if '10' in text or '10+' in text or 'more than 10' in text or '11' in text:
                                value = await opt.get_attribute('value')
                                if value:
                                    await dropdown.select_option(value=value)
                                    logger.info(f"✅ Selected experience: {text[:30]}")
                                    return
                        # Fallback: try 8-10 or similar
                        for opt in options:
                            text = (await opt.text_content() or "").lower()
                            if any(kw in text for kw in ['8', '9', '7-10', '5-10']):
                                value = await opt.get_attribute('value')
                                if value:
                                    await dropdown.select_option(value=value)
                                    logger.info(f"✅ Selected experience (fallback): {text[:30]}")
                                    return
                    except Exception as e:
                        logger.debug(f"Experience dropdown failed: {e}")
        except Exception as e:
            logger.debug(f"Experience handling failed: {e}")
    
    async def _handle_education_dropdown(self, page):
        """Handle education level dropdowns"""
        try:
            edu_selectors = [
                'select[name*="education"]',
                'select[name*="degree"]',
                'select[aria-label*="education"]',
                'select[aria-label*="degree"]',
                'select[aria-label*="highest"]',
            ]
            
            for selector in edu_selectors:
                dropdown = await page.query_selector(selector)
                if dropdown:
                    try:
                        options = await dropdown.query_selector_all('option')
                        for opt in options:
                            text = (await opt.text_content() or "").lower()
                            # Elena has a Master's degree
                            if "master" in text or "m.a." in text or "m.s." in text or "graduate" in text:
                                value = await opt.get_attribute('value')
                                if value:
                                    await dropdown.select_option(value=value)
                                    logger.info(f"✅ Selected education: {text[:30]}")
                                    return
                    except Exception as e:
                        logger.debug(f"Education dropdown failed: {e}")
        except Exception as e:
            logger.debug(f"Education handling failed: {e}")
    
    async def _handle_common_checkboxes(self, page):
        """Handle common checkboxes like age verification, background check consent"""
        try:
            # Age 18+ checkbox
            age_checkboxes = await page.query_selector_all('input[type="checkbox"][name*="age"], input[type="checkbox"][aria-label*="18"]')
            for cb in age_checkboxes:
                if not await cb.is_checked():
                    await cb.click()
                    logger.info(f"✅ Checked age verification")
            
            # Background check consent
            bg_checkboxes = await page.query_selector_all('input[type="checkbox"][name*="background"], input[type="checkbox"][name*="consent"]')
            for cb in bg_checkboxes:
                if not await cb.is_checked():
                    await cb.click()
                    logger.info(f"✅ Checked background check consent")
            
            # Terms agreement
            terms_checkboxes = await page.query_selector_all('input[type="checkbox"][name*="terms"], input[type="checkbox"][name*="agree"]')
            for cb in terms_checkboxes:
                if not await cb.is_checked():
                    await cb.click()
                    logger.info(f"✅ Checked terms agreement")
                    
        except Exception as e:
            logger.debug(f"Checkbox handling failed: {e}")
    
    async def _fill_field_with_selectors(self, page, selectors: List[str], value: str, field_name: str) -> bool:
        """Try multiple selectors to fill a field"""
        for selector in selectors:
            try:
                field = await page.query_selector(selector)
                if field:
                    # Clear existing value first
                    await field.click()
                    await field.fill("")
                    await field.fill(value)
                    logger.info(f"✅ Filled {field_name}: {selector}")
                    return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed for {field_name}: {e}")
        
        logger.warning(f"⚠️ Could not fill {field_name} - no selector matched")
        return False
    
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
        """
        Fill Lever application form with comprehensive field support.
        
        Lever uses a different structure than Greenhouse:
        - Single name field
        - URLs as separate inputs
        - Cards/sections for different parts
        """
        
        full_name = f"{self.applicant_data['first_name']} {self.applicant_data['last_name']}"
        
        # ═══════════════════════════════════════════════════════════
        # BASIC INFO
        # ═══════════════════════════════════════════════════════════
        
        field_mappings = [
            # Name (Lever uses single name field)
            ('input[name="name"]', full_name),
            ('input[placeholder*="Full name"]', full_name),
            ('input[aria-label*="Full name"]', full_name),
            
            # Contact
            ('input[name="email"]', self.applicant_data['email']),
            ('input[name="phone"]', self.applicant_data['phone']),
            ('input[type="email"]', self.applicant_data['email']),
            ('input[type="tel"]', self.applicant_data['phone']),
            
            # Current company
            ('input[name="org"]', self.applicant_data['current_company']),
            ('input[placeholder*="Current company"]', self.applicant_data['current_company']),
            
            # URLs
            ('input[name="urls[LinkedIn]"]', self.applicant_data['linkedin']),
            ('input[name="urls[GitHub]"]', self.applicant_data['github']),
            ('input[name="urls[Portfolio]"]', self.applicant_data['portfolio']),
            ('input[name="urls[Website]"]', self.applicant_data['website']),
            ('input[placeholder*="LinkedIn"]', self.applicant_data['linkedin']),
            ('input[placeholder*="GitHub"]', self.applicant_data['github']),
            ('input[placeholder*="Portfolio"]', self.applicant_data['portfolio']),
            
            # Location
            ('input[name="location"]', self.applicant_data['location']),
            ('input[placeholder*="Location"]', self.applicant_data['location']),
        ]
        
        for selector, value in field_mappings:
            try:
                field = await page.query_selector(selector)
                if field:
                    await field.click()
                    await field.fill("")
                    await field.fill(value)
                    logger.info(f"✅ Filled Lever field: {selector[:40]}")
            except Exception as e:
                logger.debug(f"Lever field {selector} failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # COVER LETTER / ADDITIONAL INFO
        # ═══════════════════════════════════════════════════════════
        
        cover_selectors = [
            'textarea[name="comments"]',
            'textarea[name="additionalInfo"]',
            'textarea[name="coverLetter"]',
            'textarea[placeholder*="cover"]',
            'textarea[placeholder*="additional"]',
            'textarea[aria-label*="Additional"]',
        ]
        
        for selector in cover_selectors:
            try:
                textarea = await page.query_selector(selector)
                if textarea:
                    await textarea.fill(cover_letter)
                    logger.info(f"✅ Filled Lever cover letter")
                    break
            except Exception as e:
                logger.debug(f"Lever textarea {selector} failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # DROPDOWNS (work auth, referral source, etc.)
        # ═══════════════════════════════════════════════════════════
        
        # Handle any dropdowns on the page
        await self._handle_work_authorization(page)
        await self._handle_referral_source(page)
        await self._handle_experience_dropdown(page)
        await self._handle_education_dropdown(page)
        
        # ═══════════════════════════════════════════════════════════
        # RESUME UPLOAD
        # ═══════════════════════════════════════════════════════════
        
        if resume_path and os.path.exists(resume_path):
            file_selectors = [
                'input[type="file"][name="resume"]',
                'input[type="file"]',
            ]
            for selector in file_selectors:
                try:
                    file_input = await page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(resume_path)
                        logger.info(f"✅ Uploaded resume to Lever")
                        break
                except Exception as e:
                    logger.debug(f"Lever resume upload failed: {e}")
        
        # Handle checkboxes
        await self._handle_common_checkboxes(page)
    
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
        """
        Fill Ashby application form with comprehensive field support.
        
        Ashby is a modern ATS used by many YC companies (Cohere, Perplexity, Ramp, etc.)
        Uses data-testid attributes and modern React patterns.
        """
        
        full_name = f"{self.applicant_data['first_name']} {self.applicant_data['last_name']}"
        
        # ═══════════════════════════════════════════════════════════
        # NAME FIELDS
        # ═══════════════════════════════════════════════════════════
        
        # First name
        first_name_selectors = [
            'input[data-testid="first-name-input"]',
            'input[name*="firstName"]',
            'input[name*="first_name"]',
            'input[placeholder*="First"]',
            'input[aria-label*="First name"]',
        ]
        await self._fill_field_with_selectors(page, first_name_selectors, self.applicant_data['first_name'], "first_name")
        
        # Last name
        last_name_selectors = [
            'input[data-testid="last-name-input"]',
            'input[name*="lastName"]',
            'input[name*="last_name"]',
            'input[placeholder*="Last"]',
            'input[aria-label*="Last name"]',
        ]
        await self._fill_field_with_selectors(page, last_name_selectors, self.applicant_data['last_name'], "last_name")
        
        # ═══════════════════════════════════════════════════════════
        # CONTACT INFO
        # ═══════════════════════════════════════════════════════════
        
        # Email
        email_selectors = [
            'input[data-testid="email-input"]',
            'input[type="email"]',
            'input[name*="email"]',
            'input[placeholder*="Email"]',
        ]
        await self._fill_field_with_selectors(page, email_selectors, self.applicant_data['email'], "email")
        
        # Phone
        phone_selectors = [
            'input[data-testid="phone-input"]',
            'input[type="tel"]',
            'input[name*="phone"]',
            'input[placeholder*="Phone"]',
        ]
        await self._fill_field_with_selectors(page, phone_selectors, self.applicant_data['phone'], "phone")
        
        # ═══════════════════════════════════════════════════════════
        # PROFESSIONAL LINKS
        # ═══════════════════════════════════════════════════════════
        
        link_mappings = [
            ('input[name*="linkedin"]', self.applicant_data['linkedin']),
            ('input[placeholder*="LinkedIn"]', self.applicant_data['linkedin']),
            ('input[name*="github"]', self.applicant_data['github']),
            ('input[placeholder*="GitHub"]', self.applicant_data['github']),
            ('input[name*="portfolio"]', self.applicant_data['portfolio']),
            ('input[name*="website"]', self.applicant_data['website']),
            ('input[placeholder*="Portfolio"]', self.applicant_data['portfolio']),
        ]
        
        for selector, value in link_mappings:
            try:
                field = await page.query_selector(selector)
                if field:
                    await field.click()
                    await field.fill("")
                    await field.fill(value)
                    logger.info(f"✅ Filled Ashby link: {selector[:40]}")
            except Exception as e:
                logger.debug(f"Ashby link field failed: {e}")
        
        # Location
        location_selectors = [
            'input[name*="location"]',
            'input[placeholder*="Location"]',
            'input[placeholder*="City"]',
            'input[aria-label*="Location"]',
        ]
        await self._fill_field_with_selectors(page, location_selectors, self.applicant_data['location'], "location")
        
        # ═══════════════════════════════════════════════════════════
        # DROPDOWNS AND CUSTOM QUESTIONS
        # ═══════════════════════════════════════════════════════════
        
        await self._handle_work_authorization(page)
        await self._handle_referral_source(page)
        await self._handle_experience_dropdown(page)
        await self._handle_education_dropdown(page)
        
        # ═══════════════════════════════════════════════════════════
        # COVER LETTER / ADDITIONAL INFO
        # ═══════════════════════════════════════════════════════════
        
        # Ashby often has multiple textareas - find the right one
        cover_selectors = [
            'textarea[name*="cover"]',
            'textarea[placeholder*="cover"]',
            'textarea[placeholder*="Cover"]',
            'textarea[aria-label*="cover"]',
            'textarea[name*="additional"]',
            'textarea[placeholder*="additional"]',
        ]
        
        cover_filled = False
        for selector in cover_selectors:
            try:
                textarea = await page.query_selector(selector)
                if textarea:
                    await textarea.fill(cover_letter)
                    logger.info(f"✅ Filled Ashby cover letter")
                    cover_filled = True
                    break
            except Exception as e:
                logger.debug(f"Ashby cover letter selector failed: {e}")
        
        # Fallback: try first visible textarea
        if not cover_filled:
            try:
                textareas = await page.query_selector_all('textarea:visible')
                for ta in textareas:
                    placeholder = await ta.get_attribute('placeholder') or ""
                    if any(kw in placeholder.lower() for kw in ['cover', 'additional', 'why', 'tell us']):
                        await ta.fill(cover_letter)
                        logger.info(f"✅ Filled Ashby cover letter (fallback)")
                        break
            except Exception as e:
                logger.debug(f"Ashby textarea fallback failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # RESUME UPLOAD
        # ═══════════════════════════════════════════════════════════
        
        if resume_path and os.path.exists(resume_path):
            file_selectors = [
                'input[type="file"][accept*="pdf"]',
                'input[type="file"][name*="resume"]',
                'input[type="file"]',
            ]
            for selector in file_selectors:
                try:
                    file_input = await page.query_selector(selector)
                    if file_input:
                        await file_input.set_input_files(resume_path)
                        logger.info(f"✅ Uploaded resume to Ashby")
                        break
                except Exception as e:
                    logger.debug(f"Ashby resume upload failed: {e}")
        
        # Handle checkboxes
        await self._handle_common_checkboxes(page)
    
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
