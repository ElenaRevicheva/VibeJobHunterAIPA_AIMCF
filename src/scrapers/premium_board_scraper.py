"""
🏆 PREMIUM JOB BOARD SCRAPER - YC Advantage & Remote-First Radar

High-quality job sources that deserve special treatment:
1. YC Work at a Startup (workatastartup.com) - +15 score boost, warm outreach
2. DynamiteJobs (dynamitejobs.com) - Remote-first AI/ML roles

These are PREMIUM sources - jobs from here get priority treatment!

Author: VibeJobHunter Premium Features
Date: January 2026
"""

import asyncio
import aiohttp
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Any, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# =====================================
# PREMIUM SOURCE CONFIGURATION
# =====================================

PREMIUM_SOURCES = {
    "yc": {
        "name": "YC Work at a Startup",
        "url": "https://www.workatastartup.com",
        "score_boost": 15,  # +15 points for YC companies!
        "warm_intro": True,
    },
    "dynamite": {
        "name": "DynamiteJobs",
        "url": "https://dynamitejobs.com",
        "score_boost": 5,  # +5 for remote-first quality
        "warm_intro": False,
    }
}

# Keywords to filter for AI/ML/Founding roles
AI_KEYWORDS = [
    "ai", "ml", "machine learning", "llm", "gpt", "claude", "nlp",
    "deep learning", "neural", "data scientist", "ai engineer",
    "founding engineer", "founding", "first engineer", "0-1",
    "full stack", "fullstack", "backend", "python", "typescript"
]

# Remote-friendly location patterns
REMOTE_PATTERNS = [
    r"remote",
    r"anywhere",
    r"distributed",
    r"work from home",
    r"wfh",
    r"global",
    r"worldwide",
    r"latam",
    r"americas",
]


class PremiumBoardScraper:
    """
    Scrape high-quality job boards for premium opportunities.
    
    Features:
    - YC Work at a Startup scraping with YC badge
    - DynamiteJobs remote-first roles
    - Special flags for premium source tracking
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.yc_companies: Set[str] = set()  # Track YC companies for cross-reference
        
        # Statistics
        self.stats = {
            "yc_jobs": 0,
            "dynamite_jobs": 0,
            "yc_companies_found": 0,
            "remote_jobs": 0,
            "ai_ml_jobs": 0,
            "errors": []
        }
        
        logger.info("🏆 Premium Board Scraper initialized (YC + DynamiteJobs)")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    # =====================================
    # YC WORK AT A STARTUP SCRAPER
    # =====================================
    
    async def fetch_yc_jobs(self, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch jobs from YC Work at a Startup.
        
        YC's job board uses their API internally. We'll use the public job listings.
        URL: https://www.workatastartup.com/jobs
        
        Returns jobs with is_yc_company=True for score boosting.
        """
        jobs = []
        keywords = keywords or ["ai", "ml", "founding", "engineer"]
        
        # YC has a JSON API endpoint
        api_url = "https://www.workatastartup.com/api/jobs"
        
        try:
            if not self.session:
                logger.warning("No session available for YC scraper")
                return []
            
            # Try the main jobs page with filters
            for keyword in keywords[:3]:  # Limit to avoid rate limiting
                search_url = f"https://www.workatastartup.com/jobs?query={keyword}"
                
                async with self.session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        parsed_jobs = self._parse_yc_html(html, keyword)
                        jobs.extend(parsed_jobs)
                        logger.info(f"🏆 YC: Found {len(parsed_jobs)} jobs for '{keyword}'")
                    else:
                        logger.warning(f"YC search returned {response.status} for '{keyword}'")
                
                await asyncio.sleep(1)  # Be nice to their servers
            
            # Deduplicate by job ID
            seen_ids = set()
            unique_jobs = []
            for job in jobs:
                if job.get("id") not in seen_ids:
                    seen_ids.add(job.get("id"))
                    unique_jobs.append(job)
            
            self.stats["yc_jobs"] = len(unique_jobs)
            logger.info(f"🏆 YC Total: {len(unique_jobs)} unique jobs from Work at a Startup")
            
            return unique_jobs
            
        except Exception as e:
            logger.error(f"YC scraper error: {e}")
            self.stats["errors"].append(f"yc:{str(e)}")
            return []
    
    def _parse_yc_html(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """Parse YC job listings from HTML"""
        jobs = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # YC uses specific class patterns for job cards
            # Look for job listing containers
            job_cards = soup.find_all(['div', 'a'], class_=re.compile(r'job|listing|posting', re.I))
            
            # Also try data attributes
            if not job_cards:
                job_cards = soup.find_all(attrs={"data-job": True})
            
            # Try finding links to job postings
            job_links = soup.find_all('a', href=re.compile(r'/jobs/\d+|/companies/.+/jobs'))
            
            for link in job_links[:50]:  # Limit to first 50
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # Extract job ID from URL
                    job_id_match = re.search(r'/jobs/(\d+)', href)
                    job_id = job_id_match.group(1) if job_id_match else href.split('/')[-1]
                    
                    # Get job title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    
                    # Try to find company name from context
                    parent = link.find_parent(['div', 'li', 'article'])
                    company = ""
                    if parent:
                        company_elem = parent.find(class_=re.compile(r'company|startup', re.I))
                        if company_elem:
                            company = company_elem.get_text(strip=True)
                    
                    # Build full URL
                    full_url = href if href.startswith('http') else f"https://www.workatastartup.com{href}"
                    
                    # Check if it's relevant (AI/ML/Founding)
                    combined_text = f"{title} {company}".lower()
                    is_relevant = any(kw in combined_text for kw in AI_KEYWORDS)
                    
                    if is_relevant or keyword.lower() in combined_text:
                        jobs.append({
                            "id": f"yc_{job_id}",
                            "title": title,
                            "company": company or "YC Startup",
                            "location": "Remote / US",  # Most YC jobs are remote-friendly
                            "url": full_url,
                            "source": "yc_workatastartup",
                            "is_yc_company": True,
                            "is_premium_source": True,
                            "score_boost": PREMIUM_SOURCES["yc"]["score_boost"],
                            "description": f"YC-backed startup. {title} at {company}.",
                            "posted_date": datetime.now().isoformat(),
                            "remote_allowed": True,
                        })
                        
                        # Track YC company
                        if company:
                            self.yc_companies.add(company.lower())
                            
                except Exception as e:
                    continue
            
            self.stats["yc_companies_found"] = len(self.yc_companies)
            
        except Exception as e:
            logger.error(f"YC HTML parsing error: {e}")
        
        return jobs
    
    # =====================================
    # DYNAMITEJOBS SCRAPER (Remote-First)
    # =====================================
    
    async def fetch_dynamite_jobs(self, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch remote AI/ML jobs from DynamiteJobs.
        
        DynamiteJobs specializes in remote positions - perfect for Panama timezone.
        URL: https://dynamitejobs.com
        """
        jobs = []
        keywords = keywords or ["ai", "machine learning", "llm", "founding engineer"]
        
        try:
            if not self.session:
                logger.warning("No session available for DynamiteJobs scraper")
                return []
            
            # DynamiteJobs has category-based URLs
            categories = [
                "engineering",
                "data",
                "product",
            ]
            
            for category in categories:
                url = f"https://dynamitejobs.com/remote-{category}-jobs"
                
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            parsed_jobs = self._parse_dynamite_html(html, keywords)
                            jobs.extend(parsed_jobs)
                            logger.info(f"🌐 DynamiteJobs: Found {len(parsed_jobs)} {category} jobs")
                        else:
                            logger.debug(f"DynamiteJobs {category} returned {response.status}")
                except Exception as e:
                    logger.debug(f"DynamiteJobs {category} error: {e}")
                
                await asyncio.sleep(0.5)
            
            # Deduplicate
            seen_ids = set()
            unique_jobs = []
            for job in jobs:
                if job.get("id") not in seen_ids:
                    seen_ids.add(job.get("id"))
                    unique_jobs.append(job)
            
            # Filter for AI/ML keywords
            ai_jobs = [j for j in unique_jobs if self._is_ai_relevant(j)]
            
            self.stats["dynamite_jobs"] = len(unique_jobs)
            self.stats["ai_ml_jobs"] = len(ai_jobs)
            self.stats["remote_jobs"] = len([j for j in unique_jobs if j.get("remote_allowed")])
            
            logger.info(f"🌐 DynamiteJobs Total: {len(ai_jobs)} AI/ML relevant jobs")
            
            return ai_jobs
            
        except Exception as e:
            logger.error(f"DynamiteJobs scraper error: {e}")
            self.stats["errors"].append(f"dynamite:{str(e)}")
            return []
    
    def _parse_dynamite_html(self, html: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Parse DynamiteJobs listings"""
        jobs = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all(['article', 'div'], class_=re.compile(r'job|listing|card', re.I))
            
            # Also look for job links
            job_links = soup.find_all('a', href=re.compile(r'/job/|/jobs/', re.I))
            
            for link in job_links[:50]:
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue
                    
                    # Generate ID from URL
                    job_id = re.sub(r'[^a-zA-Z0-9]', '_', href)[-20:]
                    
                    # Try to find company
                    parent = link.find_parent(['article', 'div', 'li'])
                    company = ""
                    location = "Remote"
                    
                    if parent:
                        company_elem = parent.find(class_=re.compile(r'company|employer', re.I))
                        if company_elem:
                            company = company_elem.get_text(strip=True)
                        
                        location_elem = parent.find(class_=re.compile(r'location|place', re.I))
                        if location_elem:
                            location = location_elem.get_text(strip=True)
                    
                    full_url = href if href.startswith('http') else f"https://dynamitejobs.com{href}"
                    
                    # Check remote status
                    is_remote = any(re.search(p, location.lower()) for p in REMOTE_PATTERNS)
                    
                    jobs.append({
                        "id": f"dj_{job_id}",
                        "title": title,
                        "company": company or "Remote Company",
                        "location": location,
                        "url": full_url,
                        "source": "dynamitejobs",
                        "is_yc_company": False,
                        "is_premium_source": True,
                        "score_boost": PREMIUM_SOURCES["dynamite"]["score_boost"],
                        "description": f"Remote-first position. {title}",
                        "posted_date": datetime.now().isoformat(),
                        "remote_allowed": is_remote or True,  # DynamiteJobs = remote by default
                    })
                    
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"DynamiteJobs HTML parsing error: {e}")
        
        return jobs
    
    def _is_ai_relevant(self, job: Dict[str, Any]) -> bool:
        """Check if job is AI/ML relevant"""
        text = f"{job.get('title', '')} {job.get('description', '')} {job.get('company', '')}".lower()
        return any(kw in text for kw in AI_KEYWORDS)
    
    # =====================================
    # MAIN FETCH METHOD
    # =====================================
    
    async def fetch_all_premium_jobs(
        self, 
        keywords: Optional[List[str]] = None,
        include_yc: bool = True,
        include_dynamite: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch jobs from all premium sources.
        
        Returns jobs with special flags:
        - is_yc_company: True for YC-backed companies
        - is_premium_source: True for all premium board jobs
        - score_boost: Additional points to add to match score
        """
        all_jobs = []
        keywords = keywords or ["ai", "founding engineer", "llm", "ml engineer"]
        
        logger.info("🏆 Starting Premium Board scraping...")
        
        tasks = []
        
        if include_yc:
            tasks.append(self.fetch_yc_jobs(keywords))
        
        if include_dynamite:
            tasks.append(self.fetch_dynamite_jobs(keywords))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_jobs.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Premium scraper error: {result}")
        
        logger.info(f"🏆 Premium Total: {len(all_jobs)} jobs from premium sources")
        logger.info(f"   - YC Jobs: {self.stats['yc_jobs']}")
        logger.info(f"   - DynamiteJobs: {self.stats['dynamite_jobs']}")
        logger.info(f"   - YC Companies Discovered: {self.stats['yc_companies_found']}")
        
        return all_jobs
    
    def is_yc_company(self, company_name: str) -> bool:
        """
        Check if a company is YC-backed.
        
        Can be used to cross-reference jobs from other sources.
        """
        return company_name.lower() in self.yc_companies
    
    def get_score_boost(self, job: Dict[str, Any]) -> int:
        """
        Get the score boost for a premium job.
        
        Returns:
        - 15 for YC companies
        - 5 for other premium sources
        - 0 for non-premium
        """
        if job.get("is_yc_company"):
            return PREMIUM_SOURCES["yc"]["score_boost"]
        elif job.get("is_premium_source"):
            return PREMIUM_SOURCES["dynamite"]["score_boost"]
        return 0
    
    def get_yc_companies(self) -> Set[str]:
        """Return set of discovered YC companies for cross-referencing"""
        return self.yc_companies


# =====================================
# WARM OUTREACH TEMPLATES
# =====================================

YC_WARM_INTRO = """Hi {founder_name},

I saw your {job_title} role on YC's Work at a Startup board. As a solo founder who shipped 11 AI products in 10 months (including AI Co-Founders running 24/7), I'm particularly drawn to YC companies building with urgency.

My EspaLuz tutor serves users in 19 countries, and my CTO AIPA reviews code across 8 repos autonomously. I'd love to bring this same builder energy to {company}.

Try my AI: wa.me/50766623757

Best,
Elena"""

PREMIUM_WARM_INTRO = """Hi {founder_name},

Your {job_title} role caught my attention - the remote-first approach and focus on {focus_area} align perfectly with how I work.

I've built 11 AI products solo (7 live agents), including autonomous AI Co-Founders that run 24/7. My background includes 7 years as Deputy CEO, so I bring both technical depth and business judgment.

Would love to chat about {company}.

Best,
Elena"""


def get_yc_outreach_message(job: Dict[str, Any], founder_name: str = "there") -> str:
    """Generate YC-specific warm outreach message"""
    return YC_WARM_INTRO.format(
        founder_name=founder_name,
        job_title=job.get("title", "role"),
        company=job.get("company", "your company")
    )


def get_premium_outreach_message(job: Dict[str, Any], founder_name: str = "there") -> str:
    """Generate premium source outreach message"""
    # Detect focus area from job
    title_lower = job.get("title", "").lower()
    if "ai" in title_lower or "ml" in title_lower:
        focus_area = "AI/ML"
    elif "founding" in title_lower:
        focus_area = "building from zero"
    else:
        focus_area = "engineering excellence"
    
    return PREMIUM_WARM_INTRO.format(
        founder_name=founder_name,
        job_title=job.get("title", "role"),
        company=job.get("company", "your company"),
        focus_area=focus_area
    )


# Singleton instance
_scraper = None

def get_premium_scraper() -> PremiumBoardScraper:
    """Get the global premium scraper instance"""
    global _scraper
    if _scraper is None:
        _scraper = PremiumBoardScraper()
    return _scraper

