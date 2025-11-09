#!/usr/bin/env python3
"""
VibeJobHunter - Main Application
AI-powered job hunting automation
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from .core import ProfileManager, get_settings, ApplicationStatus
from .agents import JobMatcher, ContentGenerator, ApplicationManager
from .scrapers import LinkedInScraper, IndeedScraper

console = Console()


@click.group()
def cli():
    """VibeJobHunter - AI-powered job hunting agent"""
    pass


@cli.command()
@click.option('--resume', '-r', type=click.Path(exists=True), help='Path to resume PDF')
@click.option('--elena', is_flag=True, help='Use pre-configured Elena profile (instant!)')
@click.option('--name', '-n', help='Your full name')
@click.option('--email', '-e', help='Your email address')
@click.option('--location', '-l', help='Your location')
def setup(resume, elena, name, email, location):
    """Set up your profile"""
    console.print(Panel.fit("🚀 [bold blue]VibeJobHunter Setup[/bold blue]", border_style="blue"))
    
    profile_manager = ProfileManager()
    
    # NEW: Instant setup with Elena profile
    if elena:
        from .loaders import CandidateDataLoader
        loader = CandidateDataLoader()
        profile = loader.load_profile()
        
        if profile:
            profile_manager.save_profile(profile)
            console.print("\n[green]✓[/green] Profile loaded instantly from candidate data!")
            console.print(f"\n[bold]Name:[/bold] {profile.name}")
            console.print(f"[bold]Email:[/bold] {profile.email}")
            console.print(f"[bold]Location:[/bold] {profile.location}")
            console.print(f"[bold]Skills:[/bold] {len(profile.skills)} skills detected")
            console.print(f"[bold]Experience:[/bold] {profile.experience_years} years")
            console.print(f"\n[bold cyan]🚀 Ready to hunt! Run: python -m src.main batch --v2 <urls>[/bold cyan]")
            return
        else:
            console.print("[red]❌ Could not load Elena profile. Using resume instead.[/red]\n")
    
    # Original resume parsing flow
    if not resume:
        console.print("[red]❌ Either --elena or --resume is required![/red]")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Parsing your resume with AI...", total=None)
        
        additional_info = {}
        if name:
            additional_info['name'] = name
        if email:
            additional_info['email'] = email
        if location:
            additional_info['location'] = location
        
        profile = profile_manager.create_profile_from_resume(resume, additional_info)
        profile_manager.save_profile(profile)
        
        progress.update(task, description="✅ Profile created!")
    
    console.print("\n[green]✓[/green] Profile setup complete!")
    console.print(f"\n[bold]Name:[/bold] {profile.name}")
    console.print(f"[bold]Email:[/bold] {profile.email}")
    console.print(f"[bold]Location:[/bold] {profile.location}")
    console.print(f"[bold]Skills:[/bold] {len(profile.skills)} skills detected")
    console.print(f"[bold]Experience:[/bold] {profile.experience_years} years")
    console.print(f"\n[bold]Top Skills:[/bold] {', '.join(profile.skills[:10])}")


@cli.command()
@click.option('--keywords', '-k', multiple=True, help='Job search keywords')
@click.option('--location', '-l', help='Job location')
@click.option('--remote', is_flag=True, help='Remote jobs only')
@click.option('--limit', default=50, help='Maximum jobs to fetch')
@click.option('--min-score', default=60.0, help='Minimum match score')
def search(keywords, location, remote, limit, min_score):
    """Search for matching jobs"""
    console.print(Panel.fit("🔍 [bold blue]Searching for Jobs[/bold blue]", border_style="blue"))
    
    # Load profile
    profile_manager = ProfileManager()
    profile = profile_manager.get_profile()
    
    if not profile:
        console.print("[red]❌ No profile found. Run 'setup' first.[/red]")
        return
    
    settings = get_settings()
    
    # Use settings defaults if not provided
    if not keywords:
        keywords = settings.target_roles[:3]
    if not location:
        location = "Remote"
    
    console.print(f"\n[bold]Searching for:[/bold] {', '.join(keywords)}")
    console.print(f"[bold]Location:[/bold] {location}")
    console.print(f"[bold]Remote only:[/bold] {remote}\n")
    
    # Search jobs
    jobs = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # LinkedIn
        task = progress.add_task("Searching LinkedIn...", total=None)
        try:
            linkedin = LinkedInScraper()
            linkedin_jobs = asyncio.run(linkedin.search_jobs(list(keywords), location, remote, limit))
            jobs.extend(linkedin_jobs)
            progress.update(task, description=f"✅ LinkedIn: {len(linkedin_jobs)} jobs found")
        except Exception as e:
            progress.update(task, description=f"⚠️ LinkedIn: {str(e)[:50]}")
        
        # Indeed
        task2 = progress.add_task("Searching Indeed...", total=None)
        try:
            indeed = IndeedScraper()
            indeed_jobs = asyncio.run(indeed.search_jobs(list(keywords), location, remote, limit))
            jobs.extend(indeed_jobs)
            progress.update(task2, description=f"✅ Indeed: {len(indeed_jobs)} jobs found")
        except Exception as e:
            progress.update(task2, description=f"⚠️ Indeed: {str(e)[:50]}")
        
        # Match and score jobs
        task3 = progress.add_task("Analyzing job matches...", total=None)
        matcher = JobMatcher()
        jobs = asyncio.run(matcher.score_jobs(profile, jobs))
        jobs = matcher.filter_jobs(jobs, min_score=min_score)
        progress.update(task3, description=f"✅ {len(jobs)} jobs match your criteria")
    
    # Save jobs
    app_manager = ApplicationManager()
    for job in jobs:
        app_manager.save_job(job)
    
    console.print(f"\n[green]✓[/green] Found {len(jobs)} matching jobs!\n")
    
    # Display top matches
    if jobs:
        table = Table(title="Top Job Matches", show_lines=True)
        table.add_column("Score", justify="center", style="cyan")
        table.add_column("Company", style="magenta")
        table.add_column("Title", style="green")
        table.add_column("Location", style="yellow")
        table.add_column("Source", justify="center")
        
        for job in jobs[:10]:
            table.add_row(
                f"{job.match_score:.0f}",
                job.company,
                job.title,
                job.location,
                job.source.value
            )
        
        console.print(table)


@cli.command()
@click.option('--top', default=5, help='Number of top jobs to apply to')
@click.option('--auto', is_flag=True, help='Auto-generate materials without confirmation')
def apply(top, auto):
    """Apply to top matching jobs"""
    console.print(Panel.fit("📝 [bold blue]Applying to Jobs[/bold blue]", border_style="blue"))
    
    # Load profile
    profile_manager = ProfileManager()
    profile = profile_manager.get_profile()
    
    if not profile:
        console.print("[red]❌ No profile found. Run 'setup' first.[/red]")
        return
    
    # Get top matches
    app_manager = ApplicationManager()
    top_jobs = app_manager.get_top_matches(limit=top)
    
    if not top_jobs:
        console.print("[yellow]No unapplied jobs found. Run 'search' first.[/yellow]")
        return
    
    console.print(f"\n[bold]Preparing applications for top {len(top_jobs)} jobs:[/bold]\n")
    
    content_gen = ContentGenerator()
    settings = get_settings()
    
    for i, job in enumerate(top_jobs, 1):
        console.print(f"\n[bold cyan]{i}. {job.company} - {job.title}[/bold cyan]")
        console.print(f"   Match Score: {job.match_score:.0f}")
        console.print(f"   URL: {job.url}")
        
        if not auto:
            if not click.confirm("   Generate application materials?"):
                continue
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Generate resume
            task1 = progress.add_task("   Tailoring resume...", total=None)
            resume = content_gen.tailor_resume(profile, job)
            progress.update(task1, description="   ✅ Resume tailored")
            
            # Generate cover letter
            task2 = progress.add_task("   Writing cover letter...", total=None)
            cover_letter = content_gen.generate_cover_letter(profile, job)
            progress.update(task2, description="   ✅ Cover letter written")
        
        # Create application
        application = app_manager.create_application(job, resume, cover_letter)
        
        console.print(f"   [green]✓[/green] Application prepared (ID: {application.id})")
        console.print(f"   [yellow]⚠[/yellow]  Manual submission required: {job.url}")
        
        # Check daily limit
        today_stats = app_manager.get_daily_stats()
        if today_stats.applications_sent >= settings.max_daily_applications:
            console.print(f"\n[yellow]Daily application limit reached ({settings.max_daily_applications})[/yellow]")
            break
    
    console.print("\n[green]✓[/green] Application preparation complete!")


@cli.command()
def status():
    """Show application status and statistics"""
    console.print(Panel.fit("📊 [bold blue]Application Status[/bold blue]", border_style="blue"))
    
    app_manager = ApplicationManager()
    stats = app_manager.get_summary_stats()
    
    # Summary stats
    console.print(f"\n[bold]Overall Statistics:[/bold]")
    console.print(f"  Jobs Discovered: {stats['total_jobs_discovered']}")
    console.print(f"  Applications Sent: {stats['total_applications']}")
    console.print(f"  Response Rate: {stats['response_rate']}%")
    console.print(f"  Avg Match Score: {stats['avg_match_score']}")
    console.print(f"  Pending Follow-ups: {stats['pending_followups']}")
    
    # Status breakdown
    table = Table(title="\nApplication Breakdown", show_header=True)
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right", style="magenta")
    
    for status, count in stats['status_breakdown'].items():
        if count > 0:
            table.add_row(status.replace("_", " ").title(), str(count))
    
    console.print(table)
    
    # Top unapplied matches
    top_jobs = app_manager.get_top_matches(limit=5)
    if top_jobs:
        console.print("\n[bold]Top Unapplied Matches:[/bold]")
        for i, job in enumerate(top_jobs, 1):
            console.print(f"  {i}. {job.company} - {job.title} (Score: {job.match_score:.0f})")


@cli.command()
@click.option('--company', '-c', help='Get follow-up email template for specific company')
def followup(company):
    """Show applications needing follow-up and email templates"""
    console.print(Panel.fit("📬 [bold blue]Follow-up Required[/bold blue]", border_style="blue"))
    
    from .enhancers import FollowUpScheduler
    scheduler = FollowUpScheduler()
    
    if company:
        # Show email template for specific company
        console.print(f"\n[bold]Email template for {company}:[/bold]\n")
        # This would need to look up the application details
        console.print("[yellow]Feature coming soon! For now, check your follow_up_schedule.json[/yellow]")
        return
    
    # Show all pending follow-ups
    pending = scheduler.get_pending_follow_ups()
    
    if not pending:
        console.print("\n[green]✓[/green] No follow-ups needed today!")
        return
    
    console.print(f"\n[bold]{len(pending)} applications need follow-up:[/bold]\n")
    
    for i, item in enumerate(pending, 1):
        console.print(f"{i}. [cyan]{item['company']} - {item['role']}[/cyan]")
        console.print(f"   Applied: {item['applied_date'][:10]} ({item['days_since_apply']} days ago)")
        console.print(f"   Status: {item['status']}")
        
        # Show email template
        email = scheduler.get_follow_up_email_template(
            item['company'], 
            item['role'], 
            item['days_since_apply']
        )
        console.print(f"\n[dim]{email[:200]}...[/dim]\n")
    
    console.print("[yellow]💡 Tip: Copy these email templates and send today for best response rate![/yellow]")


@cli.command()
@click.option('--export', '-e', is_flag=True, help='Export summary to file')
def dashboard(export):
    """Show job hunt tracking dashboard"""
    from .dashboard import JobHuntTracker
    
    tracker = JobHuntTracker()
    tracker.show_dashboard()
    
    if export:
        filepath = tracker.export_summary(tracker._load_applications())
        console.print(f"\n[green]✓ Summary exported to {filepath}[/green]")


@cli.command()
@click.option('--resume', '-r', type=click.Path(exists=True), required=True, help='Path to resume PDF')
@click.option('--count', '-c', default=10, help='Number of jobs to apply to')
def autopilot(resume, count):
    """🚀 AUTOPILOT MODE - Full automation for vibe coders"""
    import asyncio
    from .autopilot import run_autopilot
    
    asyncio.run(run_autopilot(resume, count))


@cli.command()
@click.option('--file', '-f', type=click.Path(exists=True), help='Text file with job URLs (one per line)')
@click.option('--resume', '-r', is_flag=True, help='Resume from previous interrupted session')
@click.option('--v2', is_flag=True, help='Use improved V2 with caching and parallel processing')
@click.argument('urls', nargs=-1)
def batch(file, resume, v2, urls):
    """⚡ BATCH APPLY - Maximum automation with job URLs"""
    import asyncio
    
    # Choose version
    if v2:
        from .batch_apply_v2 import run_batch_apply_v2
        run_func = lambda u: run_batch_apply_v2(u, resume=resume)
        console.print("[cyan]Using Batch Apply V2 (improved)[/cyan]\n")
    else:
        from .batch_apply import run_batch_apply
        run_func = run_batch_apply
    
    # Load URLs from file or arguments
    url_list = list(urls)
    
    if file:
        with open(file, 'r') as f:
            file_urls = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
            url_list.extend(file_urls)
    
    if not url_list and not resume:
        console.print("[red]❌ No URLs provided![/red]")
        console.print("\n[yellow]Usage:[/yellow]")
        console.print("  python -m src.main batch <url1> <url2> ...")
        console.print("  python -m src.main batch --file jobs.txt")
        console.print("  python -m src.main batch --file jobs.txt --v2  (improved version)")
        console.print("  python -m src.main batch --resume --v2  (resume interrupted session)")
        console.print("\n[dim]Example:[/dim]")
        console.print("  python -m src.main batch --file jobs.txt --v2")
        return
    
    console.print(f"\n[cyan]Processing {len(url_list) if url_list else 'saved'} job URLs...[/cyan]\n")
    asyncio.run(run_func(url_list if url_list else []))


@cli.command()
@click.option('--keywords', '-k', multiple=True, help='Search keywords (e.g., "Senior AI Engineer")')
@click.option('--limit', '-l', default=20, help='Maximum jobs to find')
def autosearch(keywords, limit):
    """🤖 AUTO SEARCH - Attempt to automatically find jobs (experimental)"""
    import asyncio
    from .auto_search import run_auto_search
    
    console.print("[yellow]⚠️ This is experimental - automated scrapers may be blocked[/yellow]")
    console.print("[dim]Manual search + batch apply is more reliable[/dim]\n")
    
    proceed = input("Continue anyway? (y/n): ").lower().strip()
    
    if proceed == 'y':
        asyncio.run(run_auto_search(list(keywords), limit))
    else:
        console.print("\n[cyan]No problem! Use manual search instead:[/cyan]")
        console.print("1. Go to: https://www.linkedin.com/jobs/")
        console.print("2. Search for your roles")
        console.print("3. Copy URLs to jobs.txt")
        console.print("4. Run: py -m src.main batch --file jobs.txt --v2")


if __name__ == "__main__":
    cli()
