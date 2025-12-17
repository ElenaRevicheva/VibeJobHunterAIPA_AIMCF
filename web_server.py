#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard

MODE:
- Web server (FastAPI)
- ATS Job Hunter (hourly)
- LinkedIn CMO posting (daily 4:30 PM Panama)
- Telegram Bot (always-on)

ALL running in ONE Railway service
"""

# ------------------------------------------------------------------
# FIX PYTHON PATH (CRITICAL FOR RAILWAY)
# ------------------------------------------------------------------
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# ------------------------------------------------------------------
# Standard imports
# ------------------------------------------------------------------
import logging
import uvicorn
import time
import asyncio
from contextlib import asynccontextmanager

# ------------------------------------------------------------------
# DEPLOYMENT FINGERPRINT (Railway verification)
# ------------------------------------------------------------------
DEPLOY_TIMESTAMP = "20251216_210000"  # ⬅️ UPDATE EACH DEPLOY
DEPLOY_FINGERPRINT = "phase3_bugs_FIXED_v2"
GIT_COMMIT_SHORT = "ashby_cache_db_fixes"

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# DEPLOYMENT VERIFICATION BANNER
# ------------------------------------------------------------------
logger.info("=" * 80)
logger.info("🚀 VIBEJOBHUNTER DEPLOYMENT")
logger.info("=" * 80)
logger.info(f"📅 DEPLOY: {DEPLOY_TIMESTAMP}")
logger.info(f"🔖 FINGERPRINT: {DEPLOY_FINGERPRINT}")
logger.info(f"💾 COMMIT: {GIT_COMMIT_SHORT}")
logger.info(f"⏰ START: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
logger.info("=" * 80)

# ------------------------------------------------------------------
# Initialize Database (safe)
# ------------------------------------------------------------------
logger.info("💾 Initializing database...")
try:
    from src.database.database_models import init_database
    init_database()
    logger.info("✅ Database initialized")
except Exception as e:
    logger.warning(f"⚠️ Database init skipped: {e}")

# ------------------------------------------------------------------
# Global orchestrator reference
# ------------------------------------------------------------------
orchestrator = None

# ------------------------------------------------------------------
# Lifespan context manager (replaces deprecated on_event)
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app):
    """
    Modern lifespan pattern for FastAPI startup/shutdown
    """
    global orchestrator
    
    # ─────────────────────────────
    # STARTUP
    # ─────────────────────────────
    logger.info("🚀 Starting VibeJobHunter services...")
    
    try:
        from src.core.models import Profile
        from src.core.config import settings
        from src.autonomous.orchestrator import AutonomousOrchestrator
        
        # Create profile
        profile = Profile(
            name=settings.FULL_NAME,
            email=settings.EMAIL,
            target_roles=settings.TARGET_ROLES,
            experience_years=settings.YEARS_EXPERIENCE,
            location=settings.LOCATION,
            remote_only=settings.REMOTE_PREFERENCE,
            skills=settings.SKILLS,
            resume_path=settings.RESUME_PATH,
            linkedin_url=settings.LINKEDIN_URL,
            github_url=settings.GITHUB_URL,
            portfolio_url=settings.PORTFOLIO_URL,
        )
        
        logger.info("✅ Profile: Elena Revicheva loaded")
        
        # Create orchestrator
        orchestrator = AutonomousOrchestrator(profile=profile)
        
        # Start ATS background runner (optional)
        try:
            from src.job_engine.ats_runner import ats_background_loop
            asyncio.create_task(ats_background_loop())
            logger.info("✅ ATS background runner started")
        except ImportError:
            logger.info("ℹ️ ATS runner module not available (optional)")
        except Exception as e:
            logger.warning(f"⚠️ ATS runner skipped: {e}")
        
        # Delayed start for autonomous mode
        async def delayed_start():
            logger.info("⏳ Waiting 10s for health check to pass...")
            await asyncio.sleep(10)
            logger.info("🚀 Starting autonomous mode...")
            await orchestrator.start_autonomous_mode()
        
        asyncio.create_task(delayed_start())
        logger.info("✅ Autonomous orchestrator scheduled")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    yield  # App is running
    
    # ─────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────
    logger.info("🛑 Shutting down VibeJobHunter...")
    if orchestrator:
        orchestrator.stop()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create app with lifespan
    app = FastAPI(
        title="VibeJobHunter",
        description="AI-powered autonomous job hunting engine",
        version="4.3.0",
        lifespan=lifespan
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ─────────────────────────────
    # ROUTES
    # ─────────────────────────────
    
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "vibejobhunter",
            "version": "4.3.0",
            "deploy": DEPLOY_TIMESTAMP,
            "components": {
                "web": "running",
                "ats_scraper": "active",
                "linkedin_cmo": "scheduled",
                "telegram_bot": "active"
            }
        }
    
    @app.get("/")
    async def root():
        return {"message": "🚀 VibeJobHunter is running!", "docs": "/docs"}
    
    @app.get("/status")
    async def status():
        global orchestrator
        stats = orchestrator.get_stats() if orchestrator else {}
        return {
            "orchestrator": "running" if orchestrator else "not started",
            "stats": stats,
            "deploy": DEPLOY_TIMESTAMP
        }
    
    # Include GA4 analytics routes if available
    try:
        from src.api.ga_dashboard_routes import router as analytics_router
        app.include_router(analytics_router)
        logger.info("✅ GA4 analytics routes loaded")
    except Exception as e:
        logger.warning(f"⚠️ GA4 routes skipped: {e}")
    
    # ATS background runner is now started via lifespan handler
    # (see lifespan() function above)
    
    # ─────────────────────────────
    # SERVER CONFIG
    # ─────────────────────────────
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"
    
    logger.info("=" * 80)
    logger.info("🌐 SERVER READY")
    logger.info(f"   Host: {host}:{port}")
    logger.info(f"   Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    logger.info("   Routes: /health, /status, /docs, /analytics/dashboard")
    logger.info("=" * 80)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=65,
    )


# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------
if __name__ == "__main__":
    main()


