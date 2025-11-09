#!/usr/bin/env python3
"""
BATCH APPLY MODE - Maximum automation
Paste job URLs, get complete application packages
"""
import asyncio
import webbrowser
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Confirm

from .core import ProfileManager, get_settings
from .agents import ContentGenerator, ApplicationManager, JobMatcher
from .scrapers import LinkedInScraper, IndeedScraper

console = Console()


class BatchApplyAgent:
    """Batch application processor"""
    
    def __init__(self):
        self.settings = get_settings()
        self.profile_manager = ProfileManager()
        self.app_manager = ApplicationManager()
        self.content_gen = ContentGenerator()
        self.matcher = JobMatcher()
    
    async def process_url(self, url: str):
        """Process a single job URL"""
        # Determine source
        if "linkedin.com" in url:
            scraper = LinkedInScraper()
        elif "indeed.com" in url:
            scraper = IndeedScraper()
        else:
            return None
        
        # Get job details
        job = await scraper.get_job_details(url)
        return job
    
    async def run(self, urls: List[str]):
        """
        Batch apply to multiple jobs
        
        Args:
            urls: List of job URLs
        """
        console.clear()
        
        console.print(Panel.fit(
            "🚀 [bold cyan]BATCH APPLY MODE[/bold cyan] 🚀\n"
            "[yellow]MAXIMUM AUTOMATION[/yellow]\n\n"
            f"[dim]Processing {len(urls)} jobs...[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        # Get profile
        profile = self.profile_manager.get_profile()
        if not profile:
            console.print("[red]❌ No profile found. Run setup first.[/red]")
            return
        
        # Process all URLs
        jobs = await self._fetch_jobs(urls)
        
        # Score jobs
        jobs = await self._score_jobs(profile, jobs)
        
        # Generate materials
        applications = await self._generate_materials(profile, jobs)
        
        # Open and apply
        await self._open_and_apply(applications)
        
        # Summary
        self._show_summary()
    
    async def _fetch_jobs(self, urls: List[str]):
        """Fetch job details from URLs"""
        console.print("[bold]Step 1/4: Fetching job details[/bold]\n")
        
        jobs = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Fetching jobs...", total=len(urls))
            
            for url in urls:
                try:
                    job = await self.process_url(url)
                    if job:
                        jobs.append(job)
                        progress.update(task, description=f"✅ Fetched: {job.company}", advance=1)
                    else:
                        progress.update(task, description=f"⚠️ Skipped: Invalid URL", advance=1)
                except Exception as e:
                    progress.update(task, description=f"⚠️ Error: {str(e)[:30]}", advance=1)
        
        console.print(f"\n[green]✓ Fetched {len(jobs)} jobs successfully![/green]\n")
        return jobs
    
    async def _score_jobs(self, profile, jobs):
        """Score jobs with AI"""
        console.print("[bold]Step 2/4: AI scoring jobs[/bold]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🤖 AI analyzing matches...", total=None)
            jobs = await self.matcher.score_jobs(profile, jobs)
            progress.update(task, description="[green]✓ All jobs scored![/green]")
        
        # Save jobs
        for job in jobs:
            self.app_manager.save_job(job)
        
        # Show scores
        table = Table(title="🎯 Job Scores", show_lines=True)
        table.add_column("Score", justify="center", style="green", width=8)
        table.add_column("Company", style="cyan", width=20)
        table.add_column("Title", style="yellow", width=30)
        
        for job in sorted(jobs, key=lambda j: j.match_score, reverse=True):
            table.add_row(
                f"{job.match_score:.0f}",
                job.company[:20],
                job.title[:30]
            )
        
        console.print(table)
        console.print()
        
        return jobs
    
    async def _generate_materials(self, profile, jobs):
        """Generate application materials"""
        console.print(f"[bold]Step 3/4: Generating materials for {len(jobs)} jobs[/bold]\n")
        
        applications = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating...", total=len(jobs))
            
            for job in jobs:
                progress.update(task, description=f"✍️ {job.company} - {job.title[:25]}...")
                
                # Generate resume
                resume = self.content_gen.tailor_resume(profile, job)
                
                # Generate cover letter
                cover_letter = self.content_gen.generate_cover_letter(profile, job)
                
                # Create application
                application = self.app_manager.create_application(job, resume, cover_letter)
                
                applications.append({
                    'job': job,
                    'application': application,
                    'resume_path': self.content_gen.resumes_dir / f"{job.company}_{job.id[:8]}.md".replace(" ", "_"),
                    'cover_letter_path': self.content_gen.cover_letters_dir / f"{job.company}_{job.id[:8]}_cover.txt".replace(" ", "_")
                })
                
                progress.update(task, advance=1)
        
        console.print(f"\n[green]✓ Generated {len(applications)} application packages![/green]\n")
        return applications
    
    async def _open_and_apply(self, applications):
        """Open jobs and guide application"""
        console.print("[bold]Step 4/4: Opening jobs in browser[/bold]\n")
        
        console.print("[yellow]Opening all job tabs in your browser...[/yellow]")
        console.print("[yellow]Your materials are ready to copy-paste![/yellow]\n")
        
        # Open all tabs at once
        for app_data in applications:
            job = app_data['job']
            webbrowser.open_new_tab(job.url)
        
        console.print(f"[green]✓ Opened {len(applications)} job tabs![/green]\n")
        
        # Show materials locations
        table = Table(title="📂 Your Application Materials", show_lines=True)
        table.add_column("#", justify="center", width=4)
        table.add_column("Company", style="cyan", width=20)
        table.add_column("Title", style="yellow", width=30)
        table.add_column("Score", justify="center", style="green", width=8)
        
        for i, app_data in enumerate(applications, 1):
            job = app_data['job']
            table.add_row(
                str(i),
                job.company[:20],
                job.title[:30],
                f"{job.match_score:.0f}"
            )
        
        console.print(table)
        
        console.print(f"\n[bold]📁 All files saved to:[/bold]")
        console.print(f"   Resumes: {self.content_gen.resumes_dir}")
        console.print(f"   Cover Letters: {self.content_gen.cover_letters_dir}")
        
        console.print("\n[yellow]→ Go through each browser tab and submit![/yellow]")
        console.print("[dim]Tip: Copy resume content from the .md files[/dim]\n")
        
        input("Press Enter when done applying...")
    
    def _show_summary(self):
        """Show final summary"""
        console.print(Panel.fit(
            "[bold green]🎉 BATCH APPLY COMPLETE! 🎉[/bold green]\n\n"
            "[cyan]What just happened:[/cyan]\n"
            "  ✓ Fetched all job details\n"
            "  ✓ AI scored every job\n"
            "  ✓ Generated custom materials\n"
            "  ✓ Opened all applications\n\n"
            "[yellow]Next steps:[/yellow]\n"
            "  • Complete the applications\n"
            "  • Check: python -m src.main status\n"
            "  • Tomorrow: Add more URLs and repeat!\n\n"
            "[bold]Keep applying daily! 🚀[/bold]",
            border_style="green"
        ))


async def run_batch_apply(urls: List[str]):
    """Run batch apply"""
    agent = BatchApplyAgent()
    await agent.run(urls)


if __name__ == "__main__":
    import sys
    urls = sys.argv[1:]
    if urls:
        asyncio.run(run_batch_apply(urls))
    else:
        print("Usage: python -m src.batch_apply <url1> <url2> ...")
