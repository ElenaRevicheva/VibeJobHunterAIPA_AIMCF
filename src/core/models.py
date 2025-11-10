"""
Data models for VibeJobHunter
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    """Status of job application"""
    FOUND = "found"
    REVIEWED = "reviewed"
    TAILORED = "tailored"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobSource(str, Enum):
    """Source of job posting"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    ANGELLIST = "angellist"
    YCOMBINATOR = "ycombinator"
    TWITTER = "twitter"
    COMPANY_WEBSITE = "company_website"
    REFERRAL = "referral"
    OTHER = "other"


class Profile(BaseModel):
    """User profile and preferences"""
    name: str
    email: str
    phone: Optional[str] = None
    location: str
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    website_url: Optional[str] = None
    
    # Skills and experience
    skills: List[str] = []
    languages: List[str] = []
    experience_years: int = 0
    
    # Resume data
    resume_path: str
    resume_text: str = ""
    key_achievements: List[str] = []
    work_history: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    
    # Preferences
    target_roles: List[str] = []
    target_locations: List[str] = []
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    remote_only: bool = False
    
    # Extended candidate data (for smart matching)
    candidate_data: Optional[Dict[str, Any]] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class JobPosting(BaseModel):
    """Job posting information"""
    id: str = Field(default="")
    title: str
    company: str
    location: str
    description: str
    requirements: List[str] = []
    responsibilities: List[str] = []
    
    # Details
    source: JobSource
    url: str
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Contract
    remote_allowed: bool = False
    
    # Match score
    match_score: float = 0.0
    match_reasons: List[str] = []
    red_flags: List[str] = []
    criteria_match: Optional[Dict[str, Any]] = None
    talking_points: List[str] = []  # Specific talking points for this job
    
    # Application tracking
    applied: bool = False
    application_date: Optional[datetime] = None
    status: ApplicationStatus = ApplicationStatus.FOUND
    
    # Generated content
    tailored_resume: Optional[str] = None
    cover_letter: Optional[str] = None
    
    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    notes: str = ""
    
    class Config:
        use_enum_values = True


class Application(BaseModel):
    """Job application tracking"""
    id: str
    job_id: str
    job_title: str
    company: str
    
    # Application details
    status: ApplicationStatus
    applied_date: datetime
    source: JobSource
    application_url: Optional[str] = None
    
    # Generated materials
    resume_version: str
    cover_letter_content: Optional[str] = None
    
    # Timeline
    timeline: List[Dict[str, Any]] = []  # Status changes, interviews, etc.
    
    # Follow-up
    next_follow_up: Optional[datetime] = None
    follow_up_count: int = 0
    
    # Interview prep
    interview_date: Optional[datetime] = None
    interview_notes: str = ""
    interview_prep: Optional[Dict[str, Any]] = None
    
    # Outcome
    offer_details: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class NetworkingContact(BaseModel):
    """Networking contact information"""
    id: str
    name: str
    company: Optional[str] = None
    title: Optional[str] = None
    
    # Contact info
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    email: Optional[str] = None
    
    # Relationship
    connection_type: str  # recruiter, engineer, founder, etc.
    contacted: bool = False
    contact_date: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    
    # Notes
    notes: str = ""
    conversation_history: List[Dict[str, Any]] = []
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DailyStats(BaseModel):
    """Daily statistics"""
    date: str
    jobs_discovered: int = 0
    jobs_reviewed: int = 0
    applications_sent: int = 0
    responses_received: int = 0
    interviews_scheduled: int = 0
    networking_contacts_made: int = 0
