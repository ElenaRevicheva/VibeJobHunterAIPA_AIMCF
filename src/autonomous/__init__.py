"""
Autonomous Job Hunting Engine

The most advanced AI-powered job hunting system ever built.
Runs 24/7, finds jobs, researches companies, contacts founders, and tracks results.
"""

from .orchestrator import AutonomousOrchestrator
from .job_monitor import JobMonitor
from .company_researcher import CompanyResearcher
from .founder_finder import FounderFinder
from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler

# NEW: Safe ATS Integration (non-breaking, can disable via env var)
try:
    from .ats_integration import get_ats_jobs_safely
except ImportError:
    # Fallback if ats_scraper not available
    async def get_ats_jobs_safely(*args, **kwargs):
        return []

__all__ = [
    "AutonomousOrchestrator",
    "JobMonitor",
    "CompanyResearcher",
    "FounderFinder",
    "MessageGenerator",
    "MultiChannelSender",
    "DemoTracker",
    "ResponseHandler",
    "get_ats_jobs_safely",  # NEW: Safe addition
]
