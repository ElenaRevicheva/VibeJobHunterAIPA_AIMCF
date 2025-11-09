"""
Red flag detection for jobs
Warns about potentially problematic companies or roles
"""
from typing import List, Tuple

from ..core.models import JobPosting
from ..loaders import CandidateDataLoader


class RedFlagDetector:
    """Detect red flags in job postings"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        criteria = self.loader.get_target_criteria()
        self.company_flags = criteria.get('red_flags_to_avoid', {}).get('companies', [])
        self.role_flags = criteria.get('red_flags_to_avoid', {}).get('roles', [])
    
    def scan_job(self, job: JobPosting) -> Tuple[bool, List[str]]:
        """
        Scan job for red flags
        
        Args:
            job: Job posting to scan
            
        Returns:
            (has_red_flags, list_of_flags)
        """
        red_flags = []
        job_text = (job.title + " " + job.description).lower()
        
        # Check company red flags
        if not job.company or len(job.company) < 2:
            red_flags.append("🚩 No clear company name")
        
        if 'no clear product' in job_text or len(job.description) < 100:
            red_flags.append("🚩 Vague/unclear job description")
        
        # Check compensation red flags
        if job.salary_range:
            salary_lower = job.salary_range.lower()
            if any(word in salary_lower for word in ['unpaid', 'volunteer', 'equity only']):
                red_flags.append("🚩 No salary / equity only")
            if any(word in salary_lower for word in ['$40k', '$50k', '$60k']):
                red_flags.append("🚩 Below market compensation")
        
        # Check role red flags
        if 'junior' in job_text or 'entry level' in job_text:
            if 'senior' not in job.title.lower():
                red_flags.append("🚩 Below experience level")
        
        # Unrealistic requirements
        if '10+ years' in job_text and 'required' in job_text:
            red_flags.append("🚩 Unrealistic requirements (10+ years required)")
        
        if 'phd required' in job_text:
            red_flags.append("🚩 PhD required")
        
        # Culture red flags
        toxic_terms = ['rock star', 'ninja', 'guru', 'work hard play hard', 
                       'wear many hats', 'fast paced environment' ]
        toxic_found = [term for term in toxic_terms if term in job_text]
        if len(toxic_found) >= 3:
            red_flags.append(f"🚩 Potential culture issues (buzzwords: {', '.join(toxic_found[:2])})")
        
        # Location red flags
        if not job.remote_allowed:
            if 'relocation required' in job_text or 'on-site only' in job_text:
                red_flags.append("🚩 No remote, relocation required")
        
        # Maintenance-only roles
        if 'maintenance' in job_text and 'legacy' in job_text:
            if 'new features' not in job_text and 'build' not in job_text:
                red_flags.append("🚩 Maintenance-only role (no building)")
        
        return len(red_flags) > 0, red_flags
    
    def filter_safe_jobs(self, jobs: List[JobPosting]) -> List[JobPosting]:
        """
        Filter out jobs with red flags
        
        Args:
            jobs: List of jobs to filter
            
        Returns:
            Jobs without red flags
        """
        safe_jobs = []
        
        for job in jobs:
            has_flags, flags = self.scan_job(job)
            
            # Add flags to job for reference
            job.red_flags = flags if has_flags else []
            
            # Only keep jobs without red flags (or minor ones)
            if not has_flags or len(flags) <= 1:
                safe_jobs.append(job)
        
        return safe_jobs
    
    def get_flag_summary(self, job: JobPosting) -> str:
        """Get human-readable summary of red flags"""
        has_flags, flags = self.scan_job(job)
        
        if not has_flags:
            return "✅ No red flags detected"
        
        summary = f"⚠️ {len(flags)} red flag(s) detected:\n"
        for flag in flags:
            summary += f"  {flag}\n"
        
        return summary
