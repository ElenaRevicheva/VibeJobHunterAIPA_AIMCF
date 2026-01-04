"""
📄 RESUME SELECTOR v3 - Smart 3-Way Strategy

Resume Selection Logic:
1. DEFAULT: NEW English resume (ATS-optimized, professional)
2. FOUNDING: OLD English resume (founder energy, emotional branding)  
3. SPANISH: NEW Spanish resume (for LATAM/Spanish companies)

Selection Rules:
- Spanish/LATAM company detected → Spanish resume
- Founding engineer keywords detected → OLD founding resume
- Everything else → NEW default resume (best ATS compatibility)
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ResumeSelector:
    """
    Smart 3-way resume selection:
    - NEW English (default) - ATS-optimized professional format
    - OLD English (founding) - Founder energy for early-stage roles
    - NEW Spanish - For LATAM/Spanish-speaking companies
    """
    
    # Resume paths - PDFs for ATS submission
    RESUME_PDFS = {
        "default": "autonomous_data/resumes/elena_resume_new.pdf",      # NEW English
        "founding": "autonomous_data/resumes/elena_resume_founding.pdf", # OLD English
        "spanish": "autonomous_data/resumes/elena_resume_spanish.pdf",   # NEW Spanish
    }
    
    # Markdown versions for content display and cover letter generation
    RESUMES = {
        "default": "src/templates/resume_new_default.md",      # NEW English
        "founding": "src/templates/resume_old_founding.md",    # OLD English  
        "spanish": "src/templates/resume_new_spanish.md",      # NEW Spanish
    }
    
    # Keywords that trigger the OLD founding resume (founder energy)
    FOUNDING_KEYWORDS = [
        "founding", "founder", "first engineer", "0-1", "zero to one",
        "greenfield", "build from scratch", "early stage", "seed",
        "series a", "equity", "technical co-founder", "cofounder",
        "employee #", "first hire", "build the team"
    ]
    
    # Spanish/LATAM indicators - trigger Spanish resume
    SPANISH_INDICATORS = [
        # Spanish words in job posting
        "ingeniero", "desarrollador", "remoto", "híbrido", "empresa",
        "requisitos", "experiencia", "conocimientos", "habilidades",
        # LATAM countries
        "méxico", "mexico", "argentina", "colombia", "chile", "perú", "peru",
        "ecuador", "venezuela", "panamá", "panama", "costa rica", "guatemala",
        "uruguay", "paraguay", "bolivia", "honduras", "el salvador", "nicaragua",
        "república dominicana", "dominican republic", "puerto rico", "cuba",
        # Spain
        "españa", "spain", "madrid", "barcelona",
        # Spanish company indicators
        "latam", "latinoamérica", "latinoamerica", "hispanic", "español",
        "spanish speaking", "bilingüe", "bilingual spanish"
    ]
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        logger.info("📄 Resume Selector v3 initialized (NEW default | OLD founding | Spanish LATAM)")
    
    def select_resume(self, job: Dict[str, Any]) -> Tuple[str, str]:
        """
        Select the best resume variant for a job
        
        Logic:
        1. Check for Spanish/LATAM → Spanish resume
        2. Check for founding keywords → OLD founding resume
        3. Default → NEW English resume (ATS-optimized)
        
        Args:
            job: Job dict with title, description, company, location, etc.
            
        Returns:
            Tuple of (resume_path, resume_type)
        """
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        company = job.get('company', '').lower()
        location = job.get('location', '').lower()
        
        job_text = f"{title} {description} {company} {location}"
        
        # 1. Check for Spanish/LATAM (highest priority for language match)
        spanish_score = self._score_keywords(job_text, self.SPANISH_INDICATORS)
        if spanish_score >= 2:
            logger.info(f"📄🇪🇸 Spanish resume selected for {company} (score: {spanish_score})")
            return self.RESUMES["spanish"], "spanish"
        
        # 2. Check for founding engineer keywords
        founding_score = self._score_keywords(job_text, self.FOUNDING_KEYWORDS)
        if founding_score >= 2:
            logger.info(f"📄🚀 Founding resume selected for {company} (score: {founding_score})")
            return self.RESUMES["founding"], "founding"
        
        # 3. Default to NEW English resume (best ATS compatibility)
        logger.info(f"📄✨ Default (NEW) resume selected for {company}")
        return self.RESUMES["default"], "default"
    
    def _score_keywords(self, text: str, keywords: list) -> int:
        """Count keyword matches in text"""
        score = 0
        for kw in keywords:
            if kw in text:
                # Higher weight for title/company matches (first 200 chars)
                score += 2 if kw in text[:200] else 1
        return score
    
    def get_resume_content(self, resume_type: str) -> Optional[str]:
        """
        Load resume content from file
        
        Args:
            resume_type: One of 'default', 'founding', 'spanish'
            
        Returns:
            Resume markdown content
        """
        # Check cache
        if resume_type in self._cache:
            return self._cache[resume_type]
        
        resume_path = self.RESUMES.get(resume_type, self.RESUMES["default"])
        
        try:
            # Try multiple base paths for Docker/local compatibility
            for base in [".", "/app", "/workspace"]:
                path = Path(base) / resume_path
                if path.exists():
                    content = path.read_text(encoding='utf-8')
                    self._cache[resume_type] = content
                    logger.debug(f"📄 Loaded resume from {path}")
                    return content
            
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
        company = job.get('company', '').lower()
        location = job.get('location', '').lower()
        job_text = f"{title} {description} {company} {location}"
        
        spanish_matches = [kw for kw in self.SPANISH_INDICATORS if kw in job_text]
        founding_matches = [kw for kw in self.FOUNDING_KEYWORDS if kw in job_text]
        
        _, selected = self.select_resume(job)
        
        resume_names = {
            "default": "NEW English (ATS-optimized)",
            "founding": "OLD English (Founder energy)",
            "spanish": "NEW Spanish (LATAM)"
        }
        
        explanation = f"📄 Selected: {resume_names.get(selected, selected)}\n\n"
        
        if spanish_matches:
            explanation += f"🇪🇸 Spanish indicators: {', '.join(spanish_matches[:5])}\n"
        if founding_matches:
            explanation += f"🚀 Founding indicators: {', '.join(founding_matches[:5])}\n"
        if not spanish_matches and not founding_matches:
            explanation += "✨ No special indicators → Using ATS-optimized default\n"
        
        return explanation
    
    def get_language_for_job(self, job: Dict[str, Any]) -> str:
        """
        Determine the language to use for this job
        
        Returns:
            'en' or 'es'
        """
        _, resume_type = self.select_resume(job)
        return 'es' if resume_type == 'spanish' else 'en'


# Singleton instance
_selector = None


def get_resume_selector() -> ResumeSelector:
    """Get the global resume selector instance"""
    global _selector
    if _selector is None:
        _selector = ResumeSelector()
    return _selector
