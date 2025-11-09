"""
Indeed job scraper
"""
import asyncio
import aiohttp
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..core.models import JobPosting, JobSource
from ..core.config import get_settings


class IndeedScraper(BaseScraper):
    """Scraper for Indeed jobs"""
    
    def __init__(self):
        super().__init__(JobSource.INDEED)
        self.settings = get_settings()
        self.base_url = "https://www.indeed.com/jobs"
    
    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 50
    ) -> List[JobPosting]:
        """Search Indeed for jobs"""
        jobs = []
        
        keyword_query = " ".join(keywords)
        
        params = {
            "q": keyword_query,
            "l": location or "Remote",
            "sort": "date",
        }
        
        if remote_only:
            params["sc"] = "0kf:attr(DSQF7);"  # Remote filter
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        print(f"Indeed returned status {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse job cards
                    job_cards = soup.find_all('div', class_='job_seen_beacon')
                    
                    for card in job_cards[:limit]:
                        try:
                            job = self._parse_job_card(card)
                            if job:
                                jobs.append(job)
                        except Exception as e:
                            print(f"Error parsing job card: {e}")
                            continue
        
        except Exception as e:
            print(f"Error scraping Indeed: {e}")
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[JobPosting]:
        """Parse an Indeed job card"""
        try:
            title_elem = card.find('h2', class_='jobTitle')
            company_elem = card.find('span', class_='companyName')
            location_elem = card.find('div', class_='companyLocation')
            link_elem = card.find('a', href=True)
            
            if not all([title_elem, company_elem, link_elem]):
                return None
            
            title = title_elem.text.strip()
            company = company_elem.text.strip()
            location = location_elem.text.strip() if location_elem else "Not specified"
            
            # Build full URL
            job_key = link_elem['href']
            if not job_key.startswith('http'):
                url = f"https://www.indeed.com{job_key}"
            else:
                url = job_key
            
            job_id = self.generate_job_id(company, title, url)
            
            job = JobPosting(
                id=job_id,
                title=title,
                company=company,
                location=location,
                description="",
                source=self.source,
                url=url,
                remote_allowed=self.is_remote_job(location, ""),
                posted_date=datetime.now(),
            )
            
            return job
        
        except Exception as e:
            print(f"Error parsing Indeed job card: {e}")
            return None
    
    async def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed job information from Indeed"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                }
                
                async with session.get(job_url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    title_elem = soup.find('h1', class_='jobsearch-JobInfoHeader-title')
                    company_elem = soup.find('div', class_='icl-u-lg-mr--sm')
                    location_elem = soup.find('div', class_='jobsearch-JobInfoHeader-subtitle')
                    desc_elem = soup.find('div', id='jobDescriptionText')
                    
                    if not all([title_elem, desc_elem]):
                        return None
                    
                    title = title_elem.text.strip()
                    company = company_elem.text.strip() if company_elem else "Unknown"
                    location = location_elem.text.strip() if location_elem else "Not specified"
                    description = desc_elem.text.strip()
                    
                    job_id = self.generate_job_id(company, title, job_url)
                    
                    requirements = self.extract_requirements(description)
                    responsibilities = self.extract_responsibilities(description)
                    salary_range = self.extract_salary_range(description)
                    
                    job = JobPosting(
                        id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        description=description,
                        requirements=requirements,
                        responsibilities=responsibilities,
                        source=self.source,
                        url=job_url,
                        salary_range=salary_range,
                        remote_allowed=self.is_remote_job(location, description),
                        posted_date=datetime.now(),
                    )
                    
                    return job
        
        except Exception as e:
            print(f"Error getting Indeed job details: {e}")
            return None
