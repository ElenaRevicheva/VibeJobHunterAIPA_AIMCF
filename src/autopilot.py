#!/usr/bin/env python3
"""
AUTOPILOT MODE - Maximum automation for vibe coders
Run once, get hired. That's the vibe.
"""
import asyncio
import webbrowser
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Confirm

from .core import ProfileManager, get_settings
from .agents import JobMatcher, ContentGenerator, ApplicationManager
from .scrapers import LinkedInScraper, IndeedScraper

console = Console()


class AutopilotAgent:
    """Fully automated job hunting agent"""
    
    def __init__(self):
        self.settings = get_settings()
        self.profile_manager = ProfileManager()
        self.app_manager = ApplicationManager()
        self.content_gen = ContentGenerator()
        self.matcher = JobMatcher()
    
    async def run(self, resume_path: str, auto_apply: int = 10):
        """
        Full autopilot mode
        
        Args:
            resume_path: Path to your resume PDF
            auto_apply: Number of jobs to auto-generate materials for
        """
        console.clear()
        
        # Epic header
        console.print(Panel.fit(
            "🚀 [bold cyan]VIBE JOB HUNTER[/bold cyan] 🚀\n"
            "[yellow]AUTOPILOT MODE ACTIVATED[/yellow]\n\n"
            "[dim]Sit back, let AI do the work[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        # Step 1: Profile
        profile = await self._setup_profile(resume_path)
        
        # Step 2: Search
        jobs = await self._search_jobs()
        
        # Step 3: Generate materials
        applications = await self._generate_materials(profile, jobs, auto_apply)
        
        # Step 4: Open & apply
        await self._open_and_apply(applications)
        
        # Done!
        self._show_summary()
    
    async def _setup_profile(self, resume_path: str):
        """Step 1: Profile setup"""
        console.print("[bold]Step 1/4: Analyzing your resume[/bold]")
        
        # Check if profile exists
        existing_profile = self.profile_manager.get_profile()
        if existing_profile:
            console.print("[green]✓[/green] Profile already exists")
            return existing_profile
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🤖 AI analyzing your resume...", total=None)
            
            profile = self.profile_manager.create_profile_from_resume(resume_path)
            self.profile_manager.save_profile(profile)
            
            progress.update(task, description="[green]✓ Profile created![/green]")
        
        console.print(f"\n[cyan]Found {len(profile.skills)} skills, {profile.experience_years} years experience[/cyan]")
        console.print()
        
        return profile
    
    async def _search_jobs(self):
        """Step 2: Search and score jobs"""
        console.print("[bold]Step 2/4: Hunting for jobs[/bold]")
        
        profile = self.profile_manager.get_profile()
        all_jobs = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            # LinkedIn
            task1 = progress.add_task("🔍 Searching LinkedIn...", total=None)
            try:
                linkedin = LinkedInScraper()
                linkedin_jobs = await linkedin.search_jobs(
                    keywords=self.settings.target_roles[:3],
                    location="Remote",
                    remote_only=True,
                    limit=50
                )
                all_jobs.extend(linkedin_jobs)
                progress.update(task1, description=f"[green]✓ LinkedIn: {len(linkedin_jobs)} jobs[/green]")
            except Exception as e:
                progress.update(task1, description=f"[yellow]⚠ LinkedIn: {str(e)[:40]}[/yellow]")
            
            # Indeed
            task2 = progress.add_task("🔍 Searching Indeed...", total=None)
            try:
                indeed = IndeedScraper()
                indeed_jobs = await indeed.search_jobs(
                    keywords=self.settings.target_roles[:3],
                    location="Remote",
                    remote_only=True,
                    limit=50
                )
                all_jobs.extend(indeed_jobs)
                progress.update(task2, description=f"[green]✓ Indeed: {len(indeed_jobs)} jobs[/green]")
            except Exception as e:
                progress.update(task2, description=f"[yellow]⚠ Indeed: {str(e)[:40]}[/yellow]")
            
            # Score jobs
            task3 = progress.add_task("🤖 AI scoring matches...", total=None)
            all_jobs = await self.matcher.score_jobs(profile, all_jobs)
            all_jobs = self.matcher.filter_jobs(all_jobs, min_score=65.0)
            progress.update(task3, description=f"[green]✓ Found {len(all_jobs)} great matches![/green]")
        
        # Save jobs
        for job in all_jobs:
            self.app_manager.save_job(job)
        
        # Show top matches
        if all_jobs:
            console.print()
            table = Table(title="🎯 Top Matches", show_lines=True, title_style="bold cyan")
            table.add_column("Score", justify="center", style="green", width=8)
            table.add_column("Company", style="cyan", width=20)
            table.add_column("Title", style="yellow", width=30)
            
            for job in all_jobs[:5]:
                table.add_row(
                    f"{job.match_score:.0f}",
                    job.company[:20],
                    job.title[:30]
                )
            
            console.print(table)
        
        console.print()
        return all_jobs
    
    async def _generate_materials(self, profile, jobs, count):
        """Step 3: Generate application materials"""
        console.print(f"[bold]Step 3/4: Generating materials for top {count} jobs[/bold]")
        console.print("[dim]AI crafting custom resumes and cover letters...[/dim]\n")
        
        applications = []
        top_jobs = jobs[:count]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating...", total=len(top_jobs))
            
            for i, job in enumerate(top_jobs, 1):
                progress.update(task, description=f"✍️ {job.company} - {job.title[:30]}...")
                
                # Generate resume
                resume = self.content_gen.tailor_resume(profile, job)
                
                # Generate cover letter
                cover_letter = self.content_gen.generate_cover_letter(profile, job)
                
                # Create application
                application = self.app_manager.create_application(
                    job,
                    resume,
                    cover_letter
                )
                
                applications.append({
                    'job': job,
                    'application': application,
                    'resume_path': self.content_gen.resumes_dir / f"{job.company}_{job.title}_{job.id[:8]}.md".replace(" ", "_").replace("/", "-"),
                    'cover_letter_path': self.content_gen.cover_letters_dir / f"{job.company}_{job.title}_{job.id[:8]}_cover.txt".replace(" ", "_").replace("/", "-")
                })
                
                progress.update(task, advance=1)
        
        console.print(f"\n[green]✓ Generated {len(applications)} complete application packages![/green]")
        console.print()
        
        return applications
    
    async def _open_and_apply(self, applications):
        """Step 4: Open jobs and guide through application"""
        console.print("[bold]Step 4/4: Time to apply! (This is the fun part)[/bold]\n")
        
        console.print("[yellow]I'll open each job in your browser.[/yellow]")
        console.print("[yellow]Your resume and cover letter are ready to copy-paste.[/yellow]")
        console.print("[yellow]Just click Submit on each one![/yellow]\n")
        
        time.sleep(2)
        
        for i, app_data in enumerate(applications, 1):
            job = app_data['job']
            
            # Show job info
            console.print(Panel(
                f"[bold cyan]{i}/{len(applications)}: {job.company}[/bold cyan]\n"
                f"[yellow]{job.title}[/yellow]\n\n"
                f"[green]Match Score: {job.match_score:.0f}/100[/green]\n"
                f"Location: {job.location}\n\n"
                f"[dim]Resume: {app_data['resume_path'].name}[/dim]\n"
                f"[dim]Cover Letter: {app_data['cover_letter_path'].name}[/dim]",
                border_style="cyan"
            ))
            
            # Ask to open
            if Confirm.ask(f"Open job application?", default=True):
                console.print("[cyan]🌐 Opening in browser...[/cyan]")
                webbrowser.open(job.url)
                
                console.print(f"\n[bold green]📂 Your materials are in:[/bold green]")
                console.print(f"   Resume: {app_data['resume_path']}")
                console.print(f"   Cover Letter: {app_data['cover_letter_path']}")
                
                console.print("\n[yellow]→ Copy-paste the content and hit Submit![/yellow]\n")
                
                # Wait for user
                input("Press Enter when you've submitted (or Ctrl+C to skip remaining)...")
                
                console.print("[green]✓ Nice! On to the next one...[/green]\n")
            else:
                console.print("[dim]Skipped. You can apply later.[/dim]\n")
    
    def _show_summary(self):
        """Show final summary"""
        console.print()
        console.print(Panel.fit(
            "[bold green]🎉 AUTOPILOT COMPLETE! 🎉[/bold green]\n\n"
            "[cyan]What just happened:[/cyan]\n"
            "  ✓ AI analyzed your resume\n"
            "  ✓ Searched 100+ jobs\n"
            "  ✓ Scored every match\n"
            "  ✓ Generated custom materials\n"
            "  ✓ Opened best opportunities\n\n"
            "[yellow]Next steps:[/yellow]\n"
            "  • Check your inbox for responses\n"
            "  • Run again tomorrow for new jobs\n"
            "  • Track everything with: python -m src.main status\n\n"
            "[bold]Your next role is coming! 🚀[/bold]",
            border_style="green"
        ))
        
        # Stats
        stats = self.app_manager.get_summary_stats()
        console.print(f"\n[bold]Today's Stats:[/bold]")
        console.print(f"  Jobs found: {stats['total_jobs_discovered']}")
        console.print(f"  Applications ready: {stats['total_applications']}")
        console.print(f"  Avg match score: {stats['avg_match_score']:.0f}")
        
        console.print("\n[dim]Tip: Run 'python -m src.main autopilot' daily for best results[/dim]\n")


async def run_autopilot(resume_path: str, count: int = 10):
    """Run the autopilot agent"""
    agent = AutopilotAgent()
    await agent.run(resume_path, count)


if __name__ == "__main__":
    import sys
    resume = sys.argv[1] if len(sys.argv) > 1 else "resume.pdf"
    asyncio.run(run_autopilot(resume))
