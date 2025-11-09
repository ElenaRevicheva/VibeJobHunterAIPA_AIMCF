#!/bin/bash
# VibeJobHunter - Quick run script

set -e

echo "🚀 VibeJobHunter"
echo "==============="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "📝 Please edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get it from: https://console.anthropic.com/"
    echo ""
    exit 1
fi

# Check if profile exists
if [ ! -f data/profiles/profile.json ]; then
    echo "📋 No profile found. Let's set one up!"
    echo ""
    
    # Check if resume exists
    RESUME=$(find . -maxdepth 1 -name "*.pdf" | head -1)
    
    if [ -z "$RESUME" ]; then
        echo "❌ No PDF resume found in current directory"
        echo "   Please run: python -m src.main setup --resume YOUR_RESUME.pdf"
        exit 1
    fi
    
    echo "Found resume: $RESUME"
    python -m src.main setup --resume "$RESUME"
    echo ""
fi

# Show menu
echo "What would you like to do?"
echo ""
echo "1) 🔍 Search for jobs"
echo "2) 📝 Apply to top matches"
echo "3) 📊 Check status"
echo "4) 📬 Check follow-ups"
echo "5) 🌐 Launch dashboard"
echo "6) ❌ Exit"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "🔍 Searching for jobs..."
        python -m src.main search --limit 50 --min-score 65
        ;;
    2)
        echo ""
        read -p "How many jobs to apply to? [5]: " num
        num=${num:-5}
        python -m src.main apply --top $num
        ;;
    3)
        echo ""
        python -m src.main status
        ;;
    4)
        echo ""
        python -m src.main followup
        ;;
    5)
        echo ""
        echo "🌐 Launching dashboard..."
        echo "   Open http://localhost:8000 in your browser"
        echo "   Press Ctrl+C to stop"
        echo ""
        python -m src.main dashboard
        ;;
    6)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
