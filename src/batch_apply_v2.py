#!/usr/bin/env python3
"""
IMPROVED BATCH APPLY MODE with:
- Parallel processing
- Progress saving/resume
- Better error handling
- Caching
- Cost tracking
"""
import asyncio
import webbrowser
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from datetime import datetime
import uuid

from .core import ProfileManager, get_settings
from .agents import ApplicationManager, JobMatcher
from .agents.content_generator_v2 import ContentGeneratorV2
from .scrapers import LinkedInScraper, IndeedScraper
from .utils import retry_async, get_logger
from .utils.progress_saver import BatchProgressTracker
from .filters import CriteriaMatcher, RedFlagDetector
from .templates import ResumeFormatter, CoverLetterFormatter
from .enhancers import PortfolioIntegrator, InterviewPrepGenerator, FollowUpScheduler

console = Console()


class BatchApplyAgentV2:
    """Enhanced batch application processor"""
    
    def __init__(self):
        self.settings = get_settings()
        self.profile_manager = ProfileManager()
        self.app_manager = ApplicationManager()
        self.content_gen = ContentGeneratorV2()
        self.matcher = JobMatcher()
        self.logger = get_logger(__name__, self.settings.base_dir / "logs")
        self.progress = BatchProgressTracker(self.settings.base_dir / "data")
        self.session_id = str(uuid.uuid4())[:8]
        
        # NEW: Smart matching and templates
        self.criteria_matcher = CriteriaMatcher()
        self.red_flag_detector = RedFlagDetector()
        self.resume_formatter = ResumeFormatter()
        self.cover_formatter = CoverLetterFormatter()
        
        # NEW: Portfolio, interview prep, and follow-ups
        self.portfolio = PortfolioIntegrator()
        self.interview_prep = InterviewPrepGenerator()
        self.follow_up_scheduler = FollowUpScheduler()
    
    @retry_async(max_attempts=2, delay=1.0)
    async def process_url(self, url: str):
        """Process a single job URL with retry"""
        if "linkedin.com" in url:
            scraper = LinkedInScraper()
        elif "indeed.com" in url:
            scraper = IndeedScraper()
        else:
            return None
        
        job = await scraper.get_job_details(url)
        return job
    
    async def run(self, urls: List[str], resume_existing: bool = False):
        """
        Run batch apply with improvements
        
        Args:
            urls: List of job URLs
            resume_existing: Resume from saved progress
        """
        console.clear()
        
        # Check for existing progress
        if resume_existing and self.progress.can_resume():
            remaining = self.progress.get_remaining_urls()
            if remaining:
                console.print(f"[yellow]Resuming previous session with {len(remaining)} remaining jobs[/yellow]\n")
                urls = remaining
        else:
            self.progress.start_batch(urls, self.session_id)
        
        console.print(Panel.fit(
            "🚀 [bold cyan]BATCH APPLY V2 - IMPROVED[/bold cyan] 🚀\n"
            "[yellow]With caching, retry, and progress saving[/yellow]\n\n"
            f"[dim]Processing {len(urls)} jobs...[/dim]",
            border_style="cyan"
        ))
        console.print()
        
        # Get profile
        profile = self.profile_manager.get_profile()
        if not profile:
            console.print("[red]❌ No profile found. Run setup first.[/red]")
            return
        
        try:
            # Process all URLs (with parallel fetching)
            jobs = await self._fetch_jobs_parallel(urls)
            
            if not jobs:
                console.print("[red]❌ No jobs fetched successfully[/red]")
                return
            
            # Score jobs
            jobs = await self._score_jobs(profile, jobs)
            
            # Generate materials (parallel)
            applications = await self._generate_materials_parallel(profile, jobs)
            
            # Mark batch complete
            self.progress.finish_batch()
            
            # Open and apply
            await self._open_and_apply(applications)
            
            # Summary with stats
            self._show_summary()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Interrupted! Progress saved. Run again to resume.[/yellow]")
            self.logger.info("Batch interrupted by user")
        except Exception as e:
            console.print(f"\n[red]❌ Error: {e}[/red]")
            self.logger.error(f"Batch apply error: {e}", exc_info=True)
    
    async def _fetch_jobs_parallel(self, urls: List[str]):
        """Fetch jobs in parallel for speed"""
        console.print("[bold]Step 1/4: Fetching job details (parallel)[/bold]\n")
        
        jobs = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Fetching jobs...", total=len(urls))
            
            # Process in batches of 5 to avoid overwhelming
            batch_size = 5
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i+batch_size]
                tasks = [self.process_url(url) for url in batch_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for url, result in zip(batch_urls, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Failed to fetch {url}: {result}")
                        self.progress.mark_failed(url, str(result))
                        progress.update(task, description=f"⚠️ Error: {str(result)[:30]}", advance=1)
                    elif result:
                        jobs.append(result)
                        self.progress.mark_completed(url)
                        progress.update(task, description=f"✅ Fetched: {result.company}", advance=1)
                    else:
                        self.progress.mark_failed(url, "Invalid URL")
                        progress.update(task, description=f"⚠️ Skipped: Invalid URL", advance=1)
                
                # Small delay between batches
                if i + batch_size < len(urls):
                    await asyncio.sleep(1)
        
        console.print(f"\n[green]✓ Fetched {len(jobs)} jobs successfully![/green]\n")
        self.logger.info(f"Fetched {len(jobs)}/{len(urls)} jobs")
        return jobs
    
    async def _score_jobs(self, profile, jobs):
        """Score jobs with AI + smart filtering"""
        console.print("[bold]Step 2/4: AI scoring + smart filtering[/bold]\n")
        console.print("[dim]Using target criteria and red flag detection[/dim]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # AI scoring
            task = progress.add_task("🤖 AI analyzing matches...", total=None)
            jobs = await self.matcher.score_jobs(profile, jobs)
            progress.update(task, description="[green]✓ All jobs scored![/green]")
        
        # Smart filtering
        console.print("\n[cyan]Applying target criteria and red flag detection...[/cyan]")
        
        filtered_jobs = []
        for job in jobs:
            # Check red flags
            has_flags, flags = self.red_flag_detector.scan_job(job)
            job.red_flags = flags
            
            # Check criteria match
            should_apply, criteria_score, reasons = self.criteria_matcher.evaluate_job(job)
            
            # Combine scores (AI + criteria)
            job.match_score = (job.match_score + criteria_score) / 2
            job.match_reasons = reasons + job.match_reasons
            
            # Only keep good matches without red flags
            if should_apply and not has_flags:
                filtered_jobs.append(job)
            elif has_flags:
                self.logger.info(f"Filtered out {job.company} due to red flags: {flags}")
        
        console.print(f"[green]✓ Filtered to {len(filtered_jobs)}/{len(jobs)} high-quality matches[/green]\n")
        
        # Save filtered jobs
        for job in filtered_jobs:
            self.app_manager.save_job(job)
        
        # Show scores
        self._display_scores(filtered_jobs)
        
        return filtered_jobs
    
    async def _generate_materials_parallel(self, profile, jobs):
        """Generate materials with parallel execution"""
        console.print(f"[bold]Step 3/4: Generating materials for {len(jobs)} jobs[/bold]\n")
        console.print("[dim]Using cache when possible to save time and money[/dim]\n")
        
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
                
                try:
                    # Use professional templates for better quality
                    resume = self.resume_formatter.format_resume(profile, job)
                    cover_letter = self.cover_formatter.format_cover_letter(profile, job)
                    
                    # Enhance with portfolio demos and links
                    resume = self.portfolio.enhance_resume_with_portfolio(resume, job)
                    cover_letter = self.portfolio.enhance_cover_letter_with_demo(cover_letter)
                    
                    # Generate interview prep package
                    prep_file = self.interview_prep.generate_prep_package(profile, job)
                    
                    application = self.app_manager.create_application(job, resume, cover_letter)
                    
                    applications.append({
                        'job': job,
                        'application': application,
                        'resume_path': self.content_gen.resumes_dir / f"{job.company}_{job.id[:8]}.md".replace(" ", "_"),
                        'cover_letter_path': self.content_gen.cover_letters_dir / f"{job.company}_{job.id[:8]}_cover.txt".replace(" ", "_"),
                        'prep_file': prep_file
                    })
                    
                    # Schedule follow-up for 3 days
                    self.follow_up_scheduler.schedule_follow_up(application, days=3)
                except Exception as e:
                    self.logger.error(f"Failed to generate materials for {job.company}: {e}")
                    progress.update(task, description=f"⚠️ Error: {job.company}", advance=1)
                    continue
                
                progress.update(task, advance=1)
        
        console.print(f"\n[green]✓ Generated {len(applications)} application packages![/green]")
        
        # Show cost stats
        stats = self.content_gen.get_usage_stats()
        console.print(f"[dim]API Usage: {stats['total_calls']} calls, "
                     f"${stats['estimated_cost_usd']:.4f} estimated cost[/dim]\n")
        
        return applications
    
    async def _open_and_apply(self, applications):
        """Open jobs and guide application"""
        console.print("[bold]Step 4/4: Opening jobs in browser[/bold]\n")
        
        console.print("[yellow]Opening all job tabs in your browser...[/yellow]")
        console.print("[yellow]Your materials are ready to copy-paste![/yellow]\n")
        
        # Open all tabs
        for app_data in applications:
            job = app_data['job']
            try:
                webbrowser.open_new_tab(job.url)
            except Exception as e:
                self.logger.warning(f"Could not open browser for {job.company}: {e}")
        
        console.print(f"[green]✓ Opened {len(applications)} job tabs![/green]\n")
        
        # Show materials table
        self._display_materials_table(applications)
        
        console.print(f"\n[bold]📁 All files saved to:[/bold]")
        console.print(f"   Resumes: {self.content_gen.resumes_dir}")
        console.print(f"   Cover Letters: {self.content_gen.cover_letters_dir}")
        console.print(f"   Interview Prep: interview_prep/")
        console.print(f"   Logs: {self.settings.base_dir / 'logs'}")
        
        console.print("\n[yellow]→ Go through each browser tab and submit![/yellow]")
        console.print("[dim]Tip: Keep this window open to reference file paths[/dim]\n")
        
        input("Press Enter when done applying...")
    
    def _display_scores(self, jobs):
        """Display job scores in a table"""
        table = Table(title="🎯 Job Scores", show_lines=True)
        table.add_column("Score", justify="center", style="green", width=8)
        table.add_column("Company", style="cyan", width=20)
        table.add_column("Title", style="yellow", width=35)
        table.add_column("Location", style="dim", width=15)
        
        for job in sorted(jobs, key=lambda j: j.match_score, reverse=True):
            score_style = "green" if job.match_score >= 80 else "yellow" if job.match_score >= 60 else "red"
            table.add_row(
                f"[{score_style}]{job.match_score:.0f}[/{score_style}]",
                job.company[:20],
                job.title[:35],
                job.location[:15]
            )
        
        console.print(table)
        console.print()
    
    def _display_materials_table(self, applications):
        """Display materials table"""
        table = Table(title="📂 Your Application Materials", show_lines=True)
        table.add_column("#", justify="center", width=4)
        table.add_column("Company", style="cyan", width=20)
        table.add_column("Title", style="yellow", width=30)
        table.add_column("Score", justify="center", style="green", width=8)
        table.add_column("Remote", justify="center", width=8)
        
        for i, app_data in enumerate(applications, 1):
            job = app_data['job']
            remote_indicator = "✓" if job.remote_allowed else "✗"
            table.add_row(
                str(i),
                job.company[:20],
                job.title[:30],
                f"{job.match_score:.0f}",
                remote_indicator
            )
        
        console.print(table)
    
    def _show_summary(self):
        """Show final summary with statistics"""
        stats = self.content_gen.get_usage_stats()
        
        console.print(Panel.fit(
            f"[bold green]🎉 BATCH APPLY COMPLETE! 🎉[/bold green]\n\n"
            f"[cyan]Session Statistics:[/cyan]\n"
            f"  ✓ Jobs processed successfully\n"
            f"  ✓ AI scoring completed\n"
            f"  ✓ Custom materials generated\n"
            f"  ✓ Applications opened in browser\n\n"
            f"[yellow]API Usage:[/yellow]\n"
            f"  • Total API calls: {stats['total_calls']}\n"
            f"  • Total tokens: {stats['total_tokens']:,}\n"
            f"  • Estimated cost: ${stats['estimated_cost_usd']:.4f}\n\n"
            f"[yellow]Next steps:[/yellow]\n"
            f"  • Complete the applications\n"
            f"  • Check status: python -m src.main status\n"
            f"  • Tomorrow: Find more jobs and repeat!\n\n"
            f"[bold]Keep applying daily! 🚀[/bold]",
            border_style="green"
        ))
        
        self.logger.info(f"Batch apply session {self.session_id} completed successfully")


async def run_batch_apply_v2(urls: List[str], resume: bool = False):
    """Run improved batch apply"""
    agent = BatchApplyAgentV2()
    await agent.run(urls, resume_existing=resume)


if __name__ == "__main__":
    import sys
    urls = sys.argv[1:]
    if urls:
        asyncio.run(run_batch_apply_v2(urls))
    else:
        print("Usage: python -m src.batch_apply_v2 <url1> <url2> ...")
