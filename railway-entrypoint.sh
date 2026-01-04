#!/bin/bash
# 🚀 Railway Entrypoint for VibeJobHunter Autonomous Engine

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  🧠✨ AI MARKETING CO-FOUNDER v5.1 - UTC TIME FIX! ✨🧠           ║"
echo "║                                                                   ║"
echo "║  📅 BUILD: January 4, 2026 - UTC Time Fix                        ║"
echo "║  🕒 Daily Posts: 21:XX UTC (4:30 PM PANAMA) ⏰                    ║"
echo "║  🔧 FIX: datetime.utcnow() for consistent scheduling             ║"
echo "║                                                                   ║"
echo "║  🎯 EMOTIONALLY INTELLIGENT AI - 11 Products                     ║"
echo "║  🔗 ALL VERIFIED LINKS | 🌍 Bilingual EN/ES                      ║"
echo "║  🚀 POSTS DAILY VIA ORCHESTRATOR (no duplicate scheduler)        ║"
echo "║  🎯 AUTO-APPLICATIONS ENABLED! 3 jobs/hour                       ║"
echo "║                                                                   ║"
echo "║  CHANGES: UTC time fix + removed duplicate CMO scheduler ✅      ║"
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
    echo "🚀 Starting: Web Server + Autonomous Job Hunter (includes LinkedIn CMO)..."
    echo ""
    
    # 1. Start Autonomous Job Hunting Orchestrator in background
    # NOTE: The orchestrator INCLUDES LinkedIn CMO scheduling (21:XX UTC daily)
    # No separate LinkedIn CMO process needed - this prevents double-posting!
    echo "🎯 [1/2] Starting Autonomous Job Hunting with Auto-Applications..."
    echo "   📱 LinkedIn CMO: Built-in, posts daily at 21:XX UTC (4:30 PM Panama)"
    python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}" &
    ORCHESTRATOR_PID=$!
    echo "   ✅ Orchestrator PID: $ORCHESTRATOR_PID (includes LinkedIn CMO scheduler)"
    echo ""
    
    # Wait a moment for orchestrator to initialize
    sleep 2
    
    # 2. Start web server in foreground
    echo "🌐 [2/2] Starting Web Server (GA4 Dashboard on port 8080)..."
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║  🎉 ALL SYSTEMS OPERATIONAL! 🎉                                   ║"
    echo "║                                                                   ║"
    echo "║  1. 🤖 Job Hunter:    Finding & applying to jobs hourly          ║"
    echo "║     📱 LinkedIn CMO:  Built-in, posts daily at 4:30 PM Panama    ║"
    echo "║  2. 🌐 Web Server:    GA4 Dashboard on port 8080                 ║"
    echo "║                                                                   ║"
    echo "║  NOTE: LinkedIn CMO now uses UTC time (datetime.utcnow)          ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    exec python web_server.py
else
    echo "🤖 Starting Autonomous Job Hunting mode..."
    echo "   📱 LinkedIn CMO: Built-in, posts daily at 21:XX UTC"
    # Run autonomous mode with interval from env var (default 1 hour)
    exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
fi
