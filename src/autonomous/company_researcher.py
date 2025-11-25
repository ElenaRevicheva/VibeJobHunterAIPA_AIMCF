"""
🔬 COMPANY RESEARCHER
AI-powered company intelligence gathering.
Researches companies before outreach to personalize messages.
"""

import asyncio
import logging
from typing import Dict, Any
import aiohttp
from bs4 import BeautifulSoup
import anthropic
from datetime import datetime

from ..core.config import settings
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

logger = setup_logger(__name__)


class CompanyResearcher:
    """
    AI-powered company intelligence
    Gathers context to make outreach hyper-relevant
    """

    def __init__(self):
        from pathlib import Path
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        logger.info("🔬 Company Researcher initialized")

    async def research_company(self, company_name: str, company_url: str) -> Dict[str, Any]:
        """
        Deep research on a company
        Returns: funding, tech stack, recent news, pain points, founder info
        """
        logger.info(f"🔬 Researching {company_name}...")

        cache_key = f"company_research_{company_name.lower().replace(' ', '_')}"
        cached = None  # TODO: Fix cache compatibility
        if cached and (datetime.now() - datetime.fromisoformat(cached.get('timestamp', datetime.now().isoformat()))).days < 7:
            logger.info(f"✅ Using cached research for {company_name}")
            return cached

        intel = {
            'company_name': company_name,
            'url': company_url,
            'timestamp': datetime.now().isoformat(),
        }

        # Gather intelligence from multiple sources
        tasks = [
            self._scrape_company_website(company_url),
            self._search_crunchbase_info(company_name),
            self._get_recent_news(company_name),
            self._analyze_tech_stack(company_url),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        for i, key in enumerate(['website_data', 'funding_data', 'news', 'tech_stack']):
            if not isinstance(results[i], Exception):
                intel[key] = results[i]
            else:
                logger.debug(f"Failed to get {key}: {results[i]}")
                intel[key] = {}

        # AI Analysis: Synthesize insights
        intel['ai_insights'] = await self._analyze_with_ai(intel)

        # Cache for 7 days
        self.cache.set(cache_key, intel)

        logger.info(f"✅ Research complete for {company_name}")
        return intel

    async def _scrape_company_website(self, url: str) -> Dict[str, Any]:
        """Scrape company website for basic info"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        return {
                            'title': soup.title.string if soup.title else '',
                            'description': soup.find('meta', attrs={'name': 'description'})['content']
                                           if soup.find('meta', attrs={'name': 'description'}) else '',
                            'about_text': self._extract_about_text(soup),
                            'keywords': self._extract_keywords(soup),
                        }
        except Exception as e:
            logger.debug(f"Failed to scrape website: {e}")
        return {}

    def _extract_about_text(self, soup) -> str:
        """Extract 'about' text from website"""
        about_keywords = ['about', 'mission', 'who we are', 'what we do']
        for keyword in about_keywords:
            section = soup.find(text=lambda t: keyword in t.lower() if t else False)
            if section:
                parent = section.find_parent()
                if parent:
                    return parent.get_text()[:500]
        return ""

    def _extract_keywords(self, soup) -> list:
        """Extract relevant keywords from page"""
        text = soup.get_text().lower()
        tech_keywords = ['ai', 'machine learning', 'llm', 'gpt', 'claude', 'nlp', 
                         'web3', 'blockchain', 'saas', 'b2b', 'b2c', 'startup']
        return [keyword for keyword in tech_keywords if keyword in text]

    async def _search_crunchbase_info(self, company_name: str) -> Dict[str, Any]:
        """Search for funding info (placeholder)"""
        return {
            'funding_stage': 'Seed / Series A (estimated)',
            'note': 'Estimated based on YC/Wellfound listing'
        }

    async def _get_recent_news(self, company_name: str) -> Dict[str, Any]:
        """Get recent company news (placeholder)"""
        return {
            'recent_mentions': [],
            'note': 'News integration pending'
        }

    async def _analyze_tech_stack(self, url: str) -> Dict[str, Any]:
        """Analyze company's tech stack from website HTML"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        tech_indicators = {
                            'react': 'react' in html.lower(),
                            'vue': 'vue' in html.lower(),
                            'python': 'python' in html.lower(),
                            'nodejs': 'node' in html.lower() or 'nodejs' in html.lower(),
                            'typescript': 'typescript' in html.lower(),
                        }
                        detected = [tech for tech, found in tech_indicators.items() if found]
                        return {'detected_technologies': detected, 'confidence': 'low'}
        except Exception as e:
            logger.debug(f"Failed to analyze tech stack: {e}")
        return {}

    async def _analyze_with_ai(self, intel: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude to synthesize insights and generate talking points"""
        try:
            company_data = f"""
Company: {intel['company_name']}
Website: {intel.get('website_data', {}).get('description', '')}
About: {intel.get('website_data', {}).get('about_text', '')}
Keywords: {', '.join(intel.get('website_data', {}).get('keywords', []))}
Tech Stack: {', '.join(intel.get('tech_stack', {}).get('detected_technologies', []))}
"""
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-sonnet-4-20250514",  # Updated model
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this company and provide insights for personalized outreach.

{company_data}

Provide:
1. Main value proposition (1 sentence)
2. Likely pain points Elena could solve (3 points)
3. Best hook for initial message (specific!)
4. Estimated company stage (Seed/Series A/etc)

Format as JSON."""
                }]
            )

            response_text = message.content[0].text

            import json
            try:
                insights = json.loads(response_text)
                return insights
            except:
                return {'raw_insights': response_text, 'value_proposition': response_text[:200]}

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {'error': str(e), 'fallback': f"AI startup in {intel.get('website_data', {}).get('keywords', ['tech'])}"}

