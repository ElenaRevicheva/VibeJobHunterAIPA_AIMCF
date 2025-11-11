"""
Profile manager for user data
"""
import json
import PyPDF2
from pathlib import Path
from typing import Optional
from anthropic import Anthropic

from .models import Profile
from .config import get_settings


class ProfileManager:
    """Manages user profile and resume data"""
    
    def __init__(self):
        self.settings = get_settings()
        self.profile_path = self.settings.data_dir / "profiles" / "profile.json"
        self.profile: Optional[Profile] = None
        self.ai = Anthropic(api_key=self.settings.anthropic_api_key) if self.settings.anthropic_api_key else None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF resume"""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF: {e}")
        return text
    
    def parse_resume_with_ai(self, resume_text: str) -> dict:
        """Use Claude to parse resume into structured data"""
        if not self.ai:
            return {}
        
        prompt = f"""Analyze this resume and extract structured information. Return JSON format with these fields:
- name: Full name
- email: Email address
- phone: Phone number
- location: Current location
- linkedin_url: LinkedIn profile URL
- github_url: GitHub profile URL
- portfolio_url: Portfolio URL
- website_url: Website URL
- skills: List of technical skills
- languages: List of languages spoken
- experience_years: Years of professional experience (estimate)
- key_achievements: List of 5-7 key achievements (bullet points)
- work_history: List of work experiences with {{"title": "", "company": "", "period": "", "description": ""}}
- education: List of education with {{"degree": "", "institution": "", "year": ""}}
- target_roles: List of suitable job titles based on experience

Resume:
{resume_text}

Return only valid JSON, no other text."""

        try:
            response = self.ai.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text
            # Extract JSON if wrapped in code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_text)
        except Exception as e:
            print(f"Error parsing resume with AI: {e}")
            return {}
    
    def create_profile_from_resume(self, resume_path: str, additional_info: dict = None) -> Profile:
        """Create profile from resume file"""
        # Extract text
        resume_text = self.extract_text_from_pdf(resume_path)
        
        # Parse with AI
        parsed_data = self.parse_resume_with_ai(resume_text)
        
        # Merge with additional info
        if additional_info:
            parsed_data.update(additional_info)
        
        # Ensure required fields
        if "name" not in parsed_data:
            parsed_data["name"] = "Unknown"
        if "email" not in parsed_data:
            parsed_data["email"] = "unknown@example.com"
        if "location" not in parsed_data:
            parsed_data["location"] = "Unknown"
        
        # Create profile
        profile = Profile(
            resume_path=resume_path,
            resume_text=resume_text,
            **parsed_data
        )
        
        self.profile = profile
        return profile
    
    def save_profile(self, profile: Profile = None) -> None:
        """Save profile to disk"""
        if profile:
            self.profile = profile
        
        if not self.profile:
            raise ValueError("No profile to save")
        
        # Ensure directory exists
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile.model_dump(), f, indent=2, default=str)
    
    def load_profile(self) -> Optional[Profile]:
        """Load profile from disk"""
        if not self.profile_path.exists():
            return None
        
        try:
            with open(self.profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.profile = Profile(**data)
                return self.profile
        except Exception as e:
            print(f"Error loading profile: {e}")
            return None
    
    def get_profile(self) -> Optional[Profile]:
        """Get current profile"""
        if not self.profile:
            self.profile = self.load_profile()
        return self.profile
    
    def update_profile(self, updates: dict) -> Profile:
        """Update profile with new data"""
        if not self.profile:
            self.profile = self.load_profile()
        
        if not self.profile:
            raise ValueError("No profile exists")
        
        # Update fields
        for key, value in updates.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
        
        # Save changes
        self.save_profile()
        return self.profile
