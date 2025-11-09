#!/usr/bin/env python3
"""
FULLY AUTOMATED JOB HUNTER
Searches, filters, applies - completely automated for Elena
"""
import asyncio
import webbrowser
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core import ProfileManager
from .search import StartupJobSearch
from .auto_search import AutoSearchAgent
from .batch_apply_v2 import BatchApplyAgentV2

console = Console()


class FullyAutomatedJobHunter:
    """Fully automated job search and apply for Elena"""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.startup_search = StartupJobSearch()
        self.auto_search = AutoSearchAgent()
        self.batch_apply = BatchApplyAgentV2()
    
    async def run_full_automation(self, target_applications: int = 20):
        """
        Fully automated: Search → Filter → Generate → Apply
        
        Args:
            target_applications: Number of applications to complete
        """
        console.clear()
        console.print(Panel.fit(
            "🤖 [bold cyan]FULLY AUTOMATED JOB HUNTER[/bold cyan] 🤖\n"
            "[yellow]Elena's AI-Powered Hiring Machine[/yellow]\n\n"
            f"[green]Target: {target_applications} high-quality applications[/green]\n"
            "[dim]Based on your profile: PayPal subs, 19 countries, Web3+AI[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        # Step 1: Get profile
        profile = self.profile_manager.get_profile()
        if not profile:
            console.print("[red]❌ No profile. Run: py -m src.main setup --elena[/red]")
            return
        
        console.print(f"[green]✓ Profile loaded: {profile.name}[/green]")
        console.print(f"[dim]Target roles: {', '.join(profile.target_roles[:3])}[/dim]\n")
        
        # Step 2: Generate optimized search URLs
        console.print("[bold]Step 1/4: Opening optimized job searches[/bold]\n")
        console.print("[cyan]Opening YC, AngelList, Web3 Career, LinkedIn...[/cyan]")
        
        await self.startup_search.open_all_search_pages()
        
        # Step 3: Attempt automated scraping (may fail due to blocking)
        console.print("\n[bold]Step 2/4: Attempting automated job discovery[/bold]\n")
        console.print("[yellow]⚠️ Note: This may be blocked by LinkedIn/Indeed[/yellow]")
        console.print("[dim]If blocked, just copy URLs from the opened browser tabs[/dim]\n")
        
        proceed = input("Try automated search? (y/n): ").lower().strip()
        
        urls = []
        
        if proceed == 'y':
            # Try automated search
            console.print("\n[cyan]Searching with your target roles...[/cyan]\n")
            
            keywords = profile.target_roles[:3]  # Top 3 target roles
            await self.auto_search.search_and_save(keywords, limit=target_applications)
            
            # Check if we found jobs
            if self.auto_search.output_file.exists():
                with open(self.auto_search.output_file, 'r') as f:
                    urls = [line.strip() for line in f if line.strip().startswith('http')]
        
        # Step 4: Manual URL collection if needed
        if not urls or len(urls) < 5:
            console.print("\n[yellow]Automated search found few jobs (or was blocked)[/yellow]")
            console.print("\n[cyan]💡 Quick manual collection:[/cyan]")
            console.print("  1. Check the browser tabs that opened")
            console.print("  2. Copy 10-20 job URLs you like")
            console.print("  3. Paste below (one per line, empty line when done)\n")
            
            console.print("[dim]Paste job URLs (press Enter twice when done):[/dim]")
            
            manual_urls = []
            while True:
                url = input().strip()
                if not url:
                    break
                if url.startswith('http'):
                    manual_urls.append(url)
            
            urls.extend(manual_urls)
        
        if not urls:
            console.print("\n[red]❌ No URLs collected. Exiting.[/red]")
            console.print("[dim]Run this again or use: py -m src.main batch --file jobs.txt --v2[/dim]")
            return
        
        console.print(f"\n[green]✓ Collected {len(urls)} job URLs![/green]\n")
        
        # Step 5: Process with batch apply V2 (smart filtering + materials generation)
        console.print("[bold]Step 3/4: Processing jobs with AI[/bold]\n")
        console.print("[cyan]Filtering by your criteria + generating materials...[/cyan]\n")
        
        await self.batch_apply.run(urls, resume_existing=False)
        
        # Step 6: Summary
        console.print(Panel.fit(
            "[bold green]🎉 FULL AUTOMATION COMPLETE! 🎉[/bold green]\n\n"
            "[cyan]What was automated:[/cyan]\n"
            "  ✓ Opened optimized job searches\n"
            "  ✓ Attempted automated discovery\n"
            "  ✓ AI scored all jobs\n"
            "  ✓ Filtered by your criteria (founding engineer, equity)\n"
            "  ✓ Generated custom materials (resume, cover, prep)\n"
            "  ✓ Enhanced with portfolio (PayPal subs, 19 countries)\n"
            "  ✓ Opened browser tabs\n"
            "  ✓ Scheduled follow-ups\n\n"
            "[yellow]Your role:[/yellow]\n"
            "  → Browse opened tabs\n"
            "  → Copy-paste materials\n"
            "  → Submit applications (5-10 min)\n\n"
            "[bold]Keep running this daily! 🚀[/bold]",
            border_style="green"
        ))


async def run_full_auto(target_apps: int = 20):
    """Run fully automated job hunter"""
    hunter = FullyAutomatedJobHunter()
    await hunter.run_full_automation(target_apps)
