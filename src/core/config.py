from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """
    Global application settings
    Used by ATS + Autonomous Orchestrator + LinkedIn CMO
    """

    # -------------------------------------------------
    # IDENTITY
    # -------------------------------------------------
    FULL_NAME: str = "Elena Revicheva"
    EMAIL: str = "elena.revicheva2016@gmail.com"

    # -------------------------------------------------
    # CAREER PROFILE
    # -------------------------------------------------
    TARGET_ROLES: List[str] = [
        "AI Engineer",
        "AI Product Manager",
        "AI Startup Founder",
        "Technical Co-Founder",
        "AI Solutions Architect",
    ]

    YEARS_EXPERIENCE: int = 8
    LOCATION: str = "Remote / Panama"
    REMOTE_PREFERENCE: bool = True

    SKILLS: List[str] = [
        "Artificial Intelligence",
        "LLMs",
        "Autonomous Agents",
        "Python",
        "FastAPI",
        "Startup Building",
        "Product Strategy",
        "Web3",
        "AI Infrastructure",
    ]

    # -------------------------------------------------
    # LINKS & FILES
    # -------------------------------------------------
    RESUME_PATH: str = "data/resume.pdf"

    LINKEDIN_URL: str = "https://www.linkedin.com/in/elena-revicheva/"
    GITHUB_URL: str = "https://github.com/ElenaRevicheva"
    PORTFOLIO_URL: str = "https://aideazz.xyz"

    # -------------------------------------------------
    # RUNTIME
    # -------------------------------------------------
    ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "local")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton (IMPORTANT)
settings = Settings()
