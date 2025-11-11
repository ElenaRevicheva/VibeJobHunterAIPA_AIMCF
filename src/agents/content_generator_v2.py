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
        
        # Get role-specific talking points if available
        talking_points_section = ""
        if hasattr(job, 'talking_points') and job.talking_points:
            talking_points_section = f"""

ROLE-SPECIFIC TALKING POINTS (USE THESE!):
{chr(10).join(job.talking_points)}
"""
        
        return f"""Write a compelling, authentic cover letter for this SPECIFIC role type.

CANDIDATE: {profile.name}
Location: {profile.location}
Experience: 7 years exec + 8 months hands-on AI engineering
Languages: {', '.join(profile.languages)}

🔥 UNIQUE VALUE PROPOSITIONS (MUST EMPHASIZE):
• 2 LIVE AI agents with PAYING USERS in 19 countries
• PayPal Subscriptions ACTIVE (revenue-generating, not just demo!)
• Speed: 6 production apps in 7 months (10x faster than teams)
• Cost: 98% reduction ($15K vs $900K traditional estimate)
• Live Demo: wa.me/50766623757 (instant credibility!)
• Bilingual: EN/ES dual-sided market expertise
• Executive: Ex-CEO & CLO (strategic thinking + execution)
• Unique: Web3 + AI combo (DAO design + LLM engineering)

Top Achievements:
{chr(10).join([f"• {ach}" for ach in profile.key_achievements[:3]])}

Core Skills: {', '.join(profile.skills[:8])}
{talking_points_section}
TARGET POSITION:
Company: {job.company}
Role: {job.title}
Location: {job.location}

Job Highlights:
{job.description[:600]}

Requirements:
{chr(10).join([f"• {req}" for req in job.requirements[:6]])}

CRITICAL GUIDELINES FOR THIS COVER LETTER:

1. OPENING (MUST use one of these hooks):
   - "I built something similar to what you're doing - try it: wa.me/50766623757"
   - "I saw {job.company} recently [specific news/launch] - congrats! Here's how I can help..."
   - "Most candidates will show you their resume. I'll show you my live product: wa.me/50766623757"
   
2. BODY (Emphasize based on role):
   - For Founding Engineer: "I've been a founding engineer on my own products - 2 live AI agents with paying users in 19 countries"
   - For AI Product Manager: "As a solo founder, I handle product strategy AND engineering. 0→1 builder."
   - For LLM Engineer: "EspaLuz uses Claude for emotional intelligence, GPT for structured tasks, with bilingual EN/ES support"
   - For AI Solutions Architect: "Built complete AI architecture: voice (Whisper), text (Claude/GPT), memory (PostgreSQL), monetization (PayPal)"
   - For AI Growth Engineer: "Organic reach to 19 countries through bilingual product + community. PayPal subs from zero to live in 7 months"

3. TRACTION (Always include):
   - 19 countries reach (proves PMF)
   - PayPal subscriptions active (proves monetization)
   - 98% cost reduction (proves efficiency)
   - Live demo link (proves it's real)

4. DIFFERENTIATION:
   "Most candidates talk about what they'll build. I show what I've already built and monetized. 
    You can try my AI assistant right now: wa.me/50766623757"

5. CLOSE:
   - Specific to company/role
   - Clear CTA
   - Mention demo link again
   - "Available for a call this week"

6. TONE: Confident builder, not desperate job seeker. You're evaluating mutual fit.

7. LENGTH: 300-400 words MAX

AVOID:
- "I am writing to express my interest..." (instant rejection)
- Generic praise without specifics
- Apologizing for "non-traditional background" (it's a strength!)
- Over-explaining the 7yr exec vs 8mo coding (focus on results)

FORMAT:
Hi [Name / Team],

[Hook with demo link or specific company research]

[2-3 paragraphs with metrics and specific achievements]

[Why this specific role/company is perfect fit]

[Close with CTA]

Best regards,
Elena Revicheva
💬 Try my AI: wa.me/50766623757
📧 aipa@aideazz.xyz
🌐 aideazz.xyz"""

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
