"""
Improved AI-powered content generation with caching, retry, and rate limiting
"""
from typing import Optional
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic
import asyncio

from ..core.models import Profile, JobPosting
from ..core.config import get_settings
from ..utils import retry_sync, ResponseCache, RateLimiter, get_logger, APICallTracker


class ContentGeneratorV2:
    """Enhanced content generator with reliability improvements"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai = Anthropic(api_key=self.settings.anthropic_api_key)
        self.logger = get_logger(__name__, self.settings.base_dir / "logs")
        
        # Output directories
        self.resumes_dir = self.settings.base_dir / "tailored_resumes"
        self.cover_letters_dir = self.settings.base_dir / "cover_letters"
        self.resumes_dir.mkdir(exist_ok=True)
        self.cover_letters_dir.mkdir(exist_ok=True)
        
        # Caching and rate limiting
        self.cache = ResponseCache(self.settings.base_dir / ".cache", ttl_hours=24)
        self.rate_limiter = RateLimiter(max_calls=50, period=60)  # 50 calls per minute
        self.tracker = APICallTracker()
    
    @retry_sync(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def tailor_resume(self, profile: Profile, job: JobPosting) -> str:
        """Generate tailored resume with caching and retry"""
        self.logger.info(f"Tailoring resume for {job.company} - {job.title}")
        
        prompt = self._build_resume_prompt(profile, job)
        
        # Check cache first
        cached = self.cache.get(prompt, "claude-3-5-sonnet-20241022")
        if cached:
            self.logger.info("Using cached resume")
            return cached
        
        # Rate limit
        self.rate_limiter.sync_acquire()
        
        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Track usage
            self.tracker.record_call(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
            
            tailored_resume = response.content[0].text
            
            # Cache response
            self.cache.set(prompt, "claude-3-5-sonnet-20241022", tailored_resume)
            
            # Save to file
            self._save_resume(tailored_resume, job)
            
            self.logger.info(f"Resume generated successfully ({len(tailored_resume)} chars)")
            return tailored_resume
        
        except Exception as e:
            self.logger.error(f"Error tailoring resume: {e}")
            raise
    
    @retry_sync(max_attempts=3, delay=2.0, exceptions=(Exception,))
    def generate_cover_letter(self, profile: Profile, job: JobPosting) -> str:
        """Generate cover letter with caching and retry"""
        self.logger.info(f"Generating cover letter for {job.company}")
        
        prompt = self._build_cover_letter_prompt(profile, job)
        
        # Check cache
        cached = self.cache.get(prompt, "claude-3-5-sonnet-20241022")
        if cached:
            self.logger.info("Using cached cover letter")
            return cached
        
        # Rate limit
        self.rate_limiter.sync_acquire()
        
        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Track usage
            self.tracker.record_call(
                response.usage.input_tokens,
                response.usage.output_tokens
            )
            
            cover_letter = response.content[0].text
            
            # Cache response
            self.cache.set(prompt, "claude-3-5-sonnet-20241022", cover_letter)
            
            # Save to file
            self._save_cover_letter(cover_letter, job)
            
            self.logger.info(f"Cover letter generated ({len(cover_letter)} chars)")
            return cover_letter
        
        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise
    
    def _build_resume_prompt(self, profile: Profile, job: JobPosting) -> str:
        """Build optimized resume generation prompt"""
        return f"""Create a tailored resume optimized for ATS and hiring managers.

CANDIDATE PROFILE:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone or "N/A"}
Location: {profile.location}
LinkedIn: {profile.linkedin_url or "N/A"}
GitHub: {profile.github_url or "N/A"}
Portfolio: {profile.portfolio_url or "N/A"}

Experience: {profile.experience_years} years
Skills: {', '.join(profile.skills)}
Languages: {', '.join(profile.languages)}

Key Achievements:
{chr(10).join([f"• {ach}" for ach in profile.key_achievements])}

Work History:
{self._format_work_history(profile.work_history)}

Education:
{self._format_education(profile.education)}

TARGET JOB:
Company: {job.company}
Title: {job.title}
Location: {job.location}

Key Requirements:
{chr(10).join([f"• {req}" for req in job.requirements[:10]])}

TASK:
Create a professional ATS-optimized resume in markdown format that:
1. Prioritizes achievements matching job requirements
2. Uses power verbs and quantifiable results
3. Includes relevant keywords naturally
4. Maintains complete honesty (no fabrication)
5. Emphasizes AI/ML expertise and 0-1 building capability
6. Format: Clean markdown suitable for PDF conversion

Focus on impact and results. Be concise yet compelling."""

    def _build_cover_letter_prompt(self, profile: Profile, job: JobPosting) -> str:
        """Build optimized cover letter generation prompt"""
        return f"""Write a compelling, authentic cover letter.

CANDIDATE: {profile.name}
Location: {profile.location}
Experience: {profile.experience_years} years
Languages: {', '.join(profile.languages)}

Top Achievements:
{chr(10).join([f"• {ach}" for ach in profile.key_achievements[:3]])}

Core Skills: {', '.join(profile.skills[:8])}

TARGET POSITION:
Company: {job.company}
Role: {job.title}
Location: {job.location}

Job Highlights:
{job.description[:600]}

Requirements:
{chr(10).join([f"• {req}" for req in job.requirements[:6]])}

GUIDELINES:
1. Opening: Strong hook showing genuine company knowledge
2. Body: 2-3 specific, relevant achievements with metrics
3. Fit: Why this role/company is perfect mutual match
4. Personality: Show passion for AI and building
5. Close: Clear call to action
6. Tone: Professional yet warm and human
7. Length: 300-400 words

Avoid clichés. Be specific. Show you researched the company."""

    def _save_resume(self, resume: str, job: JobPosting):
        """Save resume to file"""
        filename = f"{job.company}_{job.title}_{datetime.now().strftime('%Y%m%d')}.md"
        filename = filename.replace(" ", "_").replace("/", "-")[:100]  # Limit length
        filepath = self.resumes_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(resume)
    
    def _save_cover_letter(self, letter: str, job: JobPosting):
        """Save cover letter to file"""
        filename = f"{job.company}_{job.title}_{datetime.now().strftime('%Y%m%d')}_cover.txt"
        filename = filename.replace(" ", "_").replace("/", "-")[:100]
        filepath = self.cover_letters_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(letter)
    
    def _format_work_history(self, work_history: list) -> str:
        """Format work history concisely"""
        if not work_history:
            return "No work history provided"
        
        formatted = []
        for work in work_history[:5]:  # Limit to 5 most recent
            formatted.append(
                f"• {work.get('title', 'N/A')} at {work.get('company', 'N/A')} "
                f"({work.get('period', 'N/A')})\n  {work.get('description', '')[:200]}"
            )
        return "\n".join(formatted)
    
    def _format_education(self, education: list) -> str:
        """Format education concisely"""
        if not education:
            return "No education provided"
        
        formatted = []
        for edu in education[:3]:  # Limit to 3
            formatted.append(
                f"• {edu.get('degree', 'N/A')}, {edu.get('institution', 'N/A')} "
                f"({edu.get('year', 'N/A')})"
            )
        return "\n".join(formatted)
    
    def get_usage_stats(self) -> dict:
        """Get API usage statistics"""
        stats = self.tracker.get_stats()
        self.logger.info(f"API Usage - Calls: {stats['total_calls']}, "
                        f"Cost: ${stats['estimated_cost_usd']:.4f}")
        return stats
