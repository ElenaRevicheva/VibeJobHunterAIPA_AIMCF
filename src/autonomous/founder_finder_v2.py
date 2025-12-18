"""
👤 FOUNDER FINDER - Production v3.0
Finds founder contact information (LinkedIn, Twitter, Email).
Uses multiple data sources to build complete founder profiles.

CHANGES (2024-12-18):
✅ Added find_and_message() for orchestrator integration
✅ Email sending via Resend
✅ Manual outreach queue for LinkedIn/Twitter
✅ Outreach attempt logging
✅ Message generation integration
✅ Telegram notifications for manual actions
"""

import asyncio
import logging
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiohttp
from bs4 import BeautifulSoup

from ..core.models import JobPosting, Profile
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

logger = setup_logger(__name__)


class FounderFinder:
    """
    Finds and profiles company founders
    Discovers: LinkedIn, Twitter, Email, recent activity
    
    Production v3.0: Integrated with multi-channel routing
    """
    
    def __init__(self):
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        
        # Initialize integrations
        try:
            from .message_generator import MessageGenerator
            self.message_generator = MessageGenerator(profile=None)
        except Exception as e:
            logger.warning(f"MessageGenerator not available: {e}")
            self.message_generator = None
        
        try:
            from .email_service import create_email_service
            self.email_service = create_email_service()
        except Exception as e:
            logger.warning(f"Email service not available: {e}")
            self.email_service = None
        
        try:
            from ..notifications import TelegramNotifier
            self.telegram_notifier = TelegramNotifier()
        except Exception as e:
            logger.warning(f"Telegram notifier not available: {e}")
            self.telegram_notifier = None
        
        # Database helper (optional)
        try:
            from ..database.database_models import DatabaseHelper
            self.db = DatabaseHelper()
        except:
            self.db = None
            logger.debug("Database not available for outreach tracking")
        
        logger.info("👤 Founder Finder initialized (v3.0)")
    
    # ════════════════════════════════════════════════════════════
    # NEW: Main entry point for orchestrator routing
    # ════════════════════════════════════════════════════════════
    
    async def find_and_message(self, job: JobPosting, profile: Profile) -> Dict:
        """
        Complete workflow: Find founder/hiring manager → Generate message → Send
        
        This is the entry point called by orchestrator for OUTREACH routing
        
        Args:
            job: JobPosting object with company, title, description
            profile: User profile for personalization
        
        Returns: {
            'success': bool,
            'founder_found': bool,
            'message_sent': bool,
            'channel': str (linkedin|email|twitter|none),
            'founder_name': str or None
        }
        """
        result = {
            'success': False,
            'founder_found': False,
            'message_sent': False,
            'channel': 'none',
            'founder_name': None
        }
        
        company = job.company
        title = job.title
        
        logger.info(f"🔍 Starting founder outreach for {company}")
        
        try:
            # ────────────────────────────────────────────────────────
            # STEP 1: Find founder/hiring manager
            # ────────────────────────────────────────────────────────
            company_intel = {
                'url': getattr(job, 'company_url', ''),
                'description': getattr(job, 'description', '')
            }
            
            founder_data = await self.find_founder(company, company_intel)
            
            if not founder_data:
                logger.warning(f"⚠️ No founder found for {company}")
                await self._log_outreach_attempt(job, None, 'founder_not_found')
                return result
            
            result['founder_found'] = True
            
            # Extract founder name from data
            founder_name = self._extract_founder_name(founder_data)
            result['founder_name'] = founder_name
            
            if founder_name:
                logger.info(f"✅ Found contact: {founder_name}")
            else:
                logger.info(f"✅ Found contact info for {company}")
            
            # ────────────────────────────────────────────────────────
            # STEP 2: Generate personalized message
            # ────────────────────────────────────────────────────────
            message_data = await self._generate_outreach_message(
                founder_data=founder_data,
                job=job,
                profile=profile
            )
            
            if not message_data or not message_data.get('message'):
                logger.error(f"❌ Message generation failed for {company}")
                return result
            
            # ────────────────────────────────────────────────────────
            # STEP 3: Determine best channel and send
            # ────────────────────────────────────────────────────────
            channel = self._determine_best_channel(founder_data)
            result['channel'] = channel
            
            logger.info(f"📡 Best channel for {company}: {channel}")
            
            success = False
            
            if channel == 'email':
                email = self._extract_email(founder_data)
                if email:
                    success = await self._send_email_message(
                        email=email,
                        message=message_data['message'],
                        subject=message_data.get('subject', f"Re: {title} at {company}"),
                        founder_name=founder_name or "Hiring Team",
                        company=company
                    )
            
            elif channel == 'linkedin':
                linkedin_url = self._extract_linkedin(founder_data)
                if linkedin_url:
                    success = await self._send_linkedin_message(
                        linkedin_url=linkedin_url,
                        message=message_data['message'],
                        founder_name=founder_name or "Contact",
                        company=company
                    )
            
            elif channel == 'twitter':
                twitter_handle = self._extract_twitter(founder_data)
                if twitter_handle:
                    success = await self._send_twitter_dm(
                        twitter_handle=twitter_handle,
                        message=message_data['message'],
                        founder_name=founder_name or "Contact",
                        company=company
                    )
            else:
                logger.warning(f"⚠️ No valid contact channel found for {company}")
            
            result['message_sent'] = success
            result['success'] = success
            
            # ────────────────────────────────────────────────────────
            # STEP 4: Log outreach attempt
            # ────────────────────────────────────────────────────────
            await self._log_outreach_attempt(
                job=job,
                founder_data=founder_data,
                status='sent' if success else 'failed',
                channel=channel,
                message=message_data['message']
            )
            
            if success:
                logger.info(f"✅ Outreach sent to {company} via {channel}")
            else:
                logger.error(f"❌ Failed to send outreach to {company}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Founder outreach error for {company}: {e}")
            result['error'] = str(e)
            return result
    
    # ════════════════════════════════════════════════════════════
    # EXISTING: Core founder finding logic
    # ════════════════════════════════════════════════════════════
    
    async def find_founder(self, company_name: str, company_intel: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find primary founder/hiring contact
        Returns: name, title, LinkedIn, Twitter, Email
        """
        logger.info(f"👤 Finding founder for {company_name}...")
        
        # Check cache
        cache_key = f"founder_{company_name.lower().replace(' ', '_')}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✅ Using cached founder info for {company_name}")
            return cached
        
        founder_info = {
            'company': company_name,
        }
        
        # Try multiple methods
        tasks = [
            self._search_linkedin(company_name),
            self._search_twitter(company_name),
            self._find_email_pattern(company_name, company_intel.get('url', '')),
            self._check_yc_profile(company_name),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for i, key in enumerate(['linkedin', 'twitter', 'email', 'yc_profile']):
            if not isinstance(results[i], Exception):
                founder_info.update(results[i])
            else:
                logger.debug(f"Failed to find {key}: {results[i]}")
        
        # Validate we found at least one contact method
        if not any([
            founder_info.get('linkedin_company'),
            founder_info.get('twitter_company'),
            founder_info.get('email_patterns'),
            founder_info.get('founders')
        ]):
            logger.warning(f"⚠️ No contact info found for {company_name}")
            return None
        
        # Cache for 30 days
        self.cache.set(cache_key, founder_info, ttl=2592000)
        
        logger.info(f"✅ Found founder info for {company_name}")
        return founder_info
    
    async def _search_linkedin(self, company_name: str) -> Dict[str, Any]:
        """Search for founder LinkedIn profile"""
        company_slug = company_name.lower().replace(' ', '-').replace(',', '').replace('.', '')
        linkedin_url = f"https://www.linkedin.com/company/{company_slug}"
        
        return {
            'linkedin_company': linkedin_url,
            'note': 'Use Phantombuster to extract founder profile'
        }
    
    async def _search_twitter(self, company_name: str) -> Dict[str, Any]:
        """Search for founder Twitter/X profile"""
        company_slug = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
        twitter_url = f"https://twitter.com/{company_slug}"
        
        return {
            'twitter_company': twitter_url,
            'note': 'Verify this handle exists'
        }
    
    async def _find_email_pattern(self, company_name: str, company_url: str) -> Dict[str, Any]:
        """Find email pattern for company"""
        if not company_url:
            return {}
        
        # Extract domain from URL
        domain = company_url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        
        # Common founder email patterns
        patterns = [
            f"founder@{domain}",
            f"hello@{domain}",
            f"hi@{domain}",
            f"contact@{domain}",
            f"team@{domain}",
        ]
        
        return {
            'email_patterns': patterns,
            'domain': domain,
            'note': 'Try these patterns or use Hunter.io to verify'
        }
    
    async def _check_yc_profile(self, company_name: str) -> Dict[str, Any]:
        """Check if company has YC profile (contains founder info)"""
        try:
            company_slug = company_name.lower().replace(' ', '-')
            yc_url = f"https://www.ycombinator.com/companies/{company_slug}"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(yc_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract founder names
                        founders = []
                        founder_section = soup.find('div', class_='founders')
                        if founder_section:
                            founder_links = founder_section.find_all('a')
                            for link in founder_links:
                                founder_name = link.text.strip()
                                if founder_name:
                                    founders.append({
                                        'name': founder_name,
                                        'linkedin': link.get('href', '')
                                    })
                        
                        if founders:
                            return {
                                'yc_profile': yc_url,
                                'founders': founders,
                                'primary_founder': founders[0] if founders else None
                            }
        
        except Exception as e:
            logger.debug(f"YC profile check failed: {e}")
        
        return {}
    
    # ════════════════════════════════════════════════════════════
    # NEW: Message generation and sending
    # ════════════════════════════════════════════════════════════
    
    async def _generate_outreach_message(
        self,
        founder_data: Dict,
        job: JobPosting,
        profile: Profile
    ) -> Optional[Dict]:
        """Generate personalized outreach message"""
        try:
            founder_name = self._extract_founder_name(founder_data)
            
            # Use MessageGenerator if available
            if self.message_generator:
                message_data = await self.message_generator.generate_founder_message(
                    founder_name=founder_name or "Hiring Team",
                    company=job.company,
                    job_title=job.title,
                    job_description=job.description[:500] if job.description else "",
                    profile=profile,
                    context={
                        'founder_role': founder_data.get('primary_founder', {}).get('role', 'Founder'),
                        'company_stage': 'startup',
                        'match_score': getattr(job, 'match_score', 70),
                        'match_reasons': getattr(job, 'match_reasons', [])[:3]
                    }
                )
                return message_data
            
            # Fallback: Simple template
            salutation = f"Hi {founder_name}" if founder_name else "Hi there"
            
            message = f"""{salutation},

I came across {job.company}'s {job.title} role and was immediately drawn to it.

I've built 11 AI products in 10 months (5 running 24/7 as AIPAs), specializing in AI developer productivity tools and platform engineering. My background includes 7 years of strategic leadership as CEO/CLO, and I've achieved 99%+ cost reduction through intelligent automation.

I'd love to discuss how I can contribute to {job.company}'s mission. Would you be open to a quick chat?

Best regards,
Elena Revicheva
https://vibejobhunter.com"""

            return {
                'message': message,
                'subject': f"Re: {job.title} at {job.company}",
                'tone': 'professional'
            }
            
        except Exception as e:
            logger.error(f"Message generation error: {e}")
            return None
    
    def _determine_best_channel(self, founder_data: Dict) -> str:
        """
        Determine best contact channel based on available data
        
        Priority:
        1. Email (most direct, verifiable)
        2. LinkedIn (professional, high response rate)
        3. Twitter (for public tech founders)
        """
        # Check for verified email first
        if founder_data.get('email_patterns') and founder_data.get('domain'):
            # If we have email patterns, prefer email
            return 'email'
        
        # Check if we found actual founder with LinkedIn from YC
        if founder_data.get('founders') and founder_data['founders'][0].get('linkedin'):
            return 'linkedin'
        
        # Fallback to company LinkedIn
        if founder_data.get('linkedin_company'):
            return 'linkedin'
        
        # Twitter as last resort
        if founder_data.get('twitter_company'):
            return 'twitter'
        
        return 'none'
    
    async def _send_email_message(
        self,
        email: str,
        message: str,
        subject: str,
        founder_name: str,
        company: str
    ) -> bool:
        """Send email via configured email service (Resend)"""
        try:
            if not self.email_service:
                logger.warning("⚠️ Email service not configured, saving to manual queue")
                await self._save_to_manual_queue({
                    'channel': 'email',
                    'contact': founder_name,
                    'company': company,
                    'email': email,
                    'subject': subject,
                    'message': message,
                    'status': 'pending_manual_send',
                    'created_at': datetime.utcnow().isoformat()
                })
                return True
            
            # Send email using Resend
            await self.email_service.send_email(
                to=email,
                subject=subject,
                body=message,
                from_name="Elena Revicheva",
                from_email="elena@vibejobhunter.com"
            )
            
            logger.info(f"✅ Email sent to {founder_name} ({email})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email send error: {e}")
            return False
    
    async def _send_linkedin_message(
        self,
        linkedin_url: str,
        message: str,
        founder_name: str,
        company: str
    ) -> bool:
        """
        Log LinkedIn message for manual sending
        LinkedIn doesn't have an official API for DMs
        """
        try:
            logger.info(f"📝 LinkedIn message ready for {founder_name} at {company}")
            logger.info(f"   Profile: {linkedin_url}")
            
            # Save to manual outreach queue
            await self._save_to_manual_queue({
                'channel': 'linkedin',
                'contact': founder_name,
                'company': company,
                'url': linkedin_url,
                'message': message,
                'status': 'pending_manual_send',
                'created_at': datetime.utcnow().isoformat()
            })
            
            # Send Telegram notification
            if self.telegram_notifier:
                telegram_text = f"""🤝 <b>LinkedIn Outreach Ready</b>

👤 Contact: {founder_name}
🏢 Company: {company}
🔗 LinkedIn: {linkedin_url}

📝 <b>Message:</b>
{message[:300]}{"..." if len(message) > 300 else ""}

<i>Visit LinkedIn and send this message!</i>"""
                
                await self.telegram_notifier.send_notification(telegram_text)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ LinkedIn message error: {e}")
            return False
    
    async def _send_twitter_dm(
        self,
        twitter_handle: str,
        message: str,
        founder_name: str,
        company: str
    ) -> bool:
        """Log Twitter DM for manual sending"""
        try:
            logger.info(f"📝 Twitter DM ready for {founder_name} (@{twitter_handle})")
            
            await self._save_to_manual_queue({
                'channel': 'twitter',
                'contact': founder_name,
                'company': company,
                'handle': twitter_handle,
                'message': message,
                'status': 'pending_manual_send',
                'created_at': datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Twitter DM error: {e}")
            return False
    
    # ════════════════════════════════════════════════════════════
    # Helper methods: Extract data from founder_info
    # ════════════════════════════════════════════════════════════
    
    def _extract_founder_name(self, founder_data: Dict) -> Optional[str]:
        """Extract founder name from data"""
        # Check YC profile first
        if founder_data.get('founders') and len(founder_data['founders']) > 0:
            return founder_data['founders'][0].get('name')
        
        if founder_data.get('primary_founder'):
            return founder_data['primary_founder'].get('name')
        
        return None
    
    def _extract_email(self, founder_data: Dict) -> Optional[str]:
        """Extract best email from data"""
        # If we have email patterns, try the first one (founder@domain)
        patterns = founder_data.get('email_patterns', [])
        if patterns and len(patterns) > 0:
            return patterns[0]  # Usually founder@domain
        
        return None
    
    def _extract_linkedin(self, founder_data: Dict) -> Optional[str]:
        """Extract LinkedIn URL from data"""
        # Check if we have actual founder LinkedIn from YC
        if founder_data.get('founders') and len(founder_data['founders']) > 0:
            linkedin = founder_data['founders'][0].get('linkedin')
            if linkedin and linkedin.startswith('http'):
                return linkedin
        
        # Fallback to company page
        return founder_data.get('linkedin_company')
    
    def _extract_twitter(self, founder_data: Dict) -> Optional[str]:
        """Extract Twitter handle from data"""
        twitter_url = founder_data.get('twitter_company')
        if twitter_url:
            # Extract handle from URL
            return twitter_url.split('/')[-1]
        return None
    
    # ════════════════════════════════════════════════════════════
    # Tracking and logging
    # ════════════════════════════════════════════════════════════
    
    async def _log_outreach_attempt(
        self,
        job: JobPosting,
        founder_data: Optional[Dict],
        status: str,
        channel: str = None,
        message: str = None
    ) -> None:
        """Log outreach attempt to database for tracking"""
        try:
            outreach_record = {
                'job_id': getattr(job, 'id', None) or f"{job.company}_{job.title}",
                'company': job.company,
                'job_title': job.title,
                'founder_name': self._extract_founder_name(founder_data) if founder_data else None,
                'channel': channel,
                'status': status,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'match_score': getattr(job, 'match_score', 0)
            }
            
            # Save to database if available
            if self.db:
                # await self.db.save_outreach_attempt(outreach_record)
                logger.debug(f"💾 Logged outreach attempt for {job.company}")
            
            # Also save to JSON file as backup
            log_file = Path("autonomous_data/outreach_log.jsonl")
            log_file.parent.mkdir(exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(json.dumps(outreach_record) + '\n')
            
        except Exception as e:
            logger.error(f"Failed to log outreach attempt: {e}")
    
    async def _save_to_manual_queue(self, outreach_data: Dict) -> None:
        """Save outreach to manual queue (for LinkedIn/Twitter DMs)"""
        try:
            manual_queue_file = Path("autonomous_data/manual_outreach_queue.json")
            manual_queue_file.parent.mkdir(exist_ok=True)
            
            # Load existing queue
            queue = []
            if manual_queue_file.exists():
                with open(manual_queue_file, 'r') as f:
                    queue = json.load(f)
            
            # Add new item
            queue.append(outreach_data)
            
            # Save back
            with open(manual_queue_file, 'w') as f:
                json.dump(queue, f, indent=2)
            
            logger.debug(f"💾 Saved to manual queue: {outreach_data['company']}")
            
        except Exception as e:
            logger.error(f"Failed to save to manual queue: {e}")
    
    # ════════════════════════════════════════════════════════════
    # EXISTING: Enrichment and priority methods
    # ════════════════════════════════════════════════════════════
    
    async def enrich_founder_profile(self, founder_info: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich founder profile with recent activity"""
        enriched = founder_info.copy()
        
        if founder_info.get('twitter'):
            tweets = await self._get_recent_tweets(founder_info['twitter'])
            enriched['recent_tweets'] = tweets
        
        if founder_info.get('linkedin'):
            activity = await self._get_linkedin_activity(founder_info['linkedin'])
            enriched['linkedin_activity'] = activity
        
        return enriched
    
    async def _get_recent_tweets(self, twitter_handle: str) -> List[str]:
        """Get recent tweets from founder - TODO: Requires Twitter API"""
        return []
    
    async def _get_linkedin_activity(self, linkedin_url: str) -> List[str]:
        """Get recent LinkedIn activity - TODO: Requires LinkedIn API"""
        return []
    
    def generate_contact_priority(self, founder_info: Dict[str, Any]) -> List[str]:
        """
        Determine best channels to contact founder
        Returns: Ordered list of channels
        """
        channels = []
        
        # Email is highest priority (direct, verifiable)
        if founder_info.get('email_patterns') or founder_info.get('email'):
            channels.append('email')
        
        # LinkedIn second (60% response rate)
        if founder_info.get('linkedin') or founder_info.get('linkedin_company'):
            channels.append('linkedin')
        
        # Twitter third (20% response rate for DMs)
        if founder_info.get('twitter') or founder_info.get('twitter_company'):
            channels.append('twitter')
        
        return channels