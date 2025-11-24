#!/bin/bash
# 🚀 Railway Entrypoint for VibeJobHunter Autonomous Engine

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  🧠🔥 VIBEJOBHUNTER v4.0 - TRUE AI CO-FOUNDER! 🔥🧠              ║"
echo "║                                                                   ║"
echo "║  📅 BUILD: November 23, 2025 21:35 UTC                           ║"
echo "║  🎯 GIT COMMIT: ca0320c (FULL AI Co-Founder Capabilities!)       ║"
echo "║  🧠 FEATURES: 4 Strategic Capabilities ACTIVE                    ║"
echo "║     1. Performance Tracking  2. Learning & Adaptation            ║"
echo "║     3. Strategic Decisions   4. Market Intelligence              ║"
echo "║  🌍 Daily Posts: 11 AM Panama (16:00 UTC)                        ║"
echo "║                                                                   ║"
echo "║  IF YOU SEE v4.0 + ca0320c = TRUE AI CO-FOUNDER DEPLOYED! ✅     ║"
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

# Run autonomous mode with interval from env var (default 1 hour)
exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
