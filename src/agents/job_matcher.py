"""
AI-powered job matching and scoring
"""
from typing import List, Tuple
from anthropic import Anthropic

from ..core.models import Profile, JobPosting
from ..core.config import get_settings
from .founding_engineer_scorer import FoundingEngineerScorer


class JobMatcher:
    """Match jobs to profile and score relevance"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai = Anthropic(api_key=self.settings.anthropic_api_key)
        self.founding_scorer = FoundingEngineerScorer()
    
    def calculate_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Calculate match score between profile and job
        Returns: (score, reasons)
        
        Uses keyword matching as primary method (fast & reliable!)
        Falls back to AI only if keyword score is borderline
        """
        
        # FIRST: Check if this is a high-priority founding engineer role
        founding_score, strengths, talking_points = self.founding_scorer.calculate_founding_fit_score(job, profile)
        
        # Add talking points to job metadata for later use
        job.talking_points = talking_points
        
        # Use keyword matching as PRIMARY method (more reliable!)
        keyword_score, keyword_reasons = self._basic_match_score(profile, job)
        
        # Combine keyword score with founding score
        combined_score = (keyword_score * 0.7) + (founding_score * 0.3)
        
        # Combine reasons
        all_reasons = keyword_reasons + strengths[:3]
        
        # Flag high-priority jobs
        if self.founding_scorer.should_apply_immediately(job, combined_score):
            all_reasons.insert(0, "🚨 HIGH PRIORITY - APPLY IMMEDIATELY!")
        
        return combined_score, all_reasons
        
        prompt = f"""Analyze this job posting against the candidate's profile and provide:
1. A match score from 0-100 (higher is better)
2. 3-5 specific reasons why this is a good/bad match
3. Key skills/experience that align with the job

Candidate Profile:
- Name: {profile.name}
- Location: {profile.location}
- Experience: {profile.experience_years} years TOTAL (7 years exec + 8 months hands-on AI/ML engineering)

UNIQUE DIFFERENTIATORS (emphasize these!):
- 🔥 2 LIVE AI agents with PAYING USERS in 19 countries
- 💰 Revenue: PayPal Subscriptions ACTIVE (not just demo!)
- ⚡ Speed: 6 production apps in 7 months (solo-built)
- 💎 Cost: 98% reduction ($15K vs $900K traditional estimate)
- 🤖 Tech: Claude, GPT, Whisper, TTS, OCR, ElizaOS, HeyGen
- 🌎 Bilingual: EN/ES dual-sided market
- 👔 Executive: Ex-CEO & CLO at E-Government (strategic thinking)
- 🦄 Unique: Web3 + AI combination (DAO, tokenomics + LLM)
- 💬 Live Demo: wa.me/50766623757 (instant credibility!)

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

SCORING PRIORITY FOR ELENA:
+30 points: Founding Engineer / AI Product Manager / LLM Engineer roles
+25 points: YC companies or Seed/Series A startups
+20 points: Mentions equity (0.5-3%)
+15 points: Values traction/PMF (she has 19 countries proof!)
+15 points: Fast-paced/builder culture (she ships 10x faster)
+10 points: Web3 + AI combination
-20 points: Big corp (Google, Meta, etc.) - not her fit
-15 points: Pure maintenance role - she's a 0→1 builder
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
            
            # BOOST score with founding engineer bonus
            combined_score = (score * 0.7) + (founding_score * 0.3)  # 70% AI, 30% founding fit
            
            # Add founding engineer strengths to reasons
            if strengths:
                reasons.extend(strengths[:3])  # Top 3 strengths
            
            # Flag high-priority jobs
            if self.founding_scorer.should_apply_immediately(job, combined_score):
                reasons.insert(0, "🚨 HIGH PRIORITY - APPLY IMMEDIATELY!")
            
            return combined_score, reasons
        
        except Exception as e:
            print(f"Error calculating match score: {e}")
            # Fallback to basic scoring
            return self._basic_match_score(profile, job)
    
    def _basic_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Keyword-based matching (GENEROUS scoring for AI/Founding roles!)
        Designed to score most relevant jobs 65-95 points
        """
        score = 0.0
        reasons = []
        
        job_text = (job.title + " " + job.description).lower()
        
        # TARGET ROLES (50 points max)
        role_matches = {
            'founding engineer': 50, 'founding': 48,
            'ai engineer': 45, 'ai product manager': 45, 'llm engineer': 45,
            'full-stack ai': 45, 'machine learning engineer': 43, 'ml engineer': 43,
            'ai solutions': 40, 'ai growth': 40,
            'software engineer': 35, 'engineer': 28
        }
        
        for keyword, points in role_matches.items():
            if keyword in job_text:
                score += points
                reasons.append(f"✅ {keyword.title()}")
                break
        
        # AI/ML TECH (35 points max)
        tech_keywords = ['ai', 'llm', 'gpt', 'claude', 'ml', 'machine learning', 'python',
                        'react', 'typescript', 'pytorch', 'nlp']
        tech_found = [kw for kw in tech_keywords if kw in job_text]
        if tech_found:
            score += min(len(tech_found) * 3, 35)
            reasons.append(f"✅ Tech: {', '.join(tech_found[:4])}")
        
        # STARTUP SIGNALS (25 points max)  
        startup_kw = ['startup', 'seed', 'equity', 'yc', '0-1', 'founding', 'early stage']
        startup_found = [kw for kw in startup_kw if kw in job_text]
        if startup_found:
            score += min(len(startup_found) * 5, 25)
            reasons.append(f"✅ Stage: {', '.join(startup_found[:2])}")
        
        # REMOTE (15 points)
        if job.remote_allowed or 'remote' in job_text:
            score += 15
            reasons.append("✅ Remote")
        
        # SKILLS (20 points max)
        skills_found = [s for s in profile.skills[:15] if s.lower() in job_text]
        if skills_found:
            score += min(len(skills_found) * 2, 20)
            reasons.append(f"✅ Skills: {', '.join(skills_found[:3])}")
        
        # Minimum score
        if not reasons:
            score = 50
            reasons.append("Basic match")
        
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
