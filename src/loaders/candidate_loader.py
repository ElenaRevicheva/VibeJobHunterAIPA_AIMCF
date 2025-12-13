"""
Load pre-configured candidate data from JSON
Instantly creates profile without manual parsing
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..core.models import Profile
from ..core.config import get_settings


class CandidateDataLoader:
    """Load candidate profile from pre-configured JSON"""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_file = self.settings.base_dir / "src" / "core" / "candidate_data.json"
    
    def load_profile(self) -> Optional[Profile]:
        """
        Load Elena's profile from JSON (instant!)
        
        Returns:
            Profile object ready to use
        """
        if not self.data_file.exists():
            print(f"Candidate data file not found: {self.data_file}")
            return None
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            candidate = data.get('candidate', {})
            technical = data.get('technical_skills', {})
            portfolio = data.get('applications_portfolio', [])
            achievements = data.get('key_achievements_metrics', [])
            
            # Extract work history
            work_history = []
            if 'executive_experience' in data:
                exec_exp = data['executive_experience']
                work_history.append({
                    'title': exec_exp.get('title', ''),
                    'company': exec_exp.get('company', ''),
                    'period': exec_exp.get('duration', ''),
                    'description': '\n'.join(exec_exp.get('achievements', []))
                })
            
            # Add current role (Updated Dec 2025)
            work_history.insert(0, {
                'title': 'Founder & AI Engineer',
                'company': 'AIdeazz.xyz',
                'period': 'March 2025 - Present',
                'description': 'Solo-built 11 AI products (7 live AI agents) in 10 months with 99%+ cost reduction. Deployed AI Co-Founders: CTO AIPA (autonomous code reviews) + CMO AIPA (LinkedIn automation) at $0/month operational cost.'
            })
            
            # Create profile
            profile = Profile(
                name=candidate.get('name', 'Elena Revicheva'),
                email=candidate.get('contact', {}).get('email', ''),
                phone='',  # Not in public data
                location=candidate.get('location', 'Panama (Remote globally)'),
                linkedin_url=candidate.get('contact', {}).get('linkedin', ''),
                github_url=candidate.get('contact', {}).get('github', ''),
                portfolio_url=candidate.get('contact', {}).get('website', ''),
                website_url=candidate.get('contact', {}).get('website', ''),
                
                # Resume path (from structured data, not file)
                resume_path=str(self.data_file),
                
                # Skills and experience
                skills=technical.get('languages', []) + technical.get('frameworks', []),
                experience_years=7,  # From executive_experience
                
                # Achievements
                key_achievements=achievements[:10],  # Top 10
                
                # Work and education
                work_history=work_history,
                education=[{
                    'degree': 'Law Degree',
                    'institution': 'University',
                    'year': 'N/A'
                }],
                
                # Job preferences from target_roles
                target_roles=data.get('target_roles', []),
                target_locations=['Remote', 'US', 'Europe', 'LATAM'],
                remote_only=False,
                
                # Languages
                languages=candidate.get('languages', []),
                
                # Resume text (summary)
                resume_text=self._build_resume_text(data),
                
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add extended data for smart matching
            profile.candidate_data = data  # Store full data for advanced features
            
            return profile
        
        except Exception as e:
            print(f"Error loading candidate data: {e}")
            return None
    
    def _build_resume_text(self, data: dict) -> str:
        """Build resume text from data"""
        candidate = data.get('candidate', {})
        
        summary = f"{candidate.get('name', '')} - {candidate.get('title', '')}\n"
        summary += f"{candidate.get('tagline', '')}\n\n"
        
        # Add key achievements
        achievements = data.get('key_achievements_metrics', [])
        summary += "Key Achievements:\n"
        for ach in achievements[:5]:
            summary += f"- {ach}\n"
        
        return summary
    
    def get_target_criteria(self) -> dict:
        """Get target job criteria for smart matching"""
        if not self.data_file.exists():
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'target_roles': data.get('target_roles', []),
                'target_compensation': data.get('target_compensation', {}),
                'target_companies': data.get('target_companies', {}),
                'red_flags_to_avoid': data.get('red_flags_to_avoid', {}),
                'ideal_role_characteristics': data.get('ideal_role_characteristics', {})
            }
        except Exception as e:
            print(f"Error loading target criteria: {e}")
            return {}
    
    def get_email_templates(self) -> dict:
        """Get email templates"""
        if not self.data_file.exists():
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('email_templates', {})
        except Exception as e:
            print(f"Error loading email templates: {e}")
            return {}
    
    def get_interview_prep(self) -> dict:
        """Get interview preparation materials"""
        if not self.data_file.exists():
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'questions_prep': data.get('interview_questions_prep', {}),
                'talking_points': data.get('interview_talking_points', {})
            }
        except Exception as e:
            print(f"Error loading interview prep: {e}")
            return {}
    
    def get_cover_letter_template(self) -> dict:
        """Get cover letter template"""
        if not self.data_file.exists():
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('cover_letter_template', {})
        except Exception as e:
            print(f"Error loading cover letter template: {e}")
            return {}
