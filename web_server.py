#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard
Railway production entrypoint
"""

# ------------------------------------------------------------------
# FIX PYTHON PATH (CRITICAL FOR RAILWAY)
# ------------------------------------------------------------------
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# ------------------------------------------------------------------
# Standard imports
# ------------------------------------------------------------------
import logging
import uvicorn

# ------------------------------------------------------------------
# DEPLOYMENT FINGERPRINT (Railway verification)
# ------------------------------------------------------------------
DEPLOY_FINGERPRINT = "DEPLOY_FINGERPRINT=2025-12-13_job_engine_focus_v1"

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"[DEPLOY VERIFY] {DEPLOY_FINGERPRINT}")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    """Start the FastAPI web server"""

    # Import from src package
    from src.api.app import create_app

    logger.info("🚀 Starting VibeJobHunter Web Server...")
    logger.info("📊 GA4 Dashboard will be available at /analytics/dashboard")

    app = create_app()

    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"

    logger.info(f"🌐 Server starting on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
