#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard

MODE:
- Web server (FastAPI)
- ATS Job Hunter
- LinkedIn CMO posting

ALL running in ONE Railway service (restored correctly)
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

# ------------------------------------------------------------------
# DEPLOYMENT FINGERPRINT (Railway verification)
# ------------------------------------------------------------------
DEPLOY_TIMESTAMP = "20251216_120000"  # ⬅️ UPDATE EACH DEPLOY
DEPLOY_FINGERPRINT = "single_service_orchestrator_DELAYED_START_FIXED"
GIT_COMMIT_SHORT = "fix_healthcheck_delayed_orchestrator"

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
logger.info("🚀 " + "DEPLOYMENT VERIFICATION".center(76) + " 🚀")
logger.info("=" * 80)
logger.info(f"📅 DEPLOY_TIMESTAMP: {DEPLOY_TIMESTAMP}")
logger.info(f"🔖 DEPLOY_FINGERPRINT: {DEPLOY_FINGERPRINT}")
logger.info(f"💾 GIT_COMMIT: {GIT_COMMIT_SHORT}")
logger.info(f"⏰ SERVER_START_TIME: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
logger.info("=" * 80)
logger.info("🌐 SINGLE-SERVICE MODE: Web + ATS + LinkedIn CMO")
logger.info("=" * 80)

# ------------------------------------------------------------------
# Initialize Database (safe)
# ------------------------------------------------------------------
logger.info("💾 Initializing database...")
try:
    from src.database.database_models import init_database
    init_database()
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Database initialization skipped: {e}")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    logger.info("🚀 Starting VibeJobHunter Web Server...")

    # -------------------------------
    # Create FastAPI app
    # -------------------------------
    try:
        from src.api.app import create_app
        app = create_app()
        logger.info("✅ FastAPI app created")
    except Exception as e:
        logger.error(f"❌ Failed to create FastAPI app: {e}")
        raise

    # ------------------------------------------------------------------
    # START AUTONOMOUS ORCHESTRATOR (ATS + LINKEDIN CMO)
    # ------------------------------------------------------------------
    @app.on_event("startup")
    async def startup_event():
        try:
            logger.info("🧠 Initializing candidate profile...")

            from src.core.models import Profile
            from src.core.config import settings
            from src.autonomous.orchestrator import AutonomousOrchestrator

            # -------------------------------
            # CREATE PROFILE (REQUIRED)
            # -------------------------------
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

            logger.info("✅ Profile initialized successfully")

            orchestrator = AutonomousOrchestrator(profile=profile)

            # ----------------------------------------------------------
            # CRITICAL FIX: DELAY AUTONOMOUS START (RAILWAY SAFE)
            # ----------------------------------------------------------
            async def delayed_orchestrator_start():
                logger.info("⏳ Waiting 15s before starting autonomous mode...")
                await asyncio.sleep(15)
                logger.info("🚀 Starting autonomous mode now")
                await orchestrator.start_autonomous_mode()

            asyncio.create_task(delayed_orchestrator_start())

            logger.info("✅ Autonomous orchestrator scheduled successfully")

        except Exception:
            logger.error("❌ Failed to start autonomous orchestrator")
            import traceback
            logger.error(traceback.format_exc())

    # -------------------------------
    # Server configuration
    # -------------------------------
    port = int(os.getenv("PORT", 8080))
    host = "0.0.0.0"

    logger.info("=" * 80)
    logger.info("🌐 Server Configuration")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    logger.info(f"   Deploy Time: {DEPLOY_TIMESTAMP}")
    logger.info("=" * 80)
    logger.info("📊 Routes:")
    logger.info("   /analytics/dashboard")
    logger.info("   /docs")
    logger.info("   /health")
    logger.info("   /version")
    logger.info("=" * 80)

    # -------------------------------
    # Run server
    # -------------------------------
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=65,
        limit_concurrency=100,
        limit_max_requests=1000,
    )

# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------
if __name__ == "__main__":
    main()


