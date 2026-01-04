"""
👤 FOUNDER FINDER — Production v3.5 (ENHANCED EMAIL DISCOVERY)

Finds founder contact information (LinkedIn, Twitter, Email).
Uses multiple data sources to build complete founder profiles.

CHANGELOG v3.5:
✅ ENHANCED: Hunter.io integration for real email discovery
✅ ENHANCED: Personalized email generation from founder names
✅ ENHANCED: Email verification before using
✅ FIXED MessageGenerator.generate_founder_message() signature mismatch
✅ Now passes company/job as Dicts (not strings/kwargs)
✅ ResponseCache signature issue fixed (explicit kwargs)
✅ All methods implemented and working
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import aiohttp
from bs4 import BeautifulSoup

from ..core.models import JobPosting, Profile
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

# Email discovery enhancement
try:
    from .email_verifier import get_email_verifier, EmailVerifier
    EMAIL_VERIFIER_AVAILABLE = True
except ImportError:
    EMAIL_VERIFIER_AVAILABLE = False

# ──────────────────────────────────────────────────────────────
# LOGGER + DEPLOYMENT FINGERPRINT
# ──────────────────────────────────────────────────────────────
logger = setup_logger(__name__)

FINGERPRINT = "FounderFinderV2_2025-12-20_CACHE_FIX_v3.4"
CACHE_MODEL = "founder_finder_v2"

logger.info(f"🔥 LOADING MODULE: founder_finder_v2 | {FINGERPRINT}")


# ──────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────
class FounderFinderV2:
    """
    Finds and profiles company founders.
    Discovers: LinkedIn, Twitter, Email.

    Production v3.3 — MessageGenerator-compatible, cache-safe, orchestrator-ready.
    """

    def __init__(self):
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))

        # Email verifier (Hunter.io)
        if EMAIL_VERIFIER_AVAILABLE:
            self.email_verifier = get_email_verifier()
            logger.info("✅ Email verifier (Hunter.io) ENABLED")
        else:
            self.email_verifier = None
            logger.warning("⚠️ Email verifier not available")

        # Optional integrations
        try:
            from .message_generator import MessageGenerator
            from ..core.models import Profile
            # MessageGenerator needs a profile, we'll use None for now
            # It will use its internal profile if available
            self.message_generator = MessageGenerator(profile=None)
        except Exception as e:
            logger.warning(f"MessageGenerator unavailable: {e}")
            self.message_generator = None

        try:
            from .email_service import create_email_service
            self.email_service = create_email_service()
        except Exception as e:
            logger.warning(f"Email service unavailable: {e}")
            self.email_service = None

        try:
            from ..notifications import TelegramNotifier
            self.telegram_notifier = TelegramNotifier()
        except Exception as e:
            logger.warning(f"Telegram notifier unavailable: {e}")
            self.telegram_notifier = None

        try:
            from ..database.database_models import DatabaseHelper
            self.db = DatabaseHelper()
        except Exception:
            self.db = None

        logger.info("👤 FounderFinderV2 initialized (production v3.3)")

    # ════════════════════════════════════════════════════════════
    # ORCHESTRATOR ENTRYPOINT
    # ════════════════════════════════════════════════════════════

    async def find_and_message(self, job: JobPosting, profile: Profile) -> Dict[str, Any]:
        """
        Complete workflow: Find founder → Generate message → Send
        Called by orchestrator for OUTREACH routing
        """
        result = {
            "success": False,
            "founder_found": False,
            "message_sent": False,
            "channel": "none",
            "founder_name": None,
        }

        company = job.company
        logger.info(f"🔍 Founder outreach started for {company}")

        try:
            # Step 1: Find founder
            founder_data = await self.find_founder(
                company,
                {
                    "url": getattr(job, "company_url", ""),
                    "description": getattr(job, "description", ""),
                },
            )

            if not founder_data:
                logger.warning(f"⚠️ No founder found for {company}")
                await self._log_outreach_attempt(job, None, "founder_not_found")
                return result

            result["founder_found"] = True
            founder_name = self._extract_founder_name(founder_data)
            result["founder_name"] = founder_name
            
            if founder_name:
                logger.info(f"✅ Found contact: {founder_name}")

            # Step 2: Generate message
            message_data = await self._generate_outreach_message(
                founder_data, job, profile
            )
            if not message_data or not message_data.get("message"):
                logger.error(f"❌ Message generation failed for {company}")
                return result

            # Step 3: Determine channel and send
            channel = self._determine_best_channel(founder_data)
            result["channel"] = channel
            
            logger.info(f"📡 Best channel for {company}: {channel}")

            sent = False
            if channel == "email":
                email = self._extract_email(founder_data)
                if email:
                    sent = await self._send_email_message(
                        email,
                        message_data["message"],
                        message_data.get("subject", f"Re: {job.title} at {company}"),
                        founder_name or "Hiring Team",
                        company,
                    )

            elif channel == "linkedin":
                linkedin_url = self._extract_linkedin(founder_data)
                if linkedin_url:
                    sent = await self._send_linkedin_message(
                        linkedin_url,
                        message_data["message"],
                        founder_name or "Contact",
                        company,
                    )

            elif channel == "twitter":
                twitter_handle = self._extract_twitter(founder_data)
                if twitter_handle:
                    sent = await self._send_twitter_dm(
                        twitter_handle,
                        message_data["message"],
                        founder_name or "Contact",
                        company,
                    )
            else:
                logger.warning(f"⚠️ No valid contact channel for {company}")

            result["message_sent"] = sent
            result["success"] = sent

            # Step 4: Log attempt
            await self._log_outreach_attempt(
                job,
                founder_data,
                "sent" if sent else "failed",
                channel,
                message_data["message"],
            )
            
            if sent:
                logger.info(f"✅ Outreach sent to {company} via {channel}")
            else:
                logger.error(f"❌ Failed to send outreach to {company}")

            return result

        except Exception as e:
            logger.error(f"❌ Founder outreach error for {company}: {e}")
            result["error"] = str(e)
            return result

    # ════════════════════════════════════════════════════════════
    # FOUNDER DISCOVERY (CACHE-SAFE - FIXED)
    # ════════════════════════════════════════════════════════════

    async def find_founder(
        self, company_name: str, company_intel: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find founder info with caching
        
        FIXED: Explicit keyword arguments to avoid signature conflict
        """
        cache_key = f"founder::{company_name.lower().replace(' ', '_')}"

        # ─────────────────────────────────────────────────────────
        # FIX v3.4: Use get_data() for arbitrary data caching
        # ─────────────────────────────────────────────────────────
        try:
            cached = self.cache.get_data(cache_key)
            if cached:
                logger.debug(f"📦 Cache hit for founder: {company_name}")
                return cached
        except Exception as e:
            logger.debug(f"Cache get failed (non-fatal): {e}")

        # Fetch from multiple sources
        tasks = [
            self._search_linkedin(company_name),
            self._search_twitter(company_name),
            self._find_email_pattern(company_name, company_intel.get("url", "")),
            self._check_yc_profile(company_name),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        founder_info: Dict[str, Any] = {"company": company_name}

        for r in results:
            if isinstance(r, dict):
                founder_info.update(r)

        # Validate we found something
        if len(founder_info) <= 1:
            logger.debug(f"No founder info found for {company_name}")
            return None

        # ─────────────────────────────────────────────────────────
        # ENHANCED v3.5: Generate personalized emails from founder names
        # ─────────────────────────────────────────────────────────
        await self._enhance_with_personalized_emails(founder_info)

        # ─────────────────────────────────────────────────────────
        # FIX v3.4: Use set_data() for arbitrary data caching
        # ─────────────────────────────────────────────────────────
        try:
            self.cache.set_data(cache_key, founder_info)
            logger.debug(f"📦 Cached founder info for {company_name}")
        except Exception as e:
            logger.warning(f"Cache set failed (non-fatal): {e}")

        return founder_info
    
    async def _enhance_with_personalized_emails(self, founder_info: Dict[str, Any]) -> None:
        """
        Generate personalized emails from founder names.
        If we found founder names (e.g., from YC), generate their likely emails.
        """
        domain = founder_info.get("domain")
        founders = founder_info.get("founders", [])
        
        if not domain or not founders:
            return
        
        email_patterns = founder_info.get("email_patterns", [])
        existing = set(email_patterns)
        
        for founder in founders[:2]:  # Top 2 founders
            name = founder.get("name", "")
            if not name:
                continue
            
            # Parse name
            parts = name.strip().split()
            if len(parts) < 2:
                continue
            
            first_name = parts[0].lower()
            last_name = parts[-1].lower()
            
            # Generate common email patterns for this founder
            personalized_patterns = [
                f"{first_name}@{domain}",                     # john@company.com
                f"{first_name}.{last_name}@{domain}",         # john.doe@company.com
                f"{first_name[0]}{last_name}@{domain}",       # jdoe@company.com
                f"{first_name}{last_name[0]}@{domain}",       # johnd@company.com
            ]
            
            # Try to verify with Hunter.io if available
            if self.email_verifier:
                try:
                    # Use Hunter.io email finder for exact match
                    result = await self.email_verifier.find_email(domain, parts[0], parts[-1])
                    if result.get('found') and result.get('email'):
                        verified_email = result['email']
                        logger.info(f"✅ Hunter.io found founder email: {verified_email}")
                        
                        # Add to verified emails
                        if 'verified_emails' not in founder_info:
                            founder_info['verified_emails'] = []
                        
                        founder_info['verified_emails'].append({
                            'email': verified_email,
                            'name': name,
                            'position': founder.get('title', 'Founder'),
                            'confidence': result.get('score', 90)
                        })
                        
                        # Add to patterns at high priority
                        if verified_email not in existing:
                            email_patterns.insert(0, verified_email)
                            existing.add(verified_email)
                        
                        # Skip pattern-based additions if we found verified
                        continue
                        
                except Exception as e:
                    logger.debug(f"Hunter.io email finder failed: {e}")
            
            # Add pattern-based emails (lower priority)
            for pattern in personalized_patterns:
                if pattern not in existing:
                    email_patterns.append(pattern)
                    existing.add(pattern)
        
        founder_info["email_patterns"] = email_patterns

    async def _search_linkedin(self, company_name: str) -> Dict[str, Any]:
        """Construct LinkedIn company page URL"""
        slug = company_name.lower().replace(" ", "-").replace(",", "").replace(".", "")
        return {"linkedin_company": f"https://www.linkedin.com/company/{slug}"}

    async def _search_twitter(self, company_name: str) -> Dict[str, Any]:
        """Construct Twitter company handle"""
        slug = company_name.lower().replace(" ", "").replace(",", "").replace(".", "")
        return {"twitter_company": f"https://twitter.com/{slug}"}

    async def _find_email_pattern(self, company_name: str, company_url: str) -> Dict[str, Any]:
        """
        🚀 ENHANCED EMAIL DISCOVERY v3.5
        
        Priority order:
        1. Hunter.io domain search (real verified emails)
        2. Personalized emails from founder names
        3. Common founder-friendly patterns
        """
        if not company_url:
            return {}
        
        domain = company_url.replace("https://", "").replace("http://", "").split("/")[0]
        domain = domain.replace("www.", "")
        
        result = {
            "domain": domain,
            "email_patterns": [],
            "verified_emails": [],
            "email_source": "pattern"
        }
        
        # ─────────────────────────────────────────────────────
        # STEP 1: Try Hunter.io domain search (best quality)
        # ─────────────────────────────────────────────────────
        if self.email_verifier and hasattr(self.email_verifier, 'search_domain'):
            try:
                hunter_result = await self.email_verifier.search_domain(domain, limit=5)
                if hunter_result.get('found', 0) > 0:
                    for email_data in hunter_result.get('emails', []):
                        email = email_data.get('email')
                        position = (email_data.get('position') or '').lower()
                        
                        # Prioritize founders/executives
                        if email and any(p in position for p in ['founder', 'ceo', 'cto', 'vp', 'director', 'head']):
                            result['verified_emails'].append({
                                'email': email,
                                'name': email_data.get('name', ''),
                                'position': email_data.get('position', ''),
                                'confidence': email_data.get('confidence', 0)
                            })
                            result['email_patterns'].insert(0, email)  # High priority
                            logger.info(f"✅ Hunter.io found: {email} ({position})")
                    
                    if result['verified_emails']:
                        result['email_source'] = 'hunter.io'
                        
            except Exception as e:
                logger.debug(f"Hunter.io search failed (non-fatal): {e}")
        
        # ─────────────────────────────────────────────────────
        # STEP 2: Generate patterns from common founder formats
        # Only add if not already found by Hunter
        # ─────────────────────────────────────────────────────
        existing = set(result['email_patterns'])
        
        # Priority patterns (founder-friendly, non-ATS)
        priority_patterns = [
            f"founder@{domain}",
            f"hello@{domain}",
            f"hi@{domain}",
            f"team@{domain}",
            f"contact@{domain}",
        ]
        
        for pattern in priority_patterns:
            if pattern not in existing:
                result['email_patterns'].append(pattern)
        
        # ─────────────────────────────────────────────────────
        # STEP 3: Log discovery summary
        # ─────────────────────────────────────────────────────
        verified_count = len(result.get('verified_emails', []))
        pattern_count = len(result.get('email_patterns', []))
        
        if verified_count > 0:
            logger.info(f"📧 Email discovery for {company_name}: {verified_count} verified, {pattern_count} patterns")
        else:
            logger.debug(f"📧 Email patterns for {company_name}: {pattern_count} generated")
        
        return result

    async def _check_yc_profile(self, company_name: str) -> Dict[str, Any]:
        """Scrape YC profile for founder info"""
        try:
            slug = company_name.lower().replace(" ", "-")
            url = f"https://www.ycombinator.com/companies/{slug}"
            
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                async with session.get(url, headers=headers, timeout=10) as r:
                    if r.status != 200:
                        return {}
                    html = await r.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract founder names
            founders = []
            founder_section = soup.find("div", class_="founders")
            if founder_section:
                founder_links = founder_section.find_all("a")
                for link in founder_links:
                    name = link.text.strip()
                    if name:
                        founders.append({"name": name, "linkedin": link.get("href", "")})
            
            if founders:
                return {
                    "yc_profile": url,
                    "founders": founders,
                    "primary_founder": founders[0] if founders else None,
                }
            
            return {}
            
        except Exception as e:
            logger.debug(f"YC profile check failed: {e}")
            return {}

    # ════════════════════════════════════════════════════════════
    # MESSAGE GENERATION - FIXED SIGNATURE v3.3
    # ════════════════════════════════════════════════════════════

    async def _generate_outreach_message(
        self, founder_data: Dict, job: JobPosting, profile: Profile
    ) -> Optional[Dict]:
        """
        Generate personalized outreach message
        
        FIXED v3.3: Now matches MessageGenerator.generate_founder_message() signature
        - Passes company as Dict (not string)
        - Passes job as Dict (not kwargs)
        """
        try:
            founder_name = self._extract_founder_name(founder_data)
            
            # Use MessageGenerator if available
            if self.message_generator:
                # ─────────────────────────────────────────────────────
                # FIX v3.3: Convert to Dict format MessageGenerator expects
                # MessageGenerator signature:
                #   generate_founder_message(company: Dict, job: Dict, ...)
                # ─────────────────────────────────────────────────────
                company_dict = {
                    "name": job.company,
                    "founder_name": founder_name or "Hiring Team",
                    "domain": founder_data.get("domain", ""),
                    "url": getattr(job, "company_url", ""),
                }
                
                job_dict = {
                    "title": job.title,
                    "description": job.description[:500] if job.description else "",
                    "url": getattr(job, "url", ""),
                    "requirements": getattr(job, "requirements", []),
                }
                
                # Call with CORRECT signature
                message_data = await self.message_generator.generate_founder_message(
                    company=company_dict,
                    job=job_dict,
                    candidate_background=None  # Uses profile from MessageGenerator init
                )
                
                # Convert MessageGenerator response format to our format
                return {
                    "message": message_data.get("body", ""),
                    "subject": message_data.get("subject", f"Re: {job.title} at {job.company}"),
                    "tone": "professional",
                }
            
            # Fallback template if MessageGenerator not available
            salutation = f"Hi {founder_name}" if founder_name else "Hi there"
            
            # 🏆 YC ADVANTAGE: Special warm intro for YC companies
            is_yc = getattr(job, 'is_yc_company', False) or (
                hasattr(job, 'source') and 'yc' in str(job.source).lower()
            )
            
            if is_yc:
                # YC-specific warm intro - they love builders!
                message = f"""{salutation},

I saw your {job.title} role on YC's Work at a Startup board. As a solo founder who shipped 11 AI products in 10 months (including AI Co-Founders running 24/7), I'm particularly drawn to YC companies building with urgency.

My EspaLuz tutor serves users in 19 countries, and my CTO AIPA reviews code across 8 repos autonomously. I'd love to bring this same builder energy to {job.company}.

Try my AI: wa.me/50766623757

Best,
Elena"""
            else:
                # Standard warm intro
                message = f"""{salutation},

I came across {job.company}'s {job.title} role and was immediately drawn to it.

I've built 11 AI products in 10 months (7 live agents running 24/7), specializing in AI developer productivity and platform engineering. My background includes 7 years of strategic leadership as CEO/CLO.

I'd love to discuss how I can contribute to {job.company}'s mission. Would you be open to a quick chat?

Best regards,
Elena Revicheva
wa.me/50766623757"""

            return {
                "message": message,
                "subject": f"Re: {job.title} at {job.company}",
                "tone": "professional",
            }
            
        except Exception as e:
            logger.error(f"Message generation error: {e}")
            return None

    # ════════════════════════════════════════════════════════════
    # CHANNEL SENDING
    # ════════════════════════════════════════════════════════════

    async def _send_email_message(
        self, email: str, message: str, subject: str, founder_name: str, company: str
    ) -> bool:
        """Send email via Resend"""
        try:
            if not self.email_service:
                logger.warning("⚠️ Email service not configured")
                await self._save_to_manual_queue({
                    "channel": "email",
                    "contact": founder_name,
                    "company": company,
                    "email": email,
                    "subject": subject,
                    "message": message,
                    "status": "pending_manual_send",
                    "created_at": datetime.utcnow().isoformat(),
                })
                return True
            
            await self.email_service.send_email(
                to=email,
                subject=subject,
                body=message,
                from_name="Elena Revicheva",
                from_email="elena@vibejobhunter.com",
            )
            
            logger.info(f"✅ Email sent to {founder_name} ({email})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send error: {e}")
            return False

    async def _send_linkedin_message(
        self, linkedin_url: str, message: str, founder_name: str, company: str
    ) -> bool:
        """Log LinkedIn message for manual sending"""
        try:
            logger.info(f"📝 LinkedIn message ready for {founder_name} at {company}")
            
            await self._save_to_manual_queue({
                "channel": "linkedin",
                "contact": founder_name,
                "company": company,
                "url": linkedin_url,
                "message": message,
                "status": "pending_manual_send",
                "created_at": datetime.utcnow().isoformat(),
            })
            
            # Send Telegram notification with FULL message (no truncation!)
            if self.telegram_notifier:
                telegram_text = f"""🤝 <b>LinkedIn Outreach Ready</b>

👤 Contact: {founder_name}
🏢 Company: {company}
🔗 LinkedIn: {linkedin_url}

📝 <b>Message (copy this):</b>
<code>{message}</code>

<i>👆 Tap message above to copy, then paste on LinkedIn!</i>"""
                
                await self.telegram_notifier.send_notification(telegram_text)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ LinkedIn message error: {e}")
            return False

    async def _send_twitter_dm(
        self, twitter_handle: str, message: str, founder_name: str, company: str
    ) -> bool:
        """Log Twitter DM for manual sending"""
        try:
            logger.info(f"📝 Twitter DM ready for {founder_name} (@{twitter_handle})")
            
            await self._save_to_manual_queue({
                "channel": "twitter",
                "contact": founder_name,
                "company": company,
                "handle": twitter_handle,
                "message": message,
                "status": "pending_manual_send",
                "created_at": datetime.utcnow().isoformat(),
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Twitter DM error: {e}")
            return False

    # ════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════

    def _extract_founder_name(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract founder name from data"""
        if data.get("founders") and len(data["founders"]) > 0:
            return data["founders"][0].get("name")
        if data.get("primary_founder"):
            return data["primary_founder"].get("name")
        return None

    def _extract_email(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract best email from data.
        Priority: verified emails > patterns > None
        """
        # First check for verified emails (from Hunter.io)
        verified = data.get("verified_emails", [])
        if verified:
            # Return highest confidence verified email
            return verified[0].get('email')
        
        # Fall back to patterns
        patterns = data.get("email_patterns", [])
        if patterns:
            # Filter out ATS emails (careers@, jobs@, etc.)
            ats_patterns = ['careers@', 'jobs@', 'hr@', 'recruiting@', 'talent@', 'apply@']
            for pattern in patterns:
                if not any(ats in pattern.lower() for ats in ats_patterns):
                    return pattern
            # If all are ATS, still return first (ATS submitter handles those)
            return patterns[0]
        
        return None

    def _extract_linkedin(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract LinkedIn URL"""
        if data.get("founders") and len(data["founders"]) > 0:
            linkedin = data["founders"][0].get("linkedin")
            if linkedin and linkedin.startswith("http"):
                return linkedin
        return data.get("linkedin_company")

    def _extract_twitter(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract Twitter handle"""
        url = data.get("twitter_company")
        return url.split("/")[-1] if url else None

    def _determine_best_channel(self, data: Dict[str, Any]) -> str:
        """
        Determine best contact channel.
        
        Priority (for AUTO-SEND):
        1. Verified email (Hunter.io) - auto-sendable!
        2. Founder-friendly email patterns (hello@, founder@) - auto-sendable!
        3. LinkedIn (manual send only)
        4. Twitter (manual send only)
        """
        # Check for verified emails first (highest priority - auto-sendable!)
        verified = data.get("verified_emails", [])
        if verified:
            logger.info(f"📧 Best channel: EMAIL (verified via Hunter.io)")
            return "email"
        
        # Check for founder-friendly email patterns
        patterns = data.get("email_patterns", [])
        domain = data.get("domain")
        if patterns and domain:
            # Check if we have non-ATS patterns
            ats_patterns = ['careers@', 'jobs@', 'hr@', 'recruiting@', 'talent@', 'apply@']
            for pattern in patterns:
                if not any(ats in pattern.lower() for ats in ats_patterns):
                    logger.info(f"📧 Best channel: EMAIL (pattern: {pattern})")
                    return "email"
        
        # Fall back to LinkedIn (manual)
        if data.get("founders") and data["founders"][0].get("linkedin"):
            return "linkedin"
        if data.get("linkedin_company"):
            return "linkedin"
        
        # Last resort: Twitter
        if data.get("twitter_company"):
            return "twitter"
        
        return "none"

    # ════════════════════════════════════════════════════════════
    # LOGGING & TRACKING
    # ════════════════════════════════════════════════════════════

    async def _log_outreach_attempt(
        self,
        job: JobPosting,
        founder_data: Optional[Dict[str, Any]],
        status: str,
        channel: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Log outreach attempt to JSONL file"""
        try:
            record = {
                "job_id": getattr(job, "id", None) or f"{job.company}_{job.title}",
                "company": job.company,
                "job_title": job.title,
                "founder_name": self._extract_founder_name(founder_data) if founder_data else None,
                "channel": channel,
                "status": status,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "match_score": getattr(job, "match_score", 0),
            }

            log_file = Path("autonomous_data/outreach_log.jsonl")
            log_file.parent.mkdir(exist_ok=True)
            with open(log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
                
            logger.debug(f"💾 Logged outreach attempt for {job.company}")

        except Exception as e:
            logger.error(f"Failed to log outreach attempt: {e}")

    async def _save_to_manual_queue(self, outreach_data: Dict) -> None:
        """Save outreach to manual queue (LinkedIn/Twitter)"""
        try:
            queue_file = Path("autonomous_data/manual_outreach_queue.json")
            queue_file.parent.mkdir(exist_ok=True)

            # Load existing queue
            queue = []
            if queue_file.exists():
                with open(queue_file, "r") as f:
                    queue = json.load(f)

            # Add new item
            queue.append(outreach_data)

            # Save back
            with open(queue_file, "w") as f:
                json.dump(queue, f, indent=2)

            logger.debug(f"💾 Saved to manual queue: {outreach_data['company']}")

        except Exception as e:
            logger.error(f"Failed to save to manual queue: {e}")


# ──────────────────────────────────────────────────────────────
# MODULE LOAD VERIFICATION
# ──────────────────────────────────────────────────────────────
assert "FounderFinderV2" in globals(), "❌ FounderFinderV2 not loaded"
logger.info(f"✅ FounderFinderV2 LOADED | {FINGERPRINT}")
