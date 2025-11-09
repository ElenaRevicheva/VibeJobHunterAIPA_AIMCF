#!/usr/bin/env python3
"""
AUTO SEARCH MODE - Attempts to automatically find jobs
WARNING: May be blocked by LinkedIn/Indeed
"""
import asyncio
import webbrowser
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core import ProfileManager, get_settings
from .scrapers import LinkedInScraper, IndeedScraper

console = Console()


class AutoSearchAgent:
    """Attempt to automatically find job URLs"""
    
    def __init__(self):
        self.settings = get_settings()
        self.profile_manager = ProfileManager()
        self.linkedin = LinkedInScraper()
        self.indeed = IndeedScraper()
        self.output_file = Path.cwd() / "auto_found_jobs.txt"
    
    async def search_and_save(self, keywords: List[str], limit: int = 20):
        """
        Try to automatically search for jobs and save URLs
        
        Args:
            keywords: List of search keywords
            limit: Maximum jobs to find
        """
        console.clear()
        console.print(Panel.fit(
            "🤖 [bold cyan]AUTO SEARCH MODE[/bold cyan] 🤖\n"
            "[yellow]Attempting automated job search[/yellow]\n\n"
            "[red]⚠️ Warning: May be blocked by LinkedIn/Indeed[/red]\n"
            "[dim]This is experimental - manual search is more reliable[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        # Get profile
        profile = self.profile_manager.get_profile()
        if not profile:
            console.print("[red]❌ No profile found. Run setup first.[/red]")
            return
        
        # Use profile's target roles if no keywords provided
        if not keywords:
            keywords = profile.target_roles[:3]  # Top 3 target roles
            console.print(f"[cyan]Using your target roles: {', '.join(keywords)}[/cyan]\n")
        
        all_urls = []
        
        # Try LinkedIn
        console.print("[bold]Step 1: Searching LinkedIn...[/bold]")
        linkedin_urls = await self._search_linkedin(keywords, limit // 2)
        all_urls.extend(linkedin_urls)
        
        # Try Indeed
        console.print("\n[bold]Step 2: Searching Indeed...[/bold]")
        indeed_urls = await self._search_indeed(keywords, limit // 2)
        all_urls.extend(indeed_urls)
        
        # Save results
        if all_urls:
            self._save_urls(all_urls)
            console.print(f"\n[green]✓ Found {len(all_urls)} jobs![/green]")
            console.print(f"[green]✓ Saved to: {self.output_file}[/green]\n")
            
            # Show what was found
            self._show_results(all_urls)
            
            # Ask if they want to proceed
            console.print("\n[yellow]Ready to process these jobs?[/yellow]")
            console.print("[dim]You can edit auto_found_jobs.txt to remove any jobs you don't want[/dim]\n")
            
            proceed = input("Continue with batch apply? (y/n): ").lower().strip()
            
            if proceed == 'y':
                console.print("\n[cyan]Starting batch apply...[/cyan]\n")
                from .batch_apply_v2 import BatchApplyAgentV2
                agent = BatchApplyAgentV2()
                await agent.run(all_urls, resume_existing=False)
            else:
                console.print(f"\n[yellow]No problem! Edit {self.output_file} and run:[/yellow]")
                console.print(f"[cyan]py -m src.main batch --file {self.output_file} --v2[/cyan]\n")
        else:
            console.print("\n[red]❌ No jobs found (likely blocked by scrapers)[/red]")
            console.print("\n[yellow]💡 Recommendation: Use manual search instead[/yellow]")
            console.print("[dim]1. Go to LinkedIn: https://www.linkedin.com/jobs/[/dim]")
            console.print("[dim]2. Search for your roles[/dim]")
            console.print("[dim]3. Copy 10-20 URLs to jobs.txt[/dim]")
            console.print("[dim]4. Run: py -m src.main batch --file jobs.txt --v2[/dim]\n")
    
    async def _search_linkedin(self, keywords: List[str], limit: int) -> List[str]:
        """Try to search LinkedIn"""
        urls = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching LinkedIn...", total=None)
            
            try:
                for keyword in keywords:
                    # Build search URL
                    search_query = f"{keyword} remote"
                    search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query.replace(' ', '%20')}&location=Remote"
                    
                    progress.update(task, description=f"Searching: {keyword}...")
                    
                    # Try to fetch jobs
                    try:
                        jobs = await self.linkedin.search_jobs(
                            keywords=[keyword],
                            location="Remote",
                            limit=limit // len(keywords)
                        )
                        
                        for job in jobs:
                            if job.url and job.url not in urls:
                                urls.append(job.url)
                        
                        progress.update(task, description=f"✓ Found {len(jobs)} from {keyword}")
                    except Exception as e:
                        progress.update(task, description=f"⚠️ {keyword}: {str(e)[:30]}")
                        # If blocked, open search URL in browser for manual copy
                        console.print(f"[yellow]→ Opening search in browser for manual review[/yellow]")
                        webbrowser.open(search_url)
                        await asyncio.sleep(1)
            
            except Exception as e:
                progress.update(task, description=f"⚠️ LinkedIn search failed: {str(e)[:30]}")
        
        console.print(f"[dim]LinkedIn: Found {len(urls)} URLs[/dim]")
        return urls
    
    async def _search_indeed(self, keywords: List[str], limit: int) -> List[str]:
        """Try to search Indeed"""
        urls = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching Indeed...", total=None)
            
            try:
                for keyword in keywords:
                    search_query = f"{keyword} remote"
                    search_url = f"https://www.indeed.com/jobs?q={search_query.replace(' ', '+')}&l=Remote"
                    
                    progress.update(task, description=f"Searching: {keyword}...")
                    
                    try:
                        jobs = await self.indeed.search_jobs(
                            keywords=[keyword],
                            location="Remote",
                            limit=limit // len(keywords)
                        )
                        
                        for job in jobs:
                            if job.url and job.url not in urls:
                                urls.append(job.url)
                        
                        progress.update(task, description=f"✓ Found {len(jobs)} from {keyword}")
                    except Exception as e:
                        progress.update(task, description=f"⚠️ {keyword}: {str(e)[:30]}")
                        console.print(f"[yellow]→ Opening search in browser for manual review[/yellow]")
                        webbrowser.open(search_url)
                        await asyncio.sleep(1)
            
            except Exception as e:
                progress.update(task, description=f"⚠️ Indeed search failed: {str(e)[:30]}")
        
        console.print(f"[dim]Indeed: Found {len(urls)} URLs[/dim]")
        return urls
    
    def _save_urls(self, urls: List[str]):
        """Save URLs to file"""
        with open(self.output_file, 'w') as f:
            f.write("# Auto-found job URLs\n")
            f.write("# Edit this file to remove jobs you don't want\n")
            f.write("# Then run: py -m src.main batch --file auto_found_jobs.txt --v2\n\n")
            for url in urls:
                f.write(f"{url}\n")
    
    def _show_results(self, urls: List[str]):
        """Show found URLs"""
        console.print(f"\n[bold]Found {len(urls)} jobs:[/bold]")
        for i, url in enumerate(urls[:10], 1):
            console.print(f"  {i}. {url[:70]}...")
        
        if len(urls) > 10:
            console.print(f"  ... and {len(urls) - 10} more")


async def run_auto_search(keywords: List[str] = None, limit: int = 20):
    """Run automated job search"""
    agent = AutoSearchAgent()
    await agent.search_and_save(keywords or [], limit)
