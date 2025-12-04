#!/usr/bin/env python3
"""
Test script for Google Analytics 4 Performance Tracker
Run this to verify your GA4 setup is working correctly
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.performance_tracker import GA4PerformanceTracker
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_ga_setup():
    """Test GA4 configuration and connectivity"""
    
    console.print("\n")
    console.print(Panel(
        "[bold cyan]🧪 Google Analytics 4 Setup Test[/bold cyan]\n"
        "[dim]Testing your GA4 configuration...[/dim]",
        style="cyan"
    ))
    
    # Check environment variables
    console.print("\n[bold]Step 1: Checking Environment Variables[/bold]")
    
    ga_creds = os.getenv('GOOGLE_ANALYTICS_CREDENTIALS')
    ga_property = os.getenv('GA4_PROPERTY_ID')
    ga_measurement = os.getenv('GA4_MEASUREMENT_ID')
    
    if ga_creds:
        console.print("  ✅ GOOGLE_ANALYTICS_CREDENTIALS is set")
    else:
        console.print("  ❌ GOOGLE_ANALYTICS_CREDENTIALS is NOT set")
        
    if ga_property:
        console.print(f"  ✅ GA4_PROPERTY_ID is set: {ga_property}")
    else:
        console.print("  ❌ GA4_PROPERTY_ID is NOT set")
        
    if ga_measurement:
        console.print(f"  ✅ GA4_MEASUREMENT_ID is set: {ga_measurement}")
    else:
        console.print("  ⚠️  GA4_MEASUREMENT_ID is NOT set (optional)")
    
    # Initialize tracker
    console.print("\n[bold]Step 2: Initializing GA4 Performance Tracker[/bold]")
    
    try:
        tracker = GA4PerformanceTracker()
        console.print("  ✅ Tracker initialized successfully")
        
        if tracker.client:
            console.print("  ✅ GA4 API client connected")
        else:
            console.print("  ⚠️  GA4 API client not connected (will use mock data)")
            
    except Exception as e:
        console.print(f"  ❌ Failed to initialize tracker: {e}")
        return False
    
    # Test fetching data
    console.print("\n[bold]Step 3: Testing Data Fetch[/bold]")
    
    try:
        metrics = tracker.get_website_metrics(days=7)
        
        if tracker.client:
            console.print("  ✅ Successfully fetched GA4 data")
            console.print(f"     Users: {metrics.get('users', 0)}")
            console.print(f"     Sessions: {metrics.get('sessions', 0)}")
            console.print(f"     Pageviews: {metrics.get('pageviews', 0)}")
        else:
            console.print("  ⚠️  Using mock data (GA4 not configured)")
            
    except Exception as e:
        console.print(f"  ❌ Failed to fetch data: {e}")
        return False
    
    # Summary
    console.print("\n")
    
    if tracker.client and ga_property:
        console.print(Panel(
            "[bold green]✅ SUCCESS![/bold green]\n\n"
            "Your Google Analytics 4 setup is working correctly!\n\n"
            "Next steps:\n"
            "1. Add GA tracking code to aideazz.xyz\n"
            "2. Wait 24-48 hours for data collection\n"
            "3. Run: python -m src.dashboard.performance_tracker\n",
            style="green"
        ))
        return True
    else:
        console.print(Panel(
            "[bold yellow]⚠️  SETUP INCOMPLETE[/bold yellow]\n\n"
            "GA4 Performance Tracker is installed but not fully configured.\n\n"
            "To complete setup:\n"
            "1. Follow GOOGLE_ANALYTICS_SETUP_COMPLETE.md\n"
            "2. Add environment variables to Railway/your environment\n"
            "3. Run this test again\n\n"
            "Current status: Tracker will use mock data until configured.",
            style="yellow"
        ))
        return False

def show_quick_start():
    """Show quick start guide"""
    console.print("\n")
    console.print(Panel(
        "[bold]🚀 Quick Start Guide[/bold]\n\n"
        "1. Environment Variables Needed:\n"
        "   - GOOGLE_ANALYTICS_CREDENTIALS (JSON credentials)\n"
        "   - GA4_PROPERTY_ID (your property ID number)\n"
        "   - GA4_MEASUREMENT_ID (G-XXXXXXXXXX)\n\n"
        "2. Add to Railway:\n"
        "   - Go to your Railway service\n"
        "   - Click 'Variables' tab\n"
        "   - Add each variable\n"
        "   - Redeploy\n\n"
        "3. Test Again:\n"
        "   python scripts/test_ga_tracker.py\n\n"
        "4. View Dashboard:\n"
        "   python -m src.dashboard.performance_tracker\n\n"
        "📖 Full guide: GOOGLE_ANALYTICS_SETUP_COMPLETE.md",
        title="Quick Start",
        style="blue"
    ))

if __name__ == "__main__":
    success = test_ga_setup()
    
    if not success:
        show_quick_start()
    
    console.print("\n")
