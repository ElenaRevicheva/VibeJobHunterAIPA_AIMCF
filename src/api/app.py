"""
FastAPI application for VibeJobHunter web dashboard

ROLE:
- Web API + Dashboard only
- NO Telegram bot polling
- ATS runner allowed
- Railway healthcheck compatible
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.api.app")

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
    logger.info("✅ GA4 analytics router loaded")
except Exception as e:
    ANALYTICS_AVAILABLE = False
    analytics_router = None
    logger.warning(f"⚠️ GA4 analytics disabled: {e}")

# ------------------------------------------------------------------
# CTO AIPA → CMO pipeline schema
# ------------------------------------------------------------------
class TechUpdatePayload(BaseModel):
    repo: str
    title: str
    description: str
    type: str
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = None
    security_issues: int = 0
    complexity_issues: int = 0

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
        logger.info("📊 GA4 analytics routes registered")

    profile_manager = ProfileManager()
    app_manager = ApplicationManager()

    # --------------------------------------------------------------
    # HEALTH CHECK (Railway REQUIRED)
    # --------------------------------------------------------------
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "service": "vibejobhunter-web",
            "role": "web_dashboard",
            "ats_runner": "active",
        }

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

    # --------------------------------------------------------------
    # CTO → CMO TECH UPDATE WEBHOOK
    # Receives milestones from cto-aipa notifyCMO() and persists them
    # so linkedin_cmo_v4.py can pick them up on next posting cycle.
    # SAFE: never breaks existing posting — falls back gracefully.
    # --------------------------------------------------------------
    TECH_UPDATES_DIR = Path("cto_aipa_updates")
    TECH_UPDATES_FILE = TECH_UPDATES_DIR / "pending_tech_updates.json"

    def _load_updates() -> list:
        """Shared helper — always returns a list, never raises."""
        if not TECH_UPDATES_FILE.exists():
            return []
        try:
            with open(TECH_UPDATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_updates(updates: list) -> None:
        TECH_UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        with open(TECH_UPDATES_FILE, "w", encoding="utf-8") as f:
            json.dump(updates[-100:], f, indent=2, ensure_ascii=False)

    @app.post("/api/tech-update")
    async def receive_tech_update(payload: TechUpdatePayload):
        """Receive milestone from CTO AIPA. Appended to pending_tech_updates.json."""
        try:
            existing = _load_updates()
            entry: Dict[str, Any] = {
                **payload.model_dump(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "posted": False,
                "posted_x": False,
            }
            existing.append(entry)
            _save_updates(existing)
            pending_linkedin = len([u for u in existing if not u.get("posted")])
            pending_x = len([u for u in existing if not u.get("posted_x")])
            logger.info(f"✅ [CTO→CMO] Queued: {payload.repo} — {payload.title}")
            return {"ok": True, "queued": payload.title,
                    "pending_linkedin": pending_linkedin, "pending_x": pending_x}
        except Exception as e:
            logger.error(f"❌ [CTO→CMO] Failed to queue tech update: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # --------------------------------------------------------------
    # X (TWITTER) TECH UPDATE ENDPOINTS
    # Used by dragontrade-agent to pick up and mark tech milestones.
    # Auth: Authorization: Bearer <X_API_SECRET> header.
    # --------------------------------------------------------------
    X_SECRET = os.environ.get("X_UPDATES_SECRET", "")

    def _check_x_auth(request: Request) -> None:
        if not X_SECRET:
            return  # No secret configured → open (dev mode)
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {X_SECRET}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/api/x-updates")
    async def get_x_updates(request: Request, limit: int = 3):
        """Return unposted-on-X tech updates for dragontrade-agent to tweet."""
        _check_x_auth(request)
        updates = _load_updates()
        pending = [u for u in updates if not u.get("posted_x", False)]
        return {"ok": True, "pending": pending[:limit], "total": len(pending)}

    @app.post("/api/x-updates/mark")
    async def mark_x_posted(request: Request):
        """
        Mark a tech update as posted on X.
        Body: { "repo": "...", "timestamp": "..." }
        Matches on repo + timestamp as a unique key.
        """
        _check_x_auth(request)
        body: Dict[str, Any] = await request.json()
        repo = body.get("repo", "")
        ts = body.get("timestamp", "")
        if not repo or not ts:
            raise HTTPException(status_code=400, detail="repo and timestamp required")
        updates = _load_updates()
        marked = False
        for u in updates:
            if u.get("repo") == repo and u.get("timestamp") == ts and not u.get("posted_x"):
                u["posted_x"] = True
                u["posted_x_at"] = datetime.utcnow().isoformat() + "Z"
                marked = True
                break
        if marked:
            _save_updates(updates)
            logger.info(f"✅ [CTO→X] Marked as X-posted: {repo} @ {ts}")
            return {"ok": True, "marked": True}
        return {"ok": True, "marked": False, "note": "not found or already marked"}

    return app
