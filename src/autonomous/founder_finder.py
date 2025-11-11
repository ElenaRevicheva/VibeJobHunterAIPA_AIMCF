"""
👤 FOUNDER FINDER
Finds founder contact information (LinkedIn, Twitter, Email).
Uses multiple data sources to build complete founder profiles.
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
import aiohttp
from bs4 import BeautifulSoup

from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

logger = setup_logger(__name__)


class FounderFinder:
    """
    Finds and profiles company founders
    Discovers: LinkedIn, Twitter, Email, recent activity
    """
    
    def __init__(self):
        from pathlib import Path
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        logger.info("👤 Founder Finder initialized")
    
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
        if not any([founder_info.get('linkedin'), founder_info.get('twitter'), founder_info.get('email')]):
            logger.warning(f"⚠️ No contact info found for {company_name}")
            return None
        
        # Cache for 30 days
        self.cache.set(cache_key, founder_info, ttl=2592000)
        
        logger.info(f"✅ Found founder info for {company_name}")
        return founder_info
    
    async def _search_linkedin(self, company_name: str) -> Dict[str, Any]:
        """
        Search for founder LinkedIn profile
        Note: This is simplified - real implementation would use LinkedIn Sales Navigator API
        or Phantombuster
        """
        # TODO: Implement LinkedIn Sales Navigator / Phantombuster integration
        
        # For now, construct likely LinkedIn company page URL
        company_slug = company_name.lower().replace(' ', '-').replace(',', '').replace('.', '')
        linkedin_url = f"https://www.linkedin.com/company/{company_slug}"
        
        return {
            'linkedin_company': linkedin_url,
            'note': 'Use Phantombuster to extract founder profile'
        }
    
    async def _search_twitter(self, company_name: str) -> Dict[str, Any]:
        """
        Search for founder Twitter/X profile
        """
        # Construct likely Twitter handle
        company_slug = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
        twitter_url = f"https://twitter.com/{company_slug}"
        
        return {
            'twitter_company': twitter_url,
            'note': 'Verify this handle exists'
        }
    
    async def _find_email_pattern(self, company_name: str, company_url: str) -> Dict[str, Any]:
        """
        Find email pattern for company
        """
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
        """
        Check if company has YC profile (contains founder info)
        """
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
    
    async def enrich_founder_profile(self, founder_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich founder profile with recent activity
        """
        enriched = founder_info.copy()
        
        # Get recent tweets if Twitter handle exists
        if founder_info.get('twitter'):
            tweets = await self._get_recent_tweets(founder_info['twitter'])
            enriched['recent_tweets'] = tweets
        
        # Get LinkedIn activity if profile exists
        if founder_info.get('linkedin'):
            activity = await self._get_linkedin_activity(founder_info['linkedin'])
            enriched['linkedin_activity'] = activity
        
        return enriched
    
    async def _get_recent_tweets(self, twitter_handle: str) -> List[str]:
        """
        Get recent tweets from founder
        Note: Requires Twitter API access
        """
        # TODO: Implement Twitter API integration
        return []
    
    async def _get_linkedin_activity(self, linkedin_url: str) -> List[str]:
        """
        Get recent LinkedIn activity
        Note: Requires LinkedIn API / Phantombuster
        """
        # TODO: Implement LinkedIn activity scraping
        return []
    
    def generate_contact_priority(self, founder_info: Dict[str, Any]) -> List[str]:
        """
        Determine best channels to contact founder
        Returns: Ordered list of channels
        """
        channels = []
        
        # LinkedIn is highest priority (60% response rate)
        if founder_info.get('linkedin'):
            channels.append('linkedin')
        
        # Email second (30% response rate)
        if founder_info.get('email') or founder_info.get('email_patterns'):
            channels.append('email')
        
        # Twitter third (20% response rate for DMs)
        if founder_info.get('twitter'):
            channels.append('twitter')
        
        return channels
