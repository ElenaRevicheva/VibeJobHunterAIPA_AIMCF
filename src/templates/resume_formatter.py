"""
Professional resume formatter using Elena's FINAL polished template
Generates ATS-optimized resumes matching Elena's style
"""
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from ..core.models import Profile, JobPosting


class ResumeFormatter:
    """Format resumes using Elena's FINAL professional template"""
    
    def __init__(self):
        # Use Elena's FINAL resume (from aideazz-private-docs)
        self.template_path = Path(__file__).parent / "resume_final_elena.md"
        
        # Fallback to generic template if final not available
        if not self.template_path.exists():
            self.template_path = Path(__file__).parent / "resume_template.md"
    
    def format_resume(self, profile: Profile, job: JobPosting) -> str:
        """
        Generate resume using professional format
        
        Args:
            profile: Candidate profile
            job: Target job posting
            
        Returns:
            Formatted resume in markdown
        """
        # Build customized resume sections
        header = self._format_header(profile)
        summary = self._format_summary(profile, job)
        skills = self._format_skills(profile, job)
        achievements = self._format_achievements(profile, job)
        experience = self._format_experience(profile, job)
        portfolio = self._format_portfolio(profile)
        education = self._format_education(profile)
        contact = self._format_contact(profile)
        
        # Assemble resume
        resume = f"""{header}

---

## PROFESSIONAL SUMMARY

{summary}

---

## TECHNICAL SKILLS

{skills}

---

## KEY ACHIEVEMENTS

{achievements}

---

## PROFESSIONAL EXPERIENCE

{experience}

---

## APPLICATIONS PORTFOLIO

{portfolio}

---

## EDUCATION & CONTINUOUS LEARNING

{education}

---

## LANGUAGES

{self._format_languages(profile)}

---

## CONTACT

{contact}

---

*Tailored for {job.company} - {job.title}*  
*Generated: {datetime.now().strftime('%B %Y')}*
"""
        
        return resume
    
    def _format_header(self, profile: Profile) -> str:
        """Format header with name and title"""
        return f"""# {profile.name.upper()}
**AI Engineer & Founder | Former Chief Legal Officer**"""
    
    def _format_summary(self, profile: Profile, job: JobPosting) -> str:
        """Format professional summary tailored to job"""
        # Extract relevant experience
        years = profile.experience_years
        
        summary = f"""Results-driven AI Engineer and Founder combining {years} years of C-suite strategic experience with full-stack engineering expertise. Solo-built 6 production AI applications in 7 months, achieving 98% cost reduction vs traditional development. Proven ability to ship fast, execute efficiently, and deliver business impact through technical innovation.

**Key Strengths relevant to {job.company}:**
- **Technical Excellence:** 50,000+ lines of production code | 8+ AI model integrations | Full-stack TypeScript/Python
- **Strategic Leadership:** {years} years as Chief Legal Officer | Digital transformation | Cross-functional team management
- **Execution Speed:** 6 production apps in 7 months | 10x faster than traditional teams
- **Capital Efficiency:** Built for <$15K vs $950K traditional budget | 98% cost reduction"""
        
        return summary
    
    def _format_skills(self, profile: Profile, job: JobPosting) -> str:
        """Format skills section, prioritizing job requirements"""
        # Get job requirements
        job_text = (job.title + " " + job.description).lower()
        
        # Categorize skills
        languages = []
        frameworks = []
        ai_ml = []
        databases = []
        tools = []
        
        for skill in profile.skills:
            skill_lower = skill.lower()
            if any(lang in skill_lower for lang in ['python', 'typescript', 'javascript', 'sql']):
                languages.append(skill)
            elif any(fw in skill_lower for lang in ['react', 'next', 'node', 'express']):
                frameworks.append(skill)
            elif any(ai in skill_lower for ai in ['openai', 'claude', 'gpt', 'ai', 'ml']):
                ai_ml.append(skill)
            elif any(db in skill_lower for db in ['mongo', 'postgres', 'supabase']):
                databases.append(skill)
            else:
                tools.append(skill)
        
        # Add standard skills if not present
        if not languages:
            languages = ['TypeScript', 'Python', 'JavaScript', 'SQL', 'HTML/CSS']
        if not frameworks:
            frameworks = ['React', 'Next.js', 'Node.js', 'Express']
        if not ai_ml:
            ai_ml = ['OpenAI API', 'Anthropic Claude', 'Google Gemini', 'ElevenLabs', 'AssemblyAI']
        if not databases:
            databases = ['MongoDB', 'PostgreSQL', 'Supabase']
        if not tools:
            tools = ['Git', 'GitHub', 'Docker', 'Vercel', 'Railway']
        
        skills_text = f"""**Languages:** {', '.join(languages[:6])}  
**Frameworks:** {', '.join(frameworks[:5])}  
**AI/ML:** {', '.join(ai_ml[:8])}  
**Databases:** {', '.join(databases[:4])}  
**Tools & Platforms:** {', '.join(tools[:6])}  
**Methodologies:** Agile, Solo-founder MVP development, Rapid prototyping, CI/CD"""
        
        return skills_text
    
    def _format_achievements(self, profile: Profile, job: JobPosting) -> str:
        """Format key achievements"""
        achievements = profile.key_achievements[:7]
        
        formatted = ""
        for ach in achievements:
            formatted += f"✅ **{ach}**  \n"
        
        return formatted.strip()
    
    def _format_experience(self, profile: Profile, job: JobPosting) -> str:
        """Format work experience"""
        exp_text = ""
        
        for work in profile.work_history[:2]:  # Top 2 roles
            exp_text += f"""### {work.get('title', 'N/A')} | {work.get('company', 'N/A')}
**{work.get('period', 'N/A')}**

{work.get('description', 'N/A')}

---

"""
        
        return exp_text.strip()
    
    def _format_portfolio(self, profile: Profile) -> str:
        """Format portfolio section"""
        portfolio = """### AIP@ - AI Personal Assistant ⭐
**Live Demo:** wa.me/50766623757

Advanced WhatsApp-based AI assistant with voice conversation capabilities:
- **Tech Stack:** TypeScript, OpenAI, Anthropic, Gemini, ElevenLabs, AssemblyAI, MongoDB
- **Features:** Voice conversations, multi-model AI switching, context awareness
- **Impact:** Real-time processing, 99%+ uptime, natural conversation flow

### EspaLuz - Language Learning Platform
Spanish learning platform for Russian speakers (150M potential market):
- **Tech Stack:** React, Node.js, OpenAI, MongoDB
- **Features:** AI-generated lessons, cultural context, gamification

### ATUONA - Business Management Platform
AI-powered business assistant and workflow automation:
- **Tech Stack:** Next.js, TypeScript, Supabase, OpenAI
- **Features:** Task management, document analysis, insights

*Plus 3 additional production applications*"""
        
        return portfolio
    
    def _format_education(self, profile: Profile) -> str:
        """Format education section"""
        return """**Law Degree** - Legal and business foundation

**Self-Taught Full-Stack Engineer:**
- Advanced TypeScript/JavaScript
- Python for AI/ML
- System design and architecture
- AI model integration and optimization
- Cloud infrastructure and DevOps

**Continuous Learning:**
- AI/ML advancements (LLMs, voice AI, agent systems)
- Advanced system design patterns
- Performance optimization
- Security best practices"""
    
    def _format_languages(self, profile: Profile) -> str:
        """Format languages section"""
        if profile.languages:
            return '\n'.join([f"**{lang.split('(')[0].strip()}:** {lang.split('(')[1].strip(')')} if '(' in lang else 'Fluent'" 
                            for lang in profile.languages])
        
        return """**English:** Fluent (Business & Technical)  
**Spanish:** Fluent (Business & Technical)  
**Russian:** Native"""
    
    def _format_contact(self, profile: Profile) -> str:
        """Format contact section"""
        contact = f"""📧 **Email:** {profile.email}  
💬 **Live Demo:** wa.me/50766623757 (try it now!)  
🌐 **Website:** {profile.website_url}  
🔗 **LinkedIn:** {profile.linkedin_url}"""
        
        if profile.github_url:
            contact += f"\n💻 **GitHub:** {profile.github_url}"
        
        return contact
