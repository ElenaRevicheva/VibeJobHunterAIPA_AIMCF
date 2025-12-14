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
echo "║  🎯 AUTO-APPLICATIONS ENABLED! 3 jobs/hour                       ║"
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
mkdir -p autonomous_data logs tailored_resumes cover_letters autonomous_data/applications
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
    echo "🚀 Starting ALL THREE: Web Server + LinkedIn CMO + Auto-Apply Job Hunter..."
    echo ""
    
    # 1. Start Autonomous Job Hunting Orchestrator in background
    echo "🎯 [1/3] Starting Autonomous Job Hunting with Auto-Applications..."
    python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}" &
    ORCHESTRATOR_PID=$!
    echo "   ✅ Orchestrator PID: $ORCHESTRATOR_PID"
    echo ""
    
    # Wait a moment for orchestrator to initialize
    sleep 2
    
    # 2. Start LinkedIn CMO in background
    echo "📱 [2/3] Starting LinkedIn CMO (Daily Posts at 4:30 PM Panama)..."
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
    CMO_PID=$!
    echo "   ✅ LinkedIn CMO PID: $CMO_PID"
    echo ""
    
    # 3. Start web server in foreground
    echo "🌐 [3/3] Starting Web Server (GA4 Dashboard on port 8080)..."
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║  🎉 ALL SYSTEMS OPERATIONAL! 🎉                                   ║"
    echo "║                                                                   ║"
    echo "║  1. 🤖 Job Hunter:    Finding & applying to jobs hourly          ║"
    echo "║  2. 📱 LinkedIn CMO:  Posting daily at 4:30 PM Panama            ║"
    echo "║  3. 🌐 Web Server:    GA4 Dashboard on port 8080                 ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    exec python web_server.py
else
    echo "🤖 Starting Autonomous Job Hunting mode..."
    # Run autonomous mode with interval from env var (default 1 hour)
    exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
fi