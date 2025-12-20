"""
📄 RESUME SELECTOR - Golden Roadmap v2 Aligned

Selects the optimal resume variant based on:
- Role title keywords
- Company stage
- Job description emphasis

Resume Variants:
1. Founding Engineer - For founding/early roles with equity
2. Senior AI Engineer - For AI/ML technical depth roles
3. AI Solutions Architect - For architecture/enterprise roles
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ResumeSelector:
    """
    Intelligent resume selection based on job characteristics
    """
    
    # Resume paths - PDFs for ATS submission
    RESUME_PDFS = {
        "founding": "autonomous_data/resumes/founding_engineer.pdf",
        "senior_ai": "autonomous_data/resumes/senior_ai_engineer.pdf",
        "architect": "autonomous_data/resumes/ai_solutions_architect.pdf",
        "default": "autonomous_data/resumes/elena_resume.pdf",
    }
    
    # Markdown versions for content display (backwards compatibility)
    RESUMES = {
        "founding": "src/templates/resume_founding_engineer.md",
        "senior_ai": "src/templates/resume_senior_ai_engineer.md",
        "architect": "src/templates/resume_ai_solutions_architect.md",
        "default": "src/templates/resume_final_elena.md",
    }
    
    # Keyword mappings for each resume type
    FOUNDING_KEYWORDS = [
        "founding", "founder", "first engineer", "0-1", "zero to one",
        "greenfield", "build from scratch", "early stage", "seed",
        "series a", "equity", "technical co-founder", "startup",
        "principal", "staff"
    ]
    
    SENIOR_AI_KEYWORDS = [
        "ai engineer", "ml engineer", "machine learning", "llm",
        "nlp", "deep learning", "neural", "transformer", "gpt",
        "claude", "openai", "anthropic", "ai product", "llm engineer",
        "data scientist", "ai researcher"
    ]
    
    ARCHITECT_KEYWORDS = [
        "architect", "solutions architect", "platform", "infrastructure",
        "enterprise", "scale", "system design", "technical lead",
        "principal engineer", "staff engineer", "cloud", "devops"
    ]
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        logger.info("📄 Resume Selector initialized with 3 variants")
    
    def select_resume(self, job: Dict[str, Any]) -> Tuple[str, str]:
        """
        Select the best resume variant for a job
        
        Args:
            job: Job dict with title, description, company, etc.
            
        Returns:
            Tuple of (resume_path, resume_type)
        """
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        company = job.get('company', '').lower()
        
        job_text = f"{title} {description} {company}"
        
        # Score each resume type
        scores = {
            "founding": self._score_keywords(job_text, self.FOUNDING_KEYWORDS),
            "senior_ai": self._score_keywords(job_text, self.SENIOR_AI_KEYWORDS),
            "architect": self._score_keywords(job_text, self.ARCHITECT_KEYWORDS),
        }
        
        # Find best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # If no strong match, use default
        if best_score < 2:
            best_type = "default"
            logger.debug(f"📄 No strong match, using default resume")
        else:
            logger.info(f"📄 Selected '{best_type}' resume (score: {best_score}) for {job.get('company')}")
        
        return self.RESUMES[best_type], best_type
    
    def _score_keywords(self, text: str, keywords: list) -> int:
        """Count keyword matches in text"""
        score = 0
        for kw in keywords:
            if kw in text:
                # Higher weight for title matches
                score += 2 if kw in text[:100] else 1
        return score
    
    def get_resume_content(self, resume_type: str) -> Optional[str]:
        """
        Load resume content from file
        
        Args:
            resume_type: One of 'founding', 'senior_ai', 'architect', 'default'
            
        Returns:
            Resume markdown content
        """
        # Check cache
        if resume_type in self._cache:
            return self._cache[resume_type]
        
        resume_path = self.RESUMES.get(resume_type, self.RESUMES["default"])
        
        try:
            path = Path(resume_path)
            if not path.exists():
                # Try relative to workspace root
                path = Path("/workspace") / resume_path
            
            if path.exists():
                content = path.read_text()
                self._cache[resume_type] = content
                return content
            else:
                logger.warning(f"Resume not found: {resume_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load resume: {e}")
            return None
    
    def get_resume_for_job(self, job: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        Get the best resume content for a job
        
        Returns:
            Tuple of (resume_content, resume_type)
        """
        resume_path, resume_type = self.select_resume(job)
        content = self.get_resume_content(resume_type)
        return content, resume_type
    
    def get_pdf_path_for_job(self, job: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        Get the PDF resume path for ATS submission
        
        Returns:
            Tuple of (pdf_path, resume_type)
        """
        _, resume_type = self.select_resume(job)
        pdf_rel_path = self.RESUME_PDFS.get(resume_type, self.RESUME_PDFS["default"])
        
        # Check multiple locations for Docker/local compatibility
        for base in ["/app", "/workspace", "."]:
            pdf_path = Path(base) / pdf_rel_path
            if pdf_path.exists():
                logger.info(f"📄 PDF resume found: {pdf_path}")
                return str(pdf_path), resume_type
        
        # Fallback to relative path (let caller handle)
        return pdf_rel_path, resume_type
    
    def explain_selection(self, job: Dict[str, Any]) -> str:
        """
        Explain why a particular resume was selected
        
        Returns:
            Explanation string
        """
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        job_text = f"{title} {description}"
        
        matches = {
            "founding": [kw for kw in self.FOUNDING_KEYWORDS if kw in job_text],
            "senior_ai": [kw for kw in self.SENIOR_AI_KEYWORDS if kw in job_text],
            "architect": [kw for kw in self.ARCHITECT_KEYWORDS if kw in job_text],
        }
        
        _, selected = self.select_resume(job)
        
        explanation = f"Selected: {selected.upper()} resume\n\n"
        explanation += "Keyword matches:\n"
        for rtype, kws in matches.items():
            if kws:
                explanation += f"  {rtype}: {', '.join(kws[:5])}\n"
        
        return explanation


# Singleton instance
_selector = None


def get_resume_selector() -> ResumeSelector:
    """Get the global resume selector instance"""
    global _selector
    if _selector is None:
        _selector = ResumeSelector()
    return _selector
