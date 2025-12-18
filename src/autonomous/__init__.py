"""
Autonomous Job Hunting Engine

The most advanced AI-powered job hunting system ever built.
Runs 24/7, finds jobs, researches companies, contacts founders, and tracks results.
"""

from .orchestrator import AutonomousOrchestrator
from .job_monitor import JobMonitor
from .company_researcher import CompanyResearcher

# ✅ UPGRADED: Use v2 explicitly
from .founder_finder_v2 import FounderFinderV2

from .message_generator import MessageGenerator
from .multi_channel_sender import MultiChannelSender
from .demo_tracker import DemoTracker
from .response_handler import ResponseHandler

# NEW: Safe ATS Integration (non-breaking, optional)
try:
    from .ats_integration import get_ats_jobs_safely
except ImportError:
    async def get_ats_jobs_safely(*args, **kwargs):
        return []

__all__ = [
    "AutonomousOrchestrator",
    "JobMonitor",
    "CompanyResearcher",
    "FounderFinderV2",  # ✅ Correct export
    "MessageGenerator",
    "MultiChannelSender",
    "DemoTracker",
    "ResponseHandler",
    "get_ats_jobs_safely",
]
