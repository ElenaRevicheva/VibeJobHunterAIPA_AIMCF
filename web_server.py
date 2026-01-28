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
# ------------------------------------------------------------------
# Load .env file for environment variables
# ------------------------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

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
DEPLOY_TIMESTAMP = "20251223_151500"  # ⬅️ UPDATE EACH DEPLOY
DEPLOY_FINGERPRINT = "CTO_AIPA_INTEGRATION_LIVE"
GIT_COMMIT_SHORT = "cto_aipa_endpoints_v1"
CTO_INTEGRATION_VERSION = "1.0_ADDITIVE_SAFE"  # 🤖 CTO↔CMO Bridge

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
logger.info(f"🤖 CTO INTEGRATION: {CTO_INTEGRATION_VERSION}")
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
            "fingerprint": DEPLOY_FINGERPRINT,
            "cto_integration": CTO_INTEGRATION_VERSION,
            "components": {
                "web": "running",
                "ats_scraper": "active",
                "linkedin_cmo": "scheduled",
                "telegram_bot": "active",
                "cto_aipa_bridge": "active"
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
    # CTO AIPA INTEGRATION (SAFE, ADDITIVE)
    # ─────────────────────────────
    # SAFETY GUARANTEE:
    # - These endpoints ONLY store data to a separate file
    # - They do NOT modify any existing posting logic
    # - LinkedIn CMO reads this file OPTIONALLY - if read fails, regular posting continues
    # - This is a ONE-WAY bridge: CTO sends → CMO reads when convenient
    # ─────────────────────────────
    
    @app.post("/api/tech-update")
    async def receive_tech_update(request_data: dict):
        """
        Receive tech updates from CTO AIPA for LinkedIn posts.
        
        SAFE: Only stores data. Does NOT modify posting logic.
        CMO will check for updates at post time and include if available.
        If no updates or read fails, CMO continues with regular content.
        """
        import json
        from pathlib import Path
        from datetime import datetime
        
        logger.info(f"📥 [CTO Integration] Received tech update from CTO AIPA")
        
        try:
            storage_dir = Path("cto_aipa_updates")
            storage_dir.mkdir(exist_ok=True)
            storage_file = storage_dir / "pending_tech_updates.json"
            
            # Load existing updates (safe - defaults to empty list)
            existing = []
            if storage_file.exists():
                try:
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                except Exception as read_err:
                    logger.warning(f"⚠️ [CTO Integration] Could not read existing updates: {read_err}")
                    existing = []
            
            # Create new update entry
            new_update = {
                **request_data,
                "received_at": datetime.now().isoformat(),
                "posted": False
            }
            
            # Add to front, keep max 20
            existing.insert(0, new_update)
            existing = existing[:20]
            
            # Save (atomic write would be better but this is safe enough)
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            
            pending_count = len([u for u in existing if not u.get('posted')])
            logger.info(f"✅ [CTO Integration] Tech update stored. Pending: {pending_count}")
            
            return {
                "status": "success",
                "message": "Tech update received. CMO will feature it in next daily post (4:30 PM Panama).",
                "update": new_update,
                "pending_count": pending_count,
                "fingerprint": DEPLOY_FINGERPRINT
            }
        except Exception as e:
            logger.error(f"❌ [CTO Integration] Error storing update: {e}")
            # Return error but don't crash - this is non-critical
            return {"status": "error", "message": str(e), "fingerprint": DEPLOY_FINGERPRINT}
    
    @app.get("/api/tech-updates/pending")
    async def get_pending_updates():
        """
        Get pending tech updates from CTO AIPA.
        
        SAFE: Read-only endpoint. Returns empty list if no updates or on error.
        """
        import json
        from pathlib import Path
        
        storage_file = Path("cto_aipa_updates/pending_tech_updates.json")
        
        if not storage_file.exists():
            return {
                "status": "success", 
                "count": 0, 
                "updates": [],
                "fingerprint": DEPLOY_FINGERPRINT
            }
        
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                updates = json.load(f)
            pending = [u for u in updates if not u.get('posted', False)]
            return {
                "status": "success", 
                "count": len(pending), 
                "updates": pending,
                "fingerprint": DEPLOY_FINGERPRINT
            }
        except Exception as e:
            logger.warning(f"⚠️ [CTO Integration] Error reading updates: {e}")
            return {
                "status": "error", 
                "message": str(e),
                "fingerprint": DEPLOY_FINGERPRINT
            }
    
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


