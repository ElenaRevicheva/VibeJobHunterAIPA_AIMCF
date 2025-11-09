"""
Cover letter formatter using proven templates
Generates personalized cover letters with Elena's voice
"""
from ..core.models import Profile, JobPosting
from ..loaders import CandidateDataLoader


class CoverLetterFormatter:
    """Format cover letters using proven template"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        self.template = self.loader.get_cover_letter_template()
    
    def format_cover_letter(self, profile: Profile, job: JobPosting, company_research: str = "") -> str:
        """
        Generate cover letter using proven template
        
        Args:
            profile: Candidate profile
            job: Target job posting
            company_research: Optional company-specific research
            
        Returns:
            Formatted cover letter
        """
        # Use template structure
        opening = self.template.get('opening', self._default_opening())
        
        # Company research (AI will fill this)
        if not company_research:
            company_research = f"I've been following {job.company}'s work and am particularly impressed by your focus on {self._extract_focus(job)}."
        
        # Pick relevant achievements based on job
        relevant_exp = self._select_relevant_experience(profile, job)
        
        # Differentiation
        differentiation = self.template.get('differentiation', self._default_differentiation())
        
        # Call to action
        cta = self.template.get('call_to_action', '').replace('[Company]', job.company).replace('[their specific goal]', self._extract_goal(job))
        
        # Closing
        closing = self.template.get('closing', self._default_closing(profile))
        
        # Assemble cover letter
        cover_letter = f"""Dear Hiring Manager,

{opening}

{company_research}

**Most relevant to this role:**
{relevant_exp}

{differentiation}

{cta}

{closing}
"""
        
        return cover_letter
    
    def _default_opening(self) -> str:
        """Default opening paragraph"""
        return """I solo-built 6 production AI applications in 7 months, demonstrating both technical depth and execution speed. With 7 years of C-suite experience and 50K+ lines of code, I combine strategic thinking with hands-on engineering."""
    
    def _default_differentiation(self) -> str:
        """Default differentiation paragraph"""
        return """**What makes me different:** I can demonstrate a working product immediately (try: wa.me/50766623757). Most candidates talk about what they can build - I show what I've already built."""
    
    def _default_closing(self, profile: Profile) -> str:
        """Default closing"""
        return f"""Best regards,
{profile.name}
wa.me/50766623757 | {profile.email} | {profile.website_url}"""
    
    def _extract_focus(self, job: JobPosting) -> str:
        """Extract company focus from job description"""
        desc_lower = job.description.lower()
        
        if 'ai' in desc_lower or 'machine learning' in desc_lower:
            return "AI innovation"
        elif 'startup' in desc_lower or 'fast-paced' in desc_lower:
            return "fast-paced execution"
        elif 'mission' in desc_lower:
            return "mission-driven approach"
        else:
            return "innovative technology"
    
    def _extract_goal(self, job: JobPosting) -> str:
        """Extract company goal from job description"""
        desc_lower = job.description.lower()
        
        if 'scale' in desc_lower:
            return "scale your platform"
        elif 'build' in desc_lower or 'grow' in desc_lower:
            return "build and grow your product"
        elif 'transform' in desc_lower:
            return "drive transformation"
        else:
            return "achieve your goals"
    
    def _select_relevant_experience(self, profile: Profile, job: JobPosting) -> str:
        """Select 2-3 achievements relevant to job"""
        job_text = (job.title + " " + job.description).lower()
        
        # Default achievements
        achievements = [
            "Built 6 production AI applications in 7 months with 8+ AI model integrations",
            "Achieved 98% cost reduction ($15K vs $950K traditional development)",
            "7 years of C-suite strategic experience in digital transformation"
        ]
        
        # Add specific ones based on job requirements
        if 'typescript' in job_text or 'react' in job_text:
            achievements.insert(1, "50,000+ lines of production TypeScript/React code")
        
        if 'startup' in job_text or 'founding' in job_text:
            achievements.insert(0, "Solo-founder execution: built products from zero to production")
        
        # Format as list
        formatted = ""
        for i, ach in enumerate(achievements[:3], 1):
            formatted += f"- {ach}\n"
        
        return formatted.strip()
