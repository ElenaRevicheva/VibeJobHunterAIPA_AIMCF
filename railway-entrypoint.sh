#!/bin/bash
# 🚀 Railway Entrypoint for VibeJobHunter Autonomous Engine

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║  🧠✨ AI MARKETING CO-FOUNDER v5.0 - DIGNIFIED POSITIONING! ✨🧠 ║"
echo "║                                                                   ║"
echo "║  📅 BUILD: November 24, 2025 19:46 UTC                           ║"
echo "║  🕒 Daily Posts: 3 PM PANAMA (20:00 UTC) ⏰                       ║"
echo "║  🎯 GIT COMMIT: 68075b1 (Time Change + v5.0!)                    ║"
echo "║                                                                   ║"
echo "║  🎯 EMOTIONALLY INTELLIGENT AI - 9 Products (5 AIPAs + 4 Apps)   ║"
echo "║  🔗 ALL 9 VERIFIED LINKS | 🌍 Bilingual EN/ES                    ║"
echo "║  🚀 POSTS STARTING TODAY AT 3 PM PANAMA!                         ║"
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

# Run autonomous mode with interval from env var (default 1 hour)
exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
