#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard
Railway production entrypoint

MODE:
- Web server
- ATS Job Hunter
- LinkedIn CMO posting
(all running in ONE service — restored)
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
DEPLOY_TIMESTAMP = "20251215_210000"  # ⬅️ UPDATE ON EACH DEPLOY
DEPLOY_FINGERPRINT = "phase0_job_gate_plus_cmo_restored"
GIT_COMMIT_SHORT = "restore_cmo_loop"

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
# Initialize Database
# ------------------------------------------------------------------
logger.info("💾 Initializing database...")
try:
    from src.database.database_models import init_database
    init_database()
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Database init skipped: {e}")

# ------------------------------------------------------------------
# Background task starter
# ------------------------------------------------------------------
async def start_background_tasks():
    """
    Starts ATS Job Hunter + LinkedIn CMO loops
    """
    logger.info("🧠 Starting background agents...")

    # -------------------------------
    # ATS Job Hunter
    # -------------------------------
    try:
        from src.runners.ats_runner import ats_background_loop
        asyncio.create_task(ats_background_loop())
        logger.info("🧠 ATS hourly background runner STARTED")
    except Exception as e:
        logger.error(f"❌ Failed to start ATS runner: {e}")

    # -------------------------------
    # LinkedIn CMO (RESTORED)
    # -------------------------------
    try:
        from src.cmo.linkedin_cmo import linkedin_cmo_loop
        asyncio.create_task(linkedin_cmo_loop())
        logger.info("📣 LinkedIn CMO Agent STARTED")
    except Exception as e:
        logger.error(f"❌ Failed to start LinkedIn CMO: {e}")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    logger.info("🚀 Starting VibeJobHunter Web Server...")

    try:
        from src.api.app import create_app
        app = create_app()
        logger.info("✅ FastAPI app created")
    except Exception as e:
        logger.error(f"❌ Failed to create FastAPI app: {e}")
        raise

    @app.on_event("startup")
    async def on_startup():
        await start_background_tasks()

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
