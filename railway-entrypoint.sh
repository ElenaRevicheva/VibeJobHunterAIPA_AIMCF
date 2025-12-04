#!/bin/bash
# 🚀 Railway Entrypoint for VibeJobHunter Autonomous Engine

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  🧠✨ AI MARKETING CO-FOUNDER v5.0 - DIGNIFIED POSITIONING! ✨🧠 ║"
echo "║                                                                   ║"
echo "║  📅 BUILD: November 24, 2025 19:46 UTC                           ║"
echo "║  🕒 Daily Posts: 4:30 PM PANAMA (21:30 UTC) ⏰                    ║"
echo "║  🎯 GIT COMMIT: 68075b1 (Time Change + v5.0!)                    ║"
echo "║                                                                   ║"
echo "║  🎯 EMOTIONALLY INTELLIGENT AI - 9 Products (5 AIPAs + 4 Apps)   ║"
echo "║  🔗 ALL 9 VERIFIED LINKS | 🌍 Bilingual EN/ES                    ║"
echo "║  🚀 POSTS DAILY AT 4:30 PM PANAMA!                               ║"
echo "║                                                                   ║"
echo "║  IF YOU SEE v5.0 + 68075b1 = TIME CHANGE DEPLOYED! ✅            ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "🤖 VibeJobHunter Autonomous Engine"
echo "=================================="
echo ""

# Check required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY not set!"
    echo "Please set it in Railway environment variables"
    exit 1
fi

echo "✅ Environment variables loaded"
echo ""

# Setup profile (using Elena's profile by default)
echo "📋 Setting up profile..."
python -m src.main setup --elena || true
echo ""

# Create necessary directories
mkdir -p autonomous_data logs tailored_resumes cover_letters
echo "✅ Directories created"
echo ""

# Start autonomous mode
echo "🚀 Starting autonomous mode..."
echo "   Interval: ${AUTONOMOUS_INTERVAL:-1} hour(s)"
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    echo "   Telegram: ENABLED ✅"
else
    echo "   Telegram: disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable)"
fi
echo ""

# Check if we should run web server, autonomous mode, or both
if [ "$RUN_MODE" = "web" ]; then
    echo "🌐 Starting Web Server mode (with GA4 Dashboard)..."
    exec python web_server.py
elif [ "$RUN_MODE" = "both" ]; then
    echo "🚀 Starting BOTH Web Server AND LinkedIn CMO..."
    # Start LinkedIn CMO in background
    python -c "
import asyncio
import schedule
import time
from datetime import datetime
from src.notifications.linkedin_cmo_v4 import LinkedInCMO

cmo = LinkedInCMO()

def job():
    print(f'⏰ Running LinkedIn CMO at {datetime.now()}')
    asyncio.run(cmo.post_to_linkedin())

# Schedule for 21:30 UTC (4:30 PM Panama)
schedule.every().day.at('21:30').do(job)
print('✅ LinkedIn CMO scheduled for 21:30 UTC daily')

# Also run once at startup if it's the right time
now = datetime.utcnow()
if now.hour == 21 and now.minute >= 25 and now.minute < 35:
    print('🎯 Running LinkedIn CMO now (startup at posting time)')
    job()

while True:
    schedule.run_pending()
    time.sleep(60)
" &
    
    # Start web server in foreground
    exec python web_server.py
else
    echo "🤖 Starting Autonomous Job Hunting mode..."
    # Run autonomous mode with interval from env var (default 1 hour)
    exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
fi
