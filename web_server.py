#!/usr/bin/env python3
"""
FastAPI Web Server for VibeJobHunter + GA4 Dashboard + Enhanced Telegram Bot
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
import threading
import asyncio

# ------------------------------------------------------------------
# DEPLOYMENT FINGERPRINT (Railway verification)
# ------------------------------------------------------------------
DEPLOY_FINGERPRINT = "phase1_telegram_bot_FINAL"

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"[DEPLOY VERIFY] {DEPLOY_FINGERPRINT}")

# ------------------------------------------------------------------
# START ENHANCED TELEGRAM BOT (Phase 1)
# ------------------------------------------------------------------
logger.info("🤖 Initializing Enhanced Telegram Bot...")
try:
    from src.database.database_models import init_database, DatabaseHelper
    from src.notifications.telegram_bot_enhanced import create_enhanced_bot
    
    # Initialize database
    init_database()
    logger.info("✅ Database initialized")
    
    db_helper = DatabaseHelper()
    logger.info("✅ Database helper created")
    
    # Create bot
    telegram_bot = create_enhanced_bot(db_helper=db_helper)
    logger.info("✅ Enhanced Telegram Bot created")
    
    # Start bot in background thread
    def run_telegram_bot():
        """Run Telegram bot in its own event loop"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def start_bot():
                await telegram_bot.app.initialize()
                await telegram_bot.app.start()
                logger.info("✅ Enhanced Telegram Bot polling started")
                await telegram_bot.app.updater.start_polling()
                # Keep running
                await asyncio.Event().wait()
            
            loop.run_until_complete(start_bot())
        except Exception as e:
            logger.error(f"❌ Telegram bot error: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Start bot thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True, name="TelegramBot")
    bot_thread.start()
    logger.info("✅ ENHANCED TELEGRAM BOT THREAD STARTED!")
    
except Exception as e:
    logger.error(f"❌ Failed to start Enhanced Telegram Bot: {e}")
    import traceback
    logger.error(traceback.format_exc())

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
