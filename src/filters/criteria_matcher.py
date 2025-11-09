"""
Smart job matching using target criteria
Filters jobs based on Elena's preferences and requirements
"""
from typing import List, Tuple
import re

from ..core.models import JobPosting
from ..loaders import CandidateDataLoader


class CriteriaMatcher:
    """Match jobs against target criteria"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        self.criteria = self.loader.get_target_criteria()
    
    def evaluate_job(self, job: JobPosting) -> Tuple[bool, int, List[str]]:
        """
        Evaluate if job matches target criteria
        
        Args:
            job: Job posting to evaluate
            
        Returns:
            (should_apply, score, reasons)
        """
        score = 0
        reasons = []
        red_flags = []
        
        # Check target roles (critical)
        role_match = self._check_role_match(job)
        if role_match:
            score += 30
            reasons.append(f"✅ Role match: {role_match}")
        else:
            reasons.append("⚠️ Role doesn't match target roles")
        
        # Check company stage
        stage_match = self._check_company_stage(job)
        if stage_match:
            score += 15
            reasons.append(f"✅ Company stage: {stage_match}")
        
        # Check compensation (if available)
        comp_match = self._check_compensation(job)
        if comp_match:
            score += 20
            reasons.append(f"✅ Compensation: {comp_match}")
        
        # Check location/remote
        location_match = self._check_location(job)
        if location_match:
            score += 15
            reasons.append(f"✅ Location: {location_match}")
        else:
            score -= 20
            reasons.append("⚠️ Location not ideal")
        
        # Check for ideal characteristics
        ideal_score, ideal_reasons = self._check_ideal_characteristics(job)
        score += ideal_score
        reasons.extend(ideal_reasons)
        
        # Decide if should apply
        should_apply = score >= 50 and len(red_flags) == 0
        
        return should_apply, score, reasons
    
    def _check_role_match(self, job: JobPosting) -> str:
        """Check if role matches target roles"""
        target_roles = self.criteria.get('target_roles', [])
        job_title_lower = job.title.lower()
        
        for role in target_roles:
            role_lower = role.lower()
            # Exact match or contains key words
            if role_lower in job_title_lower or any(word in job_title_lower for word in role_lower.split()):
                return role
        
        return ""
    
    def _check_company_stage(self, job: JobPosting) -> str:
        """Check if company stage matches"""
        target_stages = self.criteria.get('target_companies', {}).get('stage', [])
        job_desc_lower = job.description.lower()
        
        for stage in target_stages:
            if stage.lower() in job_desc_lower:
                return stage
        
        # If no stage mentioned, give benefit of doubt
        return "Unknown (OK)"
    
    def _check_compensation(self, job: JobPosting) -> str:
        """Check if compensation matches"""
        if not job.salary_range:
            return "Not specified (OK)"
        
        target = self.criteria.get('target_compensation', {})
        target_range = target.get('base_salary_range', '$100K-180K')
        
        # Extract numbers from salary range
        salary_lower = job.salary_range.lower()
        
        # Check if below minimum
        if any(word in salary_lower for word in ['$50k', '$60k', '$70k', '$80k']):
            return ""  # Below range
        
        # If mentions 100K+ or similar, it's good
        if any(word in salary_lower for word in ['$100k', '$120k', '$150k', '$180k', '100k+']):
            return "In target range"
        
        return "Not specified (OK)"
    
    def _check_location(self, job: JobPosting) -> str:
        """Check if location matches"""
        target_locations = self.criteria.get('target_companies', {}).get('locations', [])
        
        # Remote is always good
        if job.remote_allowed or 'remote' in job.location.lower():
            return "Remote ✨"
        
        # Check other target locations
        job_location_lower = job.location.lower()
        for loc in target_locations:
            if loc.lower() in job_location_lower:
                return loc
        
        return ""
    
    def _check_ideal_characteristics(self, job: JobPosting) -> Tuple[int, List[str]]:
        """Check for ideal role characteristics"""
        score = 0
        reasons = []
        
        ideal = self.criteria.get('ideal_role_characteristics', {})
        job_text = (job.title + " " + job.description).lower()
        
        # Technical characteristics
        technical_terms = ['ai', 'ml', 'machine learning', 'llm', 'gpt', 'claude']
        if any(term in job_text for term in technical_terms):
            score += 10
            reasons.append("✅ AI/ML focus")
        
        # Ownership keywords
        ownership_terms = ['ownership', 'lead', 'architect', 'build from scratch', '0-1']
        if any(term in job_text for term in ownership_terms):
            score += 10
            reasons.append("✅ High ownership")
        
        # Startup keywords
        startup_terms = ['startup', 'fast-paced', 'move fast', 'ship quickly', 'iterate']
        if any(term in job_text for term in startup_terms):
            score += 10
            reasons.append("✅ Startup culture")
        
        # Equity mentions
        if 'equity' in job_text or 'stock' in job_text:
            score += 10
            reasons.append("✅ Equity offered")
        
        return score, reasons
    
    def filter_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """
        Filter jobs by criteria, return only good matches
        
        Args:
            jobs: List of jobs to filter
            
        Returns:
            Filtered list of jobs worth applying to
        """
        filtered = []
        
        for job in jobs:
            should_apply, score, reasons = self.evaluate_job(job)
            
            # Add score and reasons to job
            job.match_score = score
            job.match_reasons = reasons
            
            if should_apply:
                filtered.append(job)
        
        # Sort by score
        filtered.sort(key=lambda j: j.match_score, reverse=True)
        
        return filtered
