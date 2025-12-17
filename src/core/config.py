from pydantic_settings import BaseSettings
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
    WHATSAPP: str = "https://wa.me/50766623757"
    TELEGRAM: str = "https://t.me/espaluzfamily_bot"

    # -------------------------------------------------
    # CAREER PROFILE (from Golden Roadmap v2)
    # -------------------------------------------------
    
    # PRIMARY TARGET ROLES (High Priority - apply if ≥75% fit)
    PRIMARY_ROLES: List[str] = [
        "Founding Engineer",
        "Senior AI Engineer",
        "Staff AI Engineer", 
        "AI Product Engineer",
        "Principal Engineer",
        "AI Solutions Architect",
        "Technical Lead",
    ]
    
    # SECONDARY ROLES (Conditional - early-stage/technical orgs only)
    SECONDARY_ROLES: List[str] = [
        "AI Product Manager",
        "AI Growth Engineer",
    ]
    
    # Combined for backward compatibility
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

    YEARS_EXPERIENCE: int = 10  # 7 years C-suite + 1 year AI building + 2 years startup
    LOCATION: str = "Panama City, Panama"
    REMOTE_PREFERENCE: bool = True
    
    # Languages (for bilingual matching)
    LANGUAGES: List[str] = ["English", "Spanish", "Russian"]

    # -------------------------------------------------
    # TECHNICAL SKILLS (from Elena's resume)
    # -------------------------------------------------
    SKILLS: List[str] = [
        # AI/ML
        "GPT", "Claude", "Groq", "Whisper", "TTS", "MCP", "LangChain", "ElizaOS",
        "LLMs", "Autonomous Agents", "AI Infrastructure",
        # Languages
        "Python", "TypeScript", "JavaScript", "Node.js", "SQL",
        # Frameworks
        "React", "Flask", "FastAPI", "Express.js", "Vite",
        # Infrastructure
        "PostgreSQL", "Docker", "Railway", "Oracle Cloud",
        # Web3
        "Polygon", "Thirdweb", "IPFS", "DAO",
        # APIs
        "WhatsApp API", "Telegram API", "GitHub API",
        # Methodologies
        "0-to-1 Building", "Startup", "Product Strategy",
    ]

    # -------------------------------------------------
    # COMPENSATION FLOORS (from Golden Roadmap v2)
    # -------------------------------------------------
    SALARY_FLOORS: Dict[str, int] = {
        "US": 150000,      # $150K-$220K base
        "GLOBAL_REMOTE": 150000,
        "EUROPE": 90000,   # €90K-€140K
        "LATAM": 100000,   # $100K minimum
    }
    
    MIN_SALARY_DEFAULT: int = 100000  # Default floor

    # -------------------------------------------------
    # COMPANY CRITERIA (from Golden Roadmap v2)
    # -------------------------------------------------
    COMPANY_SIZE_MAX: int = 100  # No companies with 20+ engineers
    COMPANY_STAGES: List[str] = ["Seed", "Series A", "Series B"]

    # -------------------------------------------------
    # LINKS & FILES
    # -------------------------------------------------
    RESUME_PATH: str = "src/templates/resume_final_elena.md"

    LINKEDIN_URL: str = "https://www.linkedin.com/in/elenarevicheva/"
    GITHUB_URL: str = "https://github.com/ElenaRevicheva"
    PORTFOLIO_URL: str = "https://aideazz.xyz"
    WEBSITE_URL: str = "https://aideazz.xyz/card"

    # -------------------------------------------------
    # RUNTIME
    # -------------------------------------------------
    ENVIRONMENT: str = os.getenv("RAILWAY_ENVIRONMENT", "local")

    # -------------------------------------------------
    # DATA STORAGE
    # -------------------------------------------------
    data_dir: Path = Path("autonomous_data")
    
    # -------------------------------------------------
    # APPLICATION LIMITS (from Golden Roadmap v2)
    # -------------------------------------------------
    max_daily_applications: int = 5   # 3-5 per day
    max_total_applications: int = 30  # 20-30 before reassessment
    min_match_score: int = 55         # Minimum score to apply

    # -------------------------------------------------
    # LOWERCASE ALIASES (for compatibility)
    # -------------------------------------------------
    @property
    def target_roles(self) -> List[str]:
        return self.TARGET_ROLES

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton (IMPORTANT)
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings singleton"""
    return settings
