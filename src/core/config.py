"""
Configuration management for VibeJobHunter
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    # Job Platform Credentials
    linkedin_email: Optional[str] = Field(default=None, alias="LINKEDIN_EMAIL")
    linkedin_password: Optional[str] = Field(default=None, alias="LINKEDIN_PASSWORD")
    indeed_api_key: Optional[str] = Field(default=None, alias="INDEED_API_KEY")
    
    # Social Media
    twitter_api_key: Optional[str] = Field(default=None, alias="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, alias="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(default=None, alias="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: Optional[str] = Field(default=None, alias="TWITTER_ACCESS_SECRET")
    
    # Email Settings
    email_address: Optional[str] = Field(default=None, alias="EMAIL_ADDRESS")
    email_password: Optional[str] = Field(default=None, alias="EMAIL_PASSWORD")
    smtp_server: str = Field(default="smtp.gmail.com", alias="SMTP_SERVER")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    
    # Application Settings
    max_daily_applications: int = Field(default=20, alias="MAX_DAILY_APPLICATIONS")
    auto_apply_enabled: bool = Field(default=False, alias="AUTO_APPLY_ENABLED")
    notification_email: Optional[str] = Field(default=None, alias="NOTIFICATION_EMAIL")
    
    # Database
    database_url: str = Field(default="sqlite:///./vibejobhunter.db", alias="DATABASE_URL")
    
    # Dashboard
    dashboard_port: int = Field(default=8000, alias="DASHBOARD_PORT")
    dashboard_host: str = Field(default="0.0.0.0", alias="DASHBOARD_HOST")
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    templates_dir: Path = base_dir / "templates"
    logs_dir: Path = base_dir / "logs"
    
    # Job Search Preferences
    target_roles: List[str] = [
        "AI Engineer",
        "Founding Engineer", 
        "Full-Stack AI Engineer",
        "LLM Engineer",
        "AI Product Manager",
        "AI Solutions Architect",
        "AI Growth Engineer",
        "ML Engineer",
        "NLP Engineer"
    ]
    
    target_locations: List[str] = [
        "Remote",
        "Panama City",
        "United States",
        "Europe",
        "Latin America"
    ]
    
    target_keywords: List[str] = [
        "AI",
        "Machine Learning",
        "LLM",
        "GPT",
        "Claude",
        "NLP",
        "Python",
        "TypeScript",
        "React",
        "Startup",
        "0-1",
        "Founding",
        "Web3",
        "Blockchain"
    ]
    
    excluded_keywords: List[str] = [
        "PhD required",
        "10+ years required",
        "on-site only",
        "relocation required"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
