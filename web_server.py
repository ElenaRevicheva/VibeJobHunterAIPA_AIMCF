#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard
Run with: python web_server.py
"""
import os
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

    from src.api.app import create_app

    logger.info("🚀 Starting VibeJobHunter Web Server...")
    logger.info("✅ FastAPI app initialized")
    logger.info("📊 GA4 Dashboard will be available at /analytics/dashboard")

    app = create_app()

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🌐 Server starting on {host}:{port}")
    logger.info("📡 Endpoints available:")
    logger.info("   - http://localhost:8000/ (Main App)")
    logger.info("   - http://localhost:8000/analytics/dashboard (GA4 Dashboard)")
    logger.info("   - http://localhost:8000/analytics/health (Health Check)")
    logger.info("   - http://localhost:8000/docs (API Documentation)")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )

if __name__ == "__main__":
    main()

