"""
LinkedIn job scraper
"""
import asyncio
import aiohttp
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from ..core.models import JobPosting, JobSource
from ..core.config import get_settings


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn jobs"""
    
    def __init__(self):
        super().__init__(JobSource.LINKEDIN)
        self.settings = get_settings()
        self.base_url = "https://www.linkedin.com/jobs/search"
    
    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 50
    ) -> List[JobPosting]:
        """Search LinkedIn for jobs"""
        jobs = []
        
        # Build search query
        keyword_query = " ".join(keywords)
        
        params = {
            "keywords": keyword_query,
            "location": location or "Remote",
            "f_WT": "2" if remote_only else "",  # Remote filter
            "sortBy": "DD",  # Sort by date
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # LinkedIn requires proper headers to avoid blocking
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        print(f"LinkedIn returned status {response.status}")
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Parse job cards
                    job_cards = soup.find_all('div', class_='base-card')
                    
                    for card in job_cards[:limit]:
                        try:
                            job = self._parse_job_card(card)
                            if job:
                                jobs.append(job)
                        except Exception as e:
                            print(f"Error parsing job card: {e}")
                            continue
        
        except Exception as e:
            print(f"Error scraping LinkedIn: {e}")
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[JobPosting]:
        """Parse a LinkedIn job card"""
        try:
            # Extract basic info
            title_elem = card.find('h3', class_='base-search-card__title')
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            location_elem = card.find('span', class_='job-search-card__location')
            link_elem = card.find('a', class_='base-card__full-link')
            
            if not all([title_elem, company_elem, link_elem]):
                return None
            
            title = title_elem.text.strip()
            company = company_elem.text.strip()
            location = location_elem.text.strip() if location_elem else "Not specified"
            url = link_elem.get('href', '')
            
            # Generate job ID
            job_id = self.generate_job_id(company, title, url)
            
            # Create job posting
            job = JobPosting(
                id=job_id,
                title=title,
                company=company,
                location=location,
                description="",  # Will be fetched separately if needed
                source=self.source,
                url=url,
                remote_allowed=self.is_remote_job(location, ""),
                posted_date=datetime.now(),
            )
            
            return job
        
        except Exception as e:
            print(f"Error parsing job card: {e}")
            return None
    
    async def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed job information from LinkedIn"""
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
                    
                    # Extract job details
                    title_elem = soup.find('h1', class_='topcard__title')
                    company_elem = soup.find('a', class_='topcard__org-name-link')
                    location_elem = soup.find('span', class_='topcard__flavor--bullet')
                    desc_elem = soup.find('div', class_='description__text')
                    
                    if not all([title_elem, company_elem, desc_elem]):
                        return None
                    
                    title = title_elem.text.strip()
                    company = company_elem.text.strip()
                    location = location_elem.text.strip() if location_elem else "Not specified"
                    description = desc_elem.text.strip()
                    
                    job_id = self.generate_job_id(company, title, job_url)
                    
                    # Extract structured information
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
            print(f"Error getting job details: {e}")
            return None
