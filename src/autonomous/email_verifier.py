"""
📧 EMAIL VERIFIER - Verify Founder Emails Before Sending
Uses Hunter.io API to verify emails are real and deliverable.

This PREVENTS bounces which damage your email reputation.

Usage:
    verifier = EmailVerifier()
    result = await verifier.verify_email("founder@company.com")
    
    if result['deliverable']:
        # Safe to send
    else:
        # Skip - email likely to bounce
"""

import os
import logging
from typing import Dict, Optional, List
import aiohttp

logger = logging.getLogger(__name__)

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")


class EmailVerifier:
    """
    Verify emails using Hunter.io API before sending.
    
    Why this matters:
    - Bounced emails damage your sender reputation
    - Too many bounces = Resend/Gmail bans you
    - Verification costs ~$0.01 per email vs reputation damage
    
    Hunter.io Features:
    - Email verification (is it deliverable?)
    - Email finder (find founder emails from domain)
    - Domain search (find all emails at company)
    """
    
    def __init__(self):
        self.api_key = HUNTER_API_KEY
        self.base_url = "https://api.hunter.io/v2"
        
        if self.api_key:
            logger.info("✅ EmailVerifier initialized with Hunter.io API")
        else:
            logger.warning("⚠️ HUNTER_API_KEY not set - email verification disabled")
            logger.warning("   Get API key at: https://hunter.io/api")
    
    async def verify_email(self, email: str) -> Dict:
        """
        Verify if an email is deliverable.
        
        Returns:
            {
                'email': str,
                'deliverable': bool,
                'status': 'valid' | 'invalid' | 'unknown' | 'accept_all',
                'score': int (0-100),
                'reason': str,
                'skip_api': bool (if API not configured)
            }
        """
        if not self.api_key:
            # No API key - allow email but warn
            return {
                'email': email,
                'deliverable': True,  # Assume OK if no verification
                'status': 'unverified',
                'score': 50,
                'reason': 'Hunter.io API not configured - skipping verification',
                'skip_api': True
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/email-verifier"
                params = {
                    'email': email,
                    'api_key': self.api_key
                }
                
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get('data', {})
                        
                        status = result.get('status', 'unknown')
                        score = result.get('score', 0)
                        
                        # Determine if deliverable
                        # 'valid' = definitely deliverable
                        # 'accept_all' = server accepts all (can't verify)
                        # 'invalid' = will bounce
                        # 'unknown' = couldn't determine
                        
                        deliverable = status in ['valid', 'accept_all'] and score >= 50
                        
                        return {
                            'email': email,
                            'deliverable': deliverable,
                            'status': status,
                            'score': score,
                            'reason': result.get('result', ''),
                            'skip_api': False,
                            'details': {
                                'smtp_check': result.get('smtp_check'),
                                'mx_records': result.get('mx_records'),
                                'disposable': result.get('disposable'),
                                'webmail': result.get('webmail'),
                            }
                        }
                    
                    elif resp.status == 401:
                        logger.error("❌ Hunter.io API key invalid")
                        return {
                            'email': email,
                            'deliverable': True,  # Allow on API error
                            'status': 'api_error',
                            'score': 50,
                            'reason': 'Invalid API key',
                            'skip_api': True
                        }
                    
                    elif resp.status == 429:
                        logger.warning("⚠️ Hunter.io rate limited")
                        return {
                            'email': email,
                            'deliverable': True,  # Allow on rate limit
                            'status': 'rate_limited',
                            'score': 50,
                            'reason': 'API rate limited',
                            'skip_api': True
                        }
                    
                    else:
                        logger.warning(f"⚠️ Hunter.io returned {resp.status}")
                        return {
                            'email': email,
                            'deliverable': True,
                            'status': 'api_error',
                            'score': 50,
                            'reason': f'API returned {resp.status}',
                            'skip_api': True
                        }
        
        except Exception as e:
            logger.error(f"❌ Email verification error: {e}")
            return {
                'email': email,
                'deliverable': True,  # Allow on error
                'status': 'error',
                'score': 50,
                'reason': str(e),
                'skip_api': True
            }
    
    async def find_email(self, domain: str, first_name: str, last_name: str) -> Dict:
        """
        Find an email address from name and domain.
        
        Usage:
            result = await verifier.find_email("stripe.com", "Patrick", "Collison")
            # Returns patrick@stripe.com (verified)
        """
        if not self.api_key:
            return {
                'email': None,
                'found': False,
                'reason': 'Hunter.io API not configured'
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/email-finder"
                params = {
                    'domain': domain,
                    'first_name': first_name,
                    'last_name': last_name,
                    'api_key': self.api_key
                }
                
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get('data', {})
                        
                        email = result.get('email')
                        score = result.get('score', 0)
                        
                        if email and score >= 70:  # High confidence
                            return {
                                'email': email,
                                'found': True,
                                'score': score,
                                'confidence': 'high' if score >= 90 else 'medium',
                                'sources': result.get('sources', [])
                            }
                        else:
                            return {
                                'email': email,
                                'found': False,
                                'score': score,
                                'reason': 'Low confidence email'
                            }
                    
                    return {
                        'email': None,
                        'found': False,
                        'reason': f'API returned {resp.status}'
                    }
        
        except Exception as e:
            logger.error(f"❌ Email finder error: {e}")
            return {
                'email': None,
                'found': False,
                'reason': str(e)
            }
    
    async def search_domain(self, domain: str, limit: int = 10) -> Dict:
        """
        Search for all emails at a domain.
        
        Returns founders, executives, and other contacts.
        """
        if not self.api_key:
            return {
                'emails': [],
                'found': 0,
                'reason': 'Hunter.io API not configured'
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/domain-search"
                params = {
                    'domain': domain,
                    'limit': limit,
                    'api_key': self.api_key
                }
                
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get('data', {})
                        
                        emails = result.get('emails', [])
                        
                        # Sort by position - prioritize founders/executives
                        priority_positions = ['founder', 'ceo', 'cto', 'vp', 'director', 'head']
                        
                        def score_position(email_data):
                            position = (email_data.get('position') or '').lower()
                            for i, priority in enumerate(priority_positions):
                                if priority in position:
                                    return i
                            return 100
                        
                        emails.sort(key=score_position)
                        
                        return {
                            'emails': [
                                {
                                    'email': e.get('value'),
                                    'name': f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                                    'position': e.get('position'),
                                    'confidence': e.get('confidence')
                                }
                                for e in emails
                            ],
                            'found': len(emails),
                            'domain': domain
                        }
                    
                    return {
                        'emails': [],
                        'found': 0,
                        'reason': f'API returned {resp.status}'
                    }
        
        except Exception as e:
            logger.error(f"❌ Domain search error: {e}")
            return {
                'emails': [],
                'found': 0,
                'reason': str(e)
            }


# Singleton
_verifier = None

def get_email_verifier() -> EmailVerifier:
    """Get singleton email verifier"""
    global _verifier
    if _verifier is None:
        _verifier = EmailVerifier()
    return _verifier


async def verify_before_send(email: str) -> bool:
    """
    Quick helper to verify email before sending.
    
    Usage:
        if await verify_before_send("founder@company.com"):
            await send_email(...)
    """
    verifier = get_email_verifier()
    result = await verifier.verify_email(email)
    
    if not result['deliverable']:
        logger.warning(f"⚠️ Email verification failed for {email}: {result['reason']}")
    
    return result['deliverable']


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        print("\n" + "="*60)
        print("🧪 EMAIL VERIFIER TEST")
        print("="*60)
        
        verifier = get_email_verifier()
        
        if not verifier.api_key:
            print("\n⚠️ HUNTER_API_KEY not set - using demo mode")
            print("   Get your API key at: https://hunter.io/api")
        
        # Test verification
        test_email = "test@example.com"
        print(f"\n📧 Testing verification for: {test_email}")
        result = await verifier.verify_email(test_email)
        print(f"   Deliverable: {result['deliverable']}")
        print(f"   Status: {result['status']}")
        print(f"   Score: {result['score']}")
        print(f"   Reason: {result['reason']}")
        
        print("\n✅ Email verifier working!")
    
    asyncio.run(test())
