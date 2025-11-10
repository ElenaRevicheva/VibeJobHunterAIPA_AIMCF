"""
🔍 JOB MONITOR
Continuously monitors job boards for new postings.
Focuses on YC, Wellfound (AngelList), and other scraper-friendly sources.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
import aiohttp
from bs4 import BeautifulSoup
import json
from pathlib import Path

from ..core.models import JobPosting, JobSource
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

logger = setup_logger(__name__)


class JobMonitor:
    """
    Monitors job boards 24/7 for new postings
    Specializes in YC, Wellfound, Web3 Career (scraper-friendly sources)
    """
    
    def __init__(self):
        self.cache = ResponseCache()
        self.seen_jobs: Set[str] = set()
        self.last_check: Dict[str, datetime] = {}
        
        # Load seen jobs
        self._load_seen_jobs()
        
        logger.info("🔍 Job Monitor initialized")
    
    def _load_seen_jobs(self):
        """Load previously seen job IDs"""
        seen_file = Path("autonomous_data/seen_jobs.json")
        if seen_file.exists():
            try:
                with open(seen_file, 'r') as f:
                    data = json.load(f)
                    self.seen_jobs = set(data.get('seen_jobs', []))
                    logger.info(f"Loaded {len(self.seen_jobs)} previously seen jobs")
            except Exception as e:
                logger.error(f"Failed to load seen jobs: {e}")
    
    def _save_seen_jobs(self):
        """Save seen job IDs"""
        seen_file = Path("autonomous_data/seen_jobs.json")
        seen_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(seen_file, 'w') as f:
                json.dump({'seen_jobs': list(self.seen_jobs)}, f)
        except Exception as e:
            logger.error(f"Failed to save seen jobs: {e}")
    
    async def find_new_jobs(
        self, 
        target_roles: List[str], 
        max_results: int = 50
    ) -> List[JobPosting]:
        """
        Find new job postings across all sources
        Returns only jobs not seen before
        """
        logger.info(f"🔍 Searching for new jobs (target: {', '.join(target_roles[:3])}...)")
        
        all_jobs = []
        
        # Search all sources in parallel
        tasks = [
            self._search_ycombinator(target_roles),
            self._search_wellfound(target_roles),
            self._search_web3career(target_roles),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Search failed: {result}")
                continue
            all_jobs.extend(result)
        
        # Filter to only new jobs
        new_jobs = []
        for job in all_jobs:
            job_id = self._generate_job_id(job)
            if job_id not in self.seen_jobs:
                new_jobs.append(job)
                self.seen_jobs.add(job_id)
        
        # Save updated seen jobs
        self._save_seen_jobs()
        
        logger.info(f"✅ Found {len(new_jobs)} NEW jobs (filtered from {len(all_jobs)} total)")
        
        return new_jobs[:max_results]
    
    def _generate_job_id(self, job: JobPosting) -> str:
        """Generate unique ID for job"""
        return f"{job.source}_{job.company}_{job.title}".lower().replace(" ", "_")
    
    async def _search_ycombinator(self, target_roles: List[str]) -> List[JobPosting]:
        """
        Search Y Combinator job board
        YC is scraper-friendly!
        """
        logger.info("🔍 Searching Y Combinator...")
        jobs = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # YC Companies API
                url = "https://www.ycombinator.com/companies"
                params = {
                    'batch': 'W25,S25',  # Latest batches
                    'isHiring': 'true',
                    'query': 'AI engineer founding',
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Parse YC company cards
                        company_cards = soup.find_all('div', class_='company')
                        
                        for card in company_cards[:20]:  # Top 20
                            try:
                                job = self._parse_yc_company(card)
                                if job:
                                    jobs.append(job)
                            except Exception as e:
                                logger.debug(f"Failed to parse YC company: {e}")
                    else:
                        logger.warning(f"YC returned status {response.status}")
        
        except Exception as e:
            logger.error(f"YC search failed: {e}")
        
        logger.info(f"✅ Found {len(jobs)} YC jobs")
        return jobs
    
    def _parse_yc_company(self, card) -> Optional[JobPosting]:
        """Parse YC company card into JobPosting"""
        try:
            company_name = card.find('h3').text.strip()
            description = card.find('p', class_='description').text.strip()
            url = "https://www.ycombinator.com" + card.find('a')['href']
            
            # Check if they're hiring for AI/engineering roles
            text = (company_name + " " + description).lower()
            if any(keyword in text for keyword in ['ai', 'ml', 'engineer', 'founding']):
                return JobPosting(
                    title="Founding Engineer / AI Engineer",
                    company=company_name,
                    location="Remote",
                    description=description,
                    source=JobSource.YCOMBINATOR,
                    url=url,
                    posted_date=datetime.now(),
                    remote_allowed=True,
                    requirements=[],
                    responsibilities=[]
                )
        except Exception as e:
            logger.debug(f"Failed to parse YC card: {e}")
        
        return None
    
    async def _search_wellfound(self, target_roles: List[str]) -> List[JobPosting]:
        """
        Search Wellfound (formerly AngelList)
        More scraper-friendly than LinkedIn
        """
        logger.info("🔍 Searching Wellfound...")
        jobs = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Wellfound job search
                url = "https://wellfound.com/role/r/software-engineer"
                params = {
                    'query': 'founding engineer AI',
                    'remote': 'true',
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Parse job listings
                        job_cards = soup.find_all('div', class_='job-listing')
                        
                        for card in job_cards[:15]:  # Top 15
                            try:
                                job = self._parse_wellfound_job(card)
                                if job:
                                    jobs.append(job)
                            except Exception as e:
                                logger.debug(f"Failed to parse Wellfound job: {e}")
                    else:
                        logger.warning(f"Wellfound returned status {response.status}")
        
        except Exception as e:
            logger.error(f"Wellfound search failed: {e}")
        
        logger.info(f"✅ Found {len(jobs)} Wellfound jobs")
        return jobs
    
    def _parse_wellfound_job(self, card) -> Optional[JobPosting]:
        """Parse Wellfound job card"""
        try:
            title = card.find('h2', class_='title').text.strip()
            company = card.find('span', class_='company').text.strip()
            location = card.find('span', class_='location').text.strip()
            description = card.find('p', class_='description').text.strip()
            url = "https://wellfound.com" + card.find('a')['href']
            
            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=description,
                source=JobSource.ANGELLIST,
                url=url,
                posted_date=datetime.now(),
                remote_allowed='remote' in location.lower(),
                requirements=[],
                responsibilities=[]
            )
        except Exception as e:
            logger.debug(f"Failed to parse Wellfound card: {e}")
        
        return None
    
    async def _search_web3career(self, target_roles: List[str]) -> List[JobPosting]:
        """
        Search Web3 Career
        Great for Web3 + AI hybrid roles
        """
        logger.info("🔍 Searching Web3 Career...")
        jobs = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://web3.career/web3-ai-jobs"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Parse job listings
                        job_rows = soup.find_all('tr', class_='job_row')
                        
                        for row in job_rows[:10]:  # Top 10
                            try:
                                job = self._parse_web3_job(row)
                                if job:
                                    jobs.append(job)
                            except Exception as e:
                                logger.debug(f"Failed to parse Web3 job: {e}")
                    else:
                        logger.warning(f"Web3 Career returned status {response.status}")
        
        except Exception as e:
            logger.error(f"Web3 Career search failed: {e}")
        
        logger.info(f"✅ Found {len(jobs)} Web3 Career jobs")
        return jobs
    
    def _parse_web3_job(self, row) -> Optional[JobPosting]:
        """Parse Web3 Career job row"""
        try:
            title_elem = row.find('h2', class_='fs-6')
            title = title_elem.text.strip() if title_elem else "AI Engineer"
            
            company_elem = row.find('h3', class_='fs-6')
            company = company_elem.text.strip() if company_elem else "Web3 Company"
            
            location = row.find('span', class_='location').text.strip() if row.find('span', 'location') else "Remote"
            
            url_elem = row.find('a')
            url = "https://web3.career" + url_elem['href'] if url_elem else ""
            
            return JobPosting(
                title=title,
                company=company,
                location=location,
                description=f"Web3 + AI role at {company}",
                source=JobSource.OTHER,
                url=url,
                posted_date=datetime.now(),
                remote_allowed=True,
                requirements=[],
                responsibilities=[]
            )
        except Exception as e:
            logger.debug(f"Failed to parse Web3 row: {e}")
        
        return None
    
    async def get_job_details(self, job_url: str) -> Dict[str, any]:
        """
        Fetch full job details from URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(job_url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract key details
                        return {
                            'full_description': soup.get_text(),
                            'requirements': self._extract_requirements(soup),
                            'responsibilities': self._extract_responsibilities(soup),
                        }
        except Exception as e:
            logger.error(f"Failed to get job details: {e}")
        
        return {}
    
    def _extract_requirements(self, soup) -> List[str]:
        """Extract requirements from job page"""
        requirements = []
        # Look for common patterns
        for keyword in ['requirements', 'qualifications', 'must have']:
            section = soup.find(text=lambda t: keyword in t.lower() if t else False)
            if section:
                parent = section.find_parent()
                if parent:
                    items = parent.find_all('li')
                    requirements.extend([item.text.strip() for item in items])
        return requirements[:10]
    
    def _extract_responsibilities(self, soup) -> List[str]:
        """Extract responsibilities from job page"""
        responsibilities = []
        for keyword in ['responsibilities', 'you will', 'role']:
            section = soup.find(text=lambda t: keyword in t.lower() if t else False)
            if section:
                parent = section.find_parent()
                if parent:
                    items = parent.find_all('li')
                    responsibilities.extend([item.text.strip() for item in items])
        return responsibilities[:10]
