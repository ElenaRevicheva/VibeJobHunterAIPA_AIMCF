"""
AI-powered content generation for resumes and cover letters
"""
from typing import Optional
from pathlib import Path
from datetime import datetime
from anthropic import Anthropic

from ..core.models import Profile, JobPosting
from ..core.config import get_settings


class ContentGenerator:
    """Generate tailored resumes and cover letters"""
    
    def __init__(self):
        self.settings = get_settings()
        self.ai = Anthropic(api_key=self.settings.anthropic_api_key)
        
        # Output directories
        self.resumes_dir = self.settings.base_dir / "tailored_resumes"
        self.cover_letters_dir = self.settings.base_dir / "cover_letters"
        self.resumes_dir.mkdir(exist_ok=True)
        self.cover_letters_dir.mkdir(exist_ok=True)
    
    def tailor_resume(self, profile: Profile, job: JobPosting) -> str:
        """Generate tailored resume for specific job"""
        prompt = f"""Create a tailored resume for this job application. Emphasize relevant skills and achievements that match the job requirements.

Candidate Profile:
- Name: {profile.name}
- Email: {profile.email}
- Phone: {profile.phone or ""}
- Location: {profile.location}
- LinkedIn: {profile.linkedin_url or ""}
- GitHub: {profile.github_url or ""}
- Portfolio: {profile.portfolio_url or ""}
- Website: {profile.website_url or ""}

Skills: {', '.join(profile.skills)}
Languages: {', '.join(profile.languages)}
Experience: {profile.experience_years} years

Key Achievements:
{chr(10).join([f"• {ach}" for ach in profile.key_achievements])}

Work History:
{self._format_work_history(profile.work_history)}

Education:
{self._format_education(profile.education)}

Target Job:
- Title: {job.title}
- Company: {job.company}
- Requirements: {chr(10).join([f"• {req}" for req in job.requirements[:10]])}

Create a professional resume in markdown format that:
1. Highlights achievements most relevant to this specific role
2. Reorders skills to prioritize those mentioned in job requirements
3. Uses action verbs and quantifiable results
4. Maintains honesty (no fabrication)
5. Optimizes for ATS (Applicant Tracking Systems)
6. Keeps technical accuracy
7. Emphasizes "0-1 builder", "solo execution", and relevant AI/ML experience

Format: Professional markdown suitable for conversion to PDF.
"""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            tailored_resume = response.content[0].text
            
            # Save to file
            filename = f"{job.company}_{job.title}_{datetime.now().strftime('%Y%m%d')}.md"
            filename = filename.replace(" ", "_").replace("/", "-")
            filepath = self.resumes_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(tailored_resume)
            
            return tailored_resume
        
        except Exception as e:
            print(f"Error tailoring resume: {e}")
            return profile.resume_text
    
    def generate_cover_letter(self, profile: Profile, job: JobPosting) -> str:
        """Generate personalized cover letter"""
        prompt = f"""Write a compelling cover letter for this job application. Be authentic, enthusiastic, and specific.

Candidate: {profile.name}
From: {profile.location}
Languages: {', '.join(profile.languages)}

Background:
- {profile.experience_years} years of experience
- Key achievements: {', '.join(profile.key_achievements[:3])}
- Unique value: Solo-built 6 AI products in 7 months for <$15K (vs $900K team cost)
- Skills: {', '.join(profile.skills[:10])}

Target Position:
- Company: {job.company}
- Role: {job.title}
- Location: {job.location}

Job Description Highlights:
{job.description[:800]}

Key Requirements:
{chr(10).join([f"• {req}" for req in job.requirements[:8]])}

Write a cover letter that:
1. Opens with a strong hook related to the company/role
2. Demonstrates genuine interest in the company's mission
3. Highlights 2-3 specific achievements that match job requirements
4. Shows personality and passion for AI/building
5. Explains why this role is a great mutual fit
6. Closes with clear call to action
7. Keeps professional yet warm tone
8. Length: 250-400 words

Be specific, avoid generic phrases, and show you understand what the company does.
"""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            
            cover_letter = response.content[0].text
            
            # Save to file
            filename = f"{job.company}_{job.title}_{datetime.now().strftime('%Y%m%d')}_cover_letter.txt"
            filename = filename.replace(" ", "_").replace("/", "-")
            filepath = self.cover_letters_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cover_letter)
            
            return cover_letter
        
        except Exception as e:
            print(f"Error generating cover letter: {e}")
            return ""
    
    def generate_linkedin_message(self, profile: Profile, job: JobPosting, contact_name: str = "") -> str:
        """Generate LinkedIn outreach message"""
        prompt = f"""Write a brief LinkedIn message to reach out about this job opportunity.

From: {profile.name}
Background: AI Engineer, built 6 AI products solo
Skills: {', '.join(profile.skills[:5])}

Job:
- Company: {job.company}
- Role: {job.title}

To: {contact_name or "Hiring Manager"}

Write a short, personalized LinkedIn message (100-150 words) that:
1. Introduces yourself briefly
2. Mentions specific interest in the company/role
3. Highlights 1-2 relevant achievements
4. Requests a conversation
5. Is friendly and professional, not salesy

Keep it conversational and human.
"""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
        
        except Exception as e:
            print(f"Error generating LinkedIn message: {e}")
            return f"Hi! I'm interested in the {job.title} role at {job.company}. Would love to chat!"
    
    def _format_work_history(self, work_history: list) -> str:
        """Format work history for prompt"""
        if not work_history:
            return "No work history provided"
        
        formatted = []
        for work in work_history:
            formatted.append(
                f"• {work.get('title', 'N/A')} at {work.get('company', 'N/A')} "
                f"({work.get('period', 'N/A')})\n  {work.get('description', '')}"
            )
        return "\n".join(formatted)
    
    def _format_education(self, education: list) -> str:
        """Format education for prompt"""
        if not education:
            return "No education provided"
        
        formatted = []
        for edu in education:
            formatted.append(
                f"• {edu.get('degree', 'N/A')}, {edu.get('institution', 'N/A')} "
                f"({edu.get('year', 'N/A')})"
            )
        return "\n".join(formatted)
    
    def generate_interview_prep(self, profile: Profile, job: JobPosting) -> dict:
        """Generate interview preparation materials"""
        prompt = f"""Create interview preparation materials for this job.

Candidate: {profile.name}
Experience: {profile.experience_years} years
Skills: {', '.join(profile.skills[:15])}
Key Projects: {', '.join(profile.key_achievements[:3])}

Job:
- Company: {job.company}
- Role: {job.title}
- Requirements: {', '.join(job.requirements[:8])}

Provide in JSON format:
{{
  "company_research": ["fact1", "fact2", "fact3"],
  "likely_questions": [
    {{"question": "...", "suggested_answer": "..."}},
    ...
  ],
  "questions_to_ask": ["question1", "question2", ...],
  "key_points_to_emphasize": ["point1", "point2", ...],
  "potential_challenges": ["challenge1", "challenge2", ...],
  "salary_negotiation_tips": ["tip1", "tip2", ...]
}}

Focus on technical questions for AI/ML roles and behavioral questions for cultural fit.
"""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3072,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result_text = response.content[0].text
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_text)
        
        except Exception as e:
            print(f"Error generating interview prep: {e}")
            return {}
