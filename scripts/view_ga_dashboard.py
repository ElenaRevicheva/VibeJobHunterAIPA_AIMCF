#!/usr/bin/env python3
"""
View Google Analytics 4 Performance Dashboard
Shows website metrics in a beautiful terminal UI
"""
import sys
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.performance_tracker import GA4PerformanceTracker
from rich.console import Console

console = Console()

def main():
    parser = argparse.ArgumentParser(
        description='View Google Analytics 4 Performance Dashboard'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export report to markdown file'
    )
    
    args = parser.parse_args()
    
    # Initialize tracker
    tracker = GA4PerformanceTracker()
    
    if args.export:
        # Export report
        console.print("[cyan]Generating report...[/cyan]")
        report_file = tracker.export_report(days=args.days)
        console.print(f"[green]✅ Report exported to: {report_file}[/green]")
    else:
        # Show dashboard
        tracker.show_dashboard(days=args.days)
        
        console.print("\n[dim]Press Ctrl+C to exit | Refresh: python scripts/view_ga_dashboard.py[/dim]\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed.[/yellow]")
        sys.exit(0)
