"""
AI-powered job matching and scoring
"""
from typing import List, Tuple
from anthropic import Anthropic

from ..core.models import Profile, JobPosting
from ..core.config import get_settings


class JobMatcher:
    """Match jobs to profile and score relevance"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai = Anthropic(api_key=self.settings.anthropic_api_key)
    
    def calculate_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Calculate match score between profile and job
        Returns: (score, reasons)
        """
        prompt = f"""Analyze this job posting against the candidate's profile and provide:
1. A match score from 0-100 (higher is better)
2. 3-5 specific reasons why this is a good/bad match
3. Key skills/experience that align with the job

Candidate Profile:
- Name: {profile.name}
- Location: {profile.location}
- Experience: {profile.experience_years} years
- Skills: {', '.join(profile.skills[:15])}
- Key Achievements:
{chr(10).join([f"  • {ach}" for ach in profile.key_achievements[:5]])}
- Target Roles: {', '.join(profile.target_roles)}
- Languages: {', '.join(profile.languages)}

Job Posting:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location}
- Remote: {job.remote_allowed}
- Description: {job.description[:1000]}
- Requirements: {chr(10).join([f"  • {req}" for req in job.requirements[:8]])}

Return JSON format:
{{
  "score": <0-100>,
  "reasons": ["reason1", "reason2", ...],
  "aligned_skills": ["skill1", "skill2", ...],
  "missing_skills": ["skill1", "skill2", ...],
  "recommendation": "apply|maybe|skip"
}}

Consider:
- Skill match (technical and soft skills)
- Experience level fit
- Location/remote compatibility
- Company culture fit based on achievements
- Growth potential
- Role alignment with target roles
"""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result_text = response.content[0].text
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            score = float(result.get("score", 0))
            reasons = result.get("reasons", [])
            
            # Add aligned skills to reasons
            aligned = result.get("aligned_skills", [])
            if aligned:
                reasons.append(f"Aligned skills: {', '.join(aligned[:3])}")
            
            return score, reasons
        
        except Exception as e:
            print(f"Error calculating match score: {e}")
            # Fallback to basic scoring
            return self._basic_match_score(profile, job)
    
    def _basic_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """Simple keyword-based matching as fallback"""
        score = 0.0
        reasons = []
        
        # Check title match
        job_title_lower = job.title.lower()
        for target_role in profile.target_roles:
            if target_role.lower() in job_title_lower:
                score += 30
                reasons.append(f"Title matches target role: {target_role}")
                break
        
        # Check skills match
        profile_skills_lower = [s.lower() for s in profile.skills]
        job_text_lower = (job.title + " " + job.description).lower()
        
        matched_skills = []
        for skill in profile_skills_lower:
            if skill in job_text_lower:
                matched_skills.append(skill)
        
        if matched_skills:
            skill_score = min(40, len(matched_skills) * 5)
            score += skill_score
            reasons.append(f"Matched skills: {', '.join(matched_skills[:5])}")
        
        # Check location
        if profile.remote_only and job.remote_allowed:
            score += 15
            reasons.append("Remote position available")
        elif profile.location.lower() in job.location.lower():
            score += 15
            reasons.append(f"Location match: {profile.location}")
        
        # Check keywords
        matched_keywords = []
        for keyword in self.settings.target_keywords:
            if keyword.lower() in job_text_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            keyword_score = min(15, len(matched_keywords) * 2)
            score += keyword_score
            reasons.append(f"Key technologies: {', '.join(matched_keywords[:3])}")
        
        return min(score, 100), reasons
    
    async def score_jobs(self, profile: Profile, jobs: List[JobPosting]) -> List[JobPosting]:
        """Score and sort jobs by relevance"""
        for job in jobs:
            score, reasons = self.calculate_match_score(profile, job)
            job.match_score = score
            job.match_reasons = reasons
        
        # Sort by score
        jobs.sort(key=lambda j: j.match_score, reverse=True)
        return jobs
    
    def filter_jobs(
        self,
        jobs: List[JobPosting],
        min_score: float = 50.0,
        exclude_keywords: List[str] = None
    ) -> List[JobPosting]:
        """Filter jobs by criteria"""
        filtered = []
        
        exclude_keywords = exclude_keywords or self.settings.excluded_keywords
        exclude_lower = [k.lower() for k in exclude_keywords]
        
        for job in jobs:
            # Check minimum score
            if job.match_score < min_score:
                continue
            
            # Check excluded keywords
            job_text_lower = (job.title + " " + job.description).lower()
            if any(kw in job_text_lower for kw in exclude_lower):
                continue
            
            filtered.append(job)
        
        return filtered
