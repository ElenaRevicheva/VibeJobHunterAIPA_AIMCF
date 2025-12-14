#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard
Railway production entrypoint

NOTE: Telegram bot runs ONLY in orchestrator, NOT here!
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
DEPLOY_FINGERPRINT = "phase1_NO_BOT_in_webserver"

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"[DEPLOY VERIFY] {DEPLOY_FINGERPRINT}")
logger.info("=" * 60)
logger.info("🌐 WEB SERVER MODE - Bot runs in orchestrator only")
logger.info("=" * 60)

# ------------------------------------------------------------------
# Initialize Database (but not bot)
# ------------------------------------------------------------------
logger.info("💾 Initializing database...")
try:
    from src.database.database_models import init_database
    
    # Initialize database tables
    init_database()
    logger.info("✅ Database initialized successfully")
    
except Exception as e:
    logger.warning(f"⚠️  Database initialization skipped: {e}")
    logger.info("ℹ️  This is OK if database isn't needed for web server")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    """Start the FastAPI web server"""
    
    logger.info("🚀 Starting VibeJobHunter Web Server...")
    
    # Import from src package
    try:
        from src.api.app import create_app
        
        app = create_app()
        logger.info("✅ FastAPI app created")
        
    except Exception as e:
        logger.error(f"❌ Failed to create FastAPI app: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

    # Server configuration
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    
    logger.info("=" * 60)
    logger.info(f"🌐 Server Configuration:")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    logger.info("=" * 60)
    logger.info("📊 GA4 Dashboard: /analytics/dashboard")
    logger.info("🔍 API Docs: /docs")
    logger.info("📡 Health Check: /health")
    logger.info("=" * 60)
    logger.info("")
    logger.info("🤖 NOTE: Telegram bot runs in orchestrator only!")
    logger.info("   To start bot: Run orchestrator separately")
    logger.info("=" * 60)

    # Start server
    try:
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
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
