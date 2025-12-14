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
import time

# ------------------------------------------------------------------
# DEPLOYMENT FINGERPRINT (Railway verification)
# ------------------------------------------------------------------
DEPLOY_TIMESTAMP = "20251214_205500"  # ← UPDATE THIS EACH DEPLOY!
DEPLOY_FINGERPRINT = "phase1_NO_BOT_in_webserver_FIXED"
GIT_COMMIT_SHORT = "email_fix"  # Latest fix identifier

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ULTRA-VISIBLE DEPLOYMENT VERIFICATION
logger.info("=" * 80)
logger.info("🚀 " + "DEPLOYMENT VERIFICATION".center(76) + " 🚀")
logger.info("=" * 80)
logger.info(f"📅 DEPLOY_TIMESTAMP: {DEPLOY_TIMESTAMP}")
logger.info(f"🔖 DEPLOY_FINGERPRINT: {DEPLOY_FINGERPRINT}")
logger.info(f"💾 GIT_COMMIT: {GIT_COMMIT_SHORT}")
logger.info(f"⏰ SERVER_START_TIME: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
logger.info("=" * 80)
logger.info("🌐 WEB SERVER MODE - Bot runs in orchestrator only")
logger.info("🔧 FIXES: F-string syntax error + Bot conflict resolved")
logger.info("=" * 80)

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
    port = int(os.getenv("PORT", 8080))  # Railway uses PORT env var
    host = "0.0.0.0"
    
    logger.info("=" * 80)
    logger.info(f"🌐 Server Configuration:")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'local')}")
    logger.info(f"   Deploy Time: {DEPLOY_TIMESTAMP}")
    logger.info("=" * 80)
    logger.info("📊 Routes Available:")
    logger.info("   /analytics/dashboard - GA4 Dashboard")
    logger.info("   /docs - API Documentation")
    logger.info("   /health - Health Check")
    logger.info("   /version - Deployment Version")
    logger.info("=" * 80)
    logger.info("")
    logger.info("🤖 IMPORTANT: Telegram bot runs in orchestrator only!")
    logger.info("   Web server: API + Dashboard")
    logger.info("   Orchestrator: Job hunting + Bot")
    logger.info("   Both run as separate processes on Railway")
    logger.info("=" * 80)

    # Start server
    try:
        logger.info(f"🌐 Starting Uvicorn server on {host}:{port}...")
        
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