"""
Base scraper class for job platforms
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import hashlib

from ..core.models import JobPosting, JobSource


class BaseScraper(ABC):
    """Base class for all job scrapers"""
    
    def __init__(self, source: JobSource):
        self.source = source
    
    @abstractmethod
    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 50
    ) -> List[JobPosting]:
        """Search for jobs matching criteria"""
        pass
    
    @abstractmethod
    async def get_job_details(self, job_url: str) -> Optional[JobPosting]:
        """Get detailed information about a specific job"""
        pass
    
    def generate_job_id(self, company: str, title: str, url: str) -> str:
        """Generate unique job ID"""
        unique_string = f"{company}_{title}_{url}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def extract_requirements(self, text: str) -> List[str]:
        """Extract requirements from job description"""
        requirements = []
        keywords = [
            "required", "requirements", "must have", "must-have",
            "qualifications", "you have", "you'll have"
        ]
        
        lines = text.lower().split('\n')
        in_requirements = False
        
        for line in lines:
            if any(kw in line for kw in keywords):
                in_requirements = True
                continue
            
            if in_requirements:
                if line.strip().startswith(('•', '-', '*', '·')) or line.strip()[0:2].isdigit():
                    req = line.strip().lstrip('•-*·0123456789. ')
                    if len(req) > 10:
                        requirements.append(req)
                elif not line.strip():
                    in_requirements = False
        
        return requirements[:10]  # Limit to 10 requirements
    
    def extract_responsibilities(self, text: str) -> List[str]:
        """Extract responsibilities from job description"""
        responsibilities = []
        keywords = [
            "responsibilities", "you will", "you'll", "your role",
            "what you'll do", "job duties"
        ]
        
        lines = text.lower().split('\n')
        in_responsibilities = False
        
        for line in lines:
            if any(kw in line for kw in keywords):
                in_responsibilities = True
                continue
            
            if in_responsibilities:
                if line.strip().startswith(('•', '-', '*', '·')) or line.strip()[0:2].isdigit():
                    resp = line.strip().lstrip('•-*·0123456789. ')
                    if len(resp) > 10:
                        responsibilities.append(resp)
                elif not line.strip():
                    in_responsibilities = False
        
        return responsibilities[:10]  # Limit to 10
    
    def is_remote_job(self, location: str, description: str) -> bool:
        """Check if job is remote"""
        location_lower = location.lower()
        description_lower = description.lower()
        
        remote_keywords = ["remote", "work from home", "wfh", "distributed"]
        return any(kw in location_lower or kw in description_lower for kw in remote_keywords)
    
    def extract_salary_range(self, text: str) -> Optional[str]:
        """Extract salary information from text"""
        import re
        
        # Look for salary patterns
        patterns = [
            r'\$[\d,]+k?\s*-\s*\$[\d,]+k?',
            r'[\d,]+k?\s*-\s*[\d,]+k?\s*(?:USD|EUR|per year)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
