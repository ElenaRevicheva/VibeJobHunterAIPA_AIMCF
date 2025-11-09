#!/bin/bash
# 🚀 VIBE MODE - One command to rule them all

clear

echo "🎯 VIBE JOB HUNTER - AUTOPILOT MODE"
echo "===================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python first."
    exit 1
fi

echo "✓ Python found"

# Check/install dependencies
if [ ! -d "venv" ] && [ ! -f ".deps_installed" ]; then
    echo ""
    echo "📦 Installing dependencies (one-time setup)..."
    pip install -r requirements.txt > /dev/null 2>&1
    touch .deps_installed
    echo "✓ Dependencies installed"
fi

# Check .env
if [ ! -f ".env" ]; then
    echo ""
    echo "🔑 API Key Setup"
    echo ""
    read -p "Enter your Anthropic API key (sk-ant-...): " api_key
    echo "ANTHROPIC_API_KEY=$api_key" > .env
    echo "✓ API key saved"
fi

echo ""
echo "🚀 LAUNCHING AUTOPILOT..."
echo ""
sleep 1

# Find resume
RESUME=$(find . -maxdepth 1 -name "*.pdf" -name "*Resume*" -o -name "*resume*" | head -1)

if [ -z "$RESUME" ]; then
    echo "❌ No resume PDF found in current directory"
    echo "   Add your resume.pdf here and run again"
    exit 1
fi

echo "📄 Using resume: $RESUME"
echo ""

# RUN AUTOPILOT
python -m src.main autopilot --resume "$RESUME" --count 10

echo ""
echo "🎉 AUTOPILOT COMPLETE!"
echo ""
echo "📊 Check your stats: python -m src.main status"
echo "🔄 Run again tomorrow: ./vibe.sh"
echo ""
echo "Your next role is coming! 🚀✨"
