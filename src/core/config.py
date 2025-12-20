from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict
from pathlib import Path
import os


class Settings(BaseSettings):
    """
    Global application settings - ALIGNED WITH GOLDEN ROADMAP v2
    Used by ATS + Autonomous Orchestrator + LinkedIn CMO
    """

    # -------------------------------------------------
    # API KEYS (from environment)
    # -------------------------------------------------
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # -------------------------------------------------
    # IDENTITY
    # -------------------------------------------------
    FULL_NAME: str = "Elena Revicheva"
    EMAIL: str = "aipa@aideazz.xyz"
    WHATSAPP: str = "https://wa.me/50761666716"
    TELEGRAM: str = "https://t.me/ElenaRevicheva"

    # -------------------------------------------------
    # CAREER PROFILE (from Golden Roadmap v2)
    # -------------------------------------------------

    PRIMARY_ROLES: List[str] = [
        "Founding Engineer",
        "Senior AI Engineer",
        "Staff AI Engineer",
        "AI Product Engineer",
        "Principal Engineer",
        "AI Solutions Architect",
        "Technical Lead",
    ]

    SECONDARY_ROLES: List[str] = [
        "AI Product Manager",
        "AI Growth Engineer",
    ]

    TARGET_ROLES: List[str] = [
        "Founding Engineer",
        "Senior AI Engineer",
        "Staff AI Engineer",
        "AI Product Engineer",
        "Principal Engineer",
        "AI Solutions Architect",
        "Technical Lead",
        "AI Product Manager",
        "AI Growth Engineer",
        "LLM Engineer",
        "Full-Stack AI Engineer",
    ]

    YEARS_EXPERIENCE: int = 10
    LOCATION: str = "Panama City, Panama"
    REMOTE_PREFERENCE: bool = True

    LANGUAGES: List[str] = ["English", "Spanish", "Russian"]

    # -------------------------------------------------
    # TECHNICAL SKILLS
    # -------------------------------------------------
    SKILLS: List[str] = [
        "GPT", "Claude", "Groq", "Whisper", "TTS", "MCP", "LangChain", "ElizaOS",
        "LLMs", "Autonomous Agents", "AI Infrastructure",
        "Python", "TypeScript", "JavaScript", "Node.js", "SQL",
        "React", "Flask", "FastAPI", "Express.js", "Vite",
        "PostgreSQL", "Docker", "Railway", "Oracle Cloud",
        "Polygon", "Thirdweb", "IPFS", "DAO",
        "WhatsApp API", "Telegram API", "GitHub API",
        "0-to-1 Building", "Startup", "Product Strategy",
    ]

    # -------------------------------------------------
    # COMPENSATION FLOORS
    # -------------------------------------------------
    SALARY_FLOORS: Dict[str, int] = {
        "US": 150000,
        "GLOBAL_REMOTE": 150000,
        "EUROPE": 90000,
        "LATAM": 100000,
    }

    MIN_SALARY_DEFAULT: int = 100000

    # -------------------------------------------------
    # COMPANY CRITERIA
    # -------------------------------------------------
    COMPANY_SIZE_MAX: int = 100
    COMPANY_STAGES: List[str] = ["Seed", "Series A", "Series B"]

    # -------------------------------------------------
    # LINKS & FILES
    # -------------------------------------------------
    # PDF resume for ATS submissions (env var takes precedence)
    RESUME_PATH: str = os.getenv("RESUME_PATH", "autonomous_data/resumes/elena_resume.pdf")

    LINKEDIN_URL: str = "https://www.linkedin.com/in/elenarevicheva/"
    GITHUB_URL: str = "https://github.com/ElenaRevicheva"
    PORTFOLIO_URL: str = "https://aideazz.xyz/card"
    WEBSITE_URL: str = "https://aideazz.xyz"

    # -------------------------------------------------
    # RUNTIME
    # -------------------------------------------------
    ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "local")

    # -------------------------------------------------
    # DATA STORAGE
    # -------------------------------------------------
    data_dir: Path = Path("autonomous_data")

    # -------------------------------------------------
    # APPLICATION LIMITS
    # -------------------------------------------------
    max_daily_applications: int = 5
    max_total_applications: int = 30
    min_match_score: int = 55

    # -------------------------------------------------
    # LOWERCASE ALIASES
    # -------------------------------------------------
    @property
    def target_roles(self) -> List[str]:
        return self.TARGET_ROLES

    # -------------------------------------------------
    # Pydantic v2 config (CRITICAL FIX)
    # -------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",   # 🔥 ALLOWS Railway / local env vars safely
    )


# -------------------------------------------------
# Singleton
# -------------------------------------------------
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings singleton"""
    return settings

