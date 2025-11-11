#!/bin/bash
# 🚀 Railway Entrypoint for VibeJobHunter Autonomous Engine

set -e

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
echo "   Telegram: ${TELEGRAM_ENABLED:-disabled}"
echo ""

# Run autonomous mode with interval from env var (default 1 hour)
exec python -m src.main autonomous --interval "${AUTONOMOUS_INTERVAL:-1}"
