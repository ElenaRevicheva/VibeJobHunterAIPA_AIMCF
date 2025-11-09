"""
Portfolio integrator - automatically highlights relevant projects
Adds demo links, QR codes, and live examples
"""
from typing import List, Dict
from ..core.models import JobPosting, Profile
from ..loaders import CandidateDataLoader


class PortfolioIntegrator:
    """Integrate portfolio and live demos into applications"""
    
    def __init__(self):
        self.loader = CandidateDataLoader()
        self.data = self._load_candidate_data()
    
    def _load_candidate_data(self) -> dict:
        """Load full candidate data"""
        try:
            import json
            from pathlib import Path
            data_file = Path(__file__).parent.parent / "core" / "candidate_data.json"
            with open(data_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def get_relevant_projects(self, job: JobPosting, max_projects: int = 3) -> List[Dict]:
        """
        Get most relevant portfolio projects for a job
        
        Args:
            job: Target job posting
            max_projects: Maximum projects to return
            
        Returns:
            List of relevant projects with details
        """
        portfolio = self.data.get('applications_portfolio', [])
        if not portfolio:
            return []
        
        job_text = (job.title + " " + job.description).lower()
        
        # Score projects by relevance
        scored_projects = []
        for project in portfolio:
            score = self._score_project_relevance(project, job_text)
            scored_projects.append((score, project))
        
        # Sort by score and return top N
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        return [proj for score, proj in scored_projects[:max_projects]]
    
    def _score_project_relevance(self, project: Dict, job_text: str) -> int:
        """Score how relevant a project is to the job"""
        score = 0
        
        # Check tech stack match
        tech_stack = project.get('tech_stack', [])
        for tech in tech_stack:
            if tech.lower() in job_text:
                score += 10
        
        # Check description keywords
        description = project.get('description', '').lower()
        if 'ai' in description and 'ai' in job_text:
            score += 15
        if 'whatsapp' in description and 'messaging' in job_text:
            score += 10
        
        # AIP@ is always a strong demo
        if project.get('name') == 'AIP@ (AI Personal Assistant)':
            score += 20  # Bonus for live demo
        
        return score
    
    def format_portfolio_section(self, job: JobPosting) -> str:
        """
        Format portfolio section for resume/cover letter
        
        Args:
            job: Target job posting
            
        Returns:
            Formatted portfolio text
        """
        projects = self.get_relevant_projects(job, max_projects=3)
        
        if not projects:
            return ""
        
        text = "## LIVE PORTFOLIO\n\n"
        
        for project in projects:
            name = project.get('name', 'Project')
            description = project.get('description', '')
            tech_stack = ', '.join(project.get('tech_stack', []))
            demo = project.get('demo', '')
            
            text += f"### {name}\n"
            if demo:
                text += f"**Live Demo:** {demo}\n"
            text += f"{description}\n"
            text += f"**Tech:** {tech_stack}\n\n"
        
        return text
    
    def get_demo_link(self) -> str:
        """Get primary demo link"""
        return "wa.me/50766623757"
    
    def get_website_link(self) -> str:
        """Get website link"""
        contact = self.data.get('candidate', {}).get('contact', {})
        return contact.get('website', 'aideazz.xyz')
    
    def enhance_resume_with_portfolio(self, resume: str, job: JobPosting) -> str:
        """
        Add prominent demo links to resume
        
        Args:
            resume: Original resume text
            job: Target job posting
            
        Returns:
            Enhanced resume with demo links
        """
        demo = self.get_demo_link()
        website = self.get_website_link()
        
        # Add demo link prominently at top if not already there
        if demo not in resume:
            # Find contact section and add demo
            lines = resume.split('\n')
            enhanced_lines = []
            for i, line in enumerate(lines):
                enhanced_lines.append(line)
                # Add after email
                if '📧' in line or 'Email:' in line:
                    enhanced_lines.append(f"💬 **Live Demo:** {demo} ⭐ (try it now!)")
            resume = '\n'.join(enhanced_lines)
        
        return resume
    
    def enhance_cover_letter_with_demo(self, cover_letter: str) -> str:
        """
        Ensure demo link is prominent in cover letter
        
        Args:
            cover_letter: Original cover letter
            
        Returns:
            Enhanced cover letter
        """
        demo = self.get_demo_link()
        
        if demo not in cover_letter:
            # Add demo mention
            lines = cover_letter.split('\n')
            # Insert after opening paragraph
            for i, line in enumerate(lines):
                if i == 2:  # After greeting and opening
                    lines.insert(i+1, f"\n**Live Demo:** You can try my AI assistant right now at {demo} - most candidates talk about what they can build, I show what I've already built.\n")
                    break
            cover_letter = '\n'.join(lines)
        
        return cover_letter
    
    def get_portfolio_highlights(self) -> List[str]:
        """Get key portfolio highlights for applications"""
        return [
            "Live AI assistant with 99%+ uptime (wa.me/50766623757)",
            "6 production applications built in 7 months",
            "8+ AI model integrations (OpenAI, Claude, Gemini, voice AI)",
            "50,000+ lines of production TypeScript/Python code",
            "Working demo available immediately for evaluation"
        ]
