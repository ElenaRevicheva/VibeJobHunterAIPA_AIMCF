"""
FastAPI application for web dashboard
"""

import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Internal imports (ABSOLUTE — Railway safe)
# ------------------------------------------------------------------
from src.core import ProfileManager
from src.agents import ApplicationManager
from src.job_engine.ats_runner import ats_background_loop

# ------------------------------------------------------------------
# GA4 Dashboard (optional, backward compatible)
# ------------------------------------------------------------------
try:
    from src.api.ga_dashboard_routes import router as analytics_router
    ANALYTICS_AVAILABLE = True
    logger.info("✅ Successfully imported GA4 analytics router")
except Exception as e:
    ANALYTICS_AVAILABLE = False
    analytics_router = None
    logger.error(f"❌ Failed to import GA4 analytics router: {e}")

# ==================================================================
# APP FACTORY
# ==================================================================
def create_app() -> FastAPI:
    app = FastAPI(
        title="VibeJobHunter Dashboard",
        description="AI-powered job hunting automation dashboard",
        version="1.0.0",
    )

    # --------------------------------------------------------------
    # CORS
    # --------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------
    # BACKGROUND JOBS (ATS RUNNER)
    # --------------------------------------------------------------
    @app.on_event("startup")
    async def start_background_jobs():
        logger.info("🧠 ATS hourly background runner STARTED")
        asyncio.create_task(ats_background_loop())

    # --------------------------------------------------------------
    # ROUTES
    # --------------------------------------------------------------
    if ANALYTICS_AVAILABLE and analytics_router:
        app.include_router(analytics_router)
        logger.info("✅ GA4 Analytics routes registered")

    profile_manager = ProfileManager()
    app_manager = ApplicationManager()

    # --------------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return "<h1>🚀 VibeJobHunter Dashboard is running</h1>"

    # --------------------------------------------------------------
    # API
    # --------------------------------------------------------------
    @app.get("/api/stats")
    async def get_stats():
        return app_manager.get_summary_stats()

    @app.get("/api/profile")
    async def get_profile():
        profile = profile_manager.get_profile()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile.model_dump()

    @app.get("/api/jobs")
    async def get_jobs(limit: int = 50, min_score: float = 0):
        jobs = [j for j in app_manager.jobs.values() if j.match_score >= min_score]
        jobs.sort(key=lambda j: j.match_score, reverse=True)
        return [j.model_dump() for j in jobs[:limit]]

    @app.get("/api/jobs/top")
    async def get_top_jobs(limit: int = 10):
        jobs = app_manager.get_top_matches(limit=limit)
        return [j.model_dump() for j in jobs]

    @app.get("/api/applications")
    async def get_applications(status: Optional[str] = None):
        if status:
            from src.core.models import ApplicationStatus
            try:
                status_enum = ApplicationStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")
            apps = app_manager.get_applications_by_status(status_enum)
        else:
            apps = app_manager.applications.values()

        return [a.model_dump() for a in apps]

    return app
