"""
Job Hunt Tracker Dashboard
Visualizes progress, metrics, and success
"""
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.layout import Layout
from rich import box

from ..core.models import Application, ApplicationStatus


class JobHuntTracker:
    """Track and visualize job hunt progress"""
    
    def __init__(self):
        self.console = Console()
        self.data_dir = Path.cwd() / "data"
        self.applications_file = self.data_dir / "applications.json"
        self.metrics_file = self.data_dir / "metrics.json"
    
    def show_dashboard(self):
        """Display the main tracking dashboard"""
        self.console.clear()
        
        # Load data
        applications = self._load_applications()
        metrics = self._calculate_metrics(applications)
        
        # Create layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=12),
            Layout(name="tables")
        )
        
        # Header
        layout["header"].update(
            Panel(
                "[bold cyan]🎯 JOB HUNT TRACKER[/bold cyan]\n"
                f"[dim]Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]",
                style="cyan"
            )
        )
        
        # Stats
        stats_text = self._format_stats(metrics, applications)
        layout["stats"].update(Panel(stats_text, title="📊 Overview", border_style="green"))
        
        # Tables
        layout["tables"].split_row(
            Layout(self._create_status_table(applications), name="status"),
            Layout(self._create_recent_table(applications), name="recent")
        )
        
        self.console.print(layout)
        
        # Follow-up reminders
        self._show_follow_up_reminders(applications)
    
    def _format_stats(self, metrics: Dict, applications: List[Application]) -> str:
        """Format stats panel"""
        total = metrics['total']
        applied = metrics['applied']
        interviewing = metrics['interviewing']
        offers = metrics['offers']
        rejected = metrics['rejected']
        
        # Calculate rates
        response_rate = (interviewing / applied * 100) if applied > 0 else 0
        success_rate = (offers / applied * 100) if applied > 0 else 0
        avg_per_day = metrics['avg_per_day']
        
        # Progress bars
        target = 50  # Target: 50 applications
        progress_pct = min(applied / target * 100, 100)
        
        return f"""
[bold]APPLICATIONS:[/bold]
  Total: {total} | Applied: [cyan]{applied}[/cyan] | Interviewing: [yellow]{interviewing}[/yellow] | Offers: [green]{offers}[/green] | Rejected: [red]{rejected}[/red]

[bold]SUCCESS METRICS:[/bold]
  Response Rate: [cyan]{response_rate:.1f}%[/cyan] | Success Rate: [green]{success_rate:.1f}%[/green] | Avg/Day: [yellow]{avg_per_day:.1f}[/yellow]

[bold]PROGRESS TO TARGET (50 apps):[/bold]
  {"█" * int(progress_pct / 2)}{" " * (50 - int(progress_pct / 2))} {applied}/50 ({progress_pct:.0f}%)

[bold]TIME TO OFFER (estimate):[/bold]
  At current rate: [yellow]{metrics['estimated_days_to_offer']} days[/yellow] | Target: [green]30 days[/green]
"""
    
    def _create_status_table(self, applications: List[Application]) -> Table:
        """Create status breakdown table"""
        table = Table(title="📋 By Status", box=box.ROUNDED, show_header=True)
        table.add_column("Status", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("Latest", style="dim")
        
        # Group by status
        by_status = defaultdict(list)
        for app in applications:
            by_status[app.status].append(app)
        
        # Add rows
        status_order = [
            ApplicationStatus.OFFER_RECEIVED,
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.APPLIED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.DRAFT
        ]
        
        for status in status_order:
            apps = by_status[status]
            if apps:
                latest = max(apps, key=lambda x: x.applied_date)
                table.add_row(
                    self._format_status(status),
                    str(len(apps)),
                    latest.company
                )
        
        return table
    
    def _create_recent_table(self, applications: List[Application]) -> Table:
        """Create recent applications table"""
        table = Table(title="🕒 Recent Activity", box=box.ROUNDED, show_header=True)
        table.add_column("Company", style="bold")
        table.add_column("Role", style="cyan")
        table.add_column("Status")
        table.add_column("Date", style="dim")
        
        # Get last 10
        recent = sorted(applications, key=lambda x: x.applied_date, reverse=True)[:10]
        
        for app in recent:
            table.add_row(
                app.company,
                app.role[:30] + "..." if len(app.role) > 30 else app.role,
                self._format_status_short(app.status),
                app.applied_date.strftime('%m/%d')
            )
        
        return table
    
    def _show_follow_up_reminders(self, applications: List[Application]):
        """Show follow-up reminders"""
        now = datetime.now()
        needs_follow_up = []
        
        for app in applications:
            if app.status == ApplicationStatus.APPLIED:
                days_since = (now - app.applied_date).days
                if days_since >= 3:
                    needs_follow_up.append((app, days_since))
        
        if needs_follow_up:
            self.console.print("\n")
            panel_text = "[bold yellow]📧 FOLLOW-UP REMINDERS:[/bold yellow]\n\n"
            
            for app, days in sorted(needs_follow_up, key=lambda x: x[1], reverse=True)[:5]:
                urgency = "🔴" if days > 7 else "🟡"
                panel_text += f"{urgency} {app.company} - {app.role} ({days} days ago)\n"
            
            self.console.print(Panel(panel_text, border_style="yellow"))
    
    def _calculate_metrics(self, applications: List[Application]) -> Dict:
        """Calculate key metrics"""
        now = datetime.now()
        
        total = len(applications)
        applied = len([a for a in applications if a.status in [
            ApplicationStatus.APPLIED, 
            ApplicationStatus.INTERVIEWING,
            ApplicationStatus.OFFER_RECEIVED,
            ApplicationStatus.REJECTED
        ]])
        interviewing = len([a for a in applications if a.status == ApplicationStatus.INTERVIEWING])
        offers = len([a for a in applications if a.status == ApplicationStatus.OFFER_RECEIVED])
        rejected = len([a for a in applications if a.status == ApplicationStatus.REJECTED])
        
        # Calculate date range
        if applications:
            earliest = min(a.applied_date for a in applications if a.status != ApplicationStatus.DRAFT)
            days_active = max((now - earliest).days, 1)
        else:
            days_active = 1
        
        avg_per_day = applied / days_active if days_active > 0 else 0
        
        # Estimate days to offer
        # Assuming 5% conversion rate (industry average)
        if avg_per_day > 0:
            apps_needed = 20  # Need ~20 apps to get 1 offer at 5%
            estimated_days = apps_needed / avg_per_day
        else:
            estimated_days = 999
        
        return {
            'total': total,
            'applied': applied,
            'interviewing': interviewing,
            'offers': offers,
            'rejected': rejected,
            'days_active': days_active,
            'avg_per_day': avg_per_day,
            'estimated_days_to_offer': int(estimated_days)
        }
    
    def show_company_insights(self, applications: List[Application]):
        """Show insights by company"""
        self.console.print("\n[bold cyan]🏢 COMPANY INSIGHTS[/bold cyan]\n")
        
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Company", style="bold")
        table.add_column("Applications", justify="right")
        table.add_column("Latest Status")
        table.add_column("Match Score", justify="right")
        
        # Group by company
        by_company = defaultdict(list)
        for app in applications:
            by_company[app.company].append(app)
        
        # Sort by number of applications
        sorted_companies = sorted(by_company.items(), key=lambda x: len(x[1]), reverse=True)
        
        for company, apps in sorted_companies[:15]:
            latest = max(apps, key=lambda x: x.applied_date)
            avg_score = sum(a.ai_match_score for a in apps) / len(apps)
            
            table.add_row(
                company,
                str(len(apps)),
                self._format_status_short(latest.status),
                f"{avg_score}%"
            )
        
        self.console.print(table)
    
    def _format_status(self, status: ApplicationStatus) -> str:
        """Format status with emoji"""
        emoji_map = {
            ApplicationStatus.DRAFT: "📝 Draft",
            ApplicationStatus.APPLIED: "📧 Applied",
            ApplicationStatus.INTERVIEWING: "🎤 Interviewing",
            ApplicationStatus.OFFER_RECEIVED: "🎉 Offer",
            ApplicationStatus.REJECTED: "❌ Rejected"
        }
        return emoji_map.get(status, str(status))
    
    def _format_status_short(self, status: ApplicationStatus) -> str:
        """Format status short"""
        emoji_map = {
            ApplicationStatus.DRAFT: "📝",
            ApplicationStatus.APPLIED: "📧",
            ApplicationStatus.INTERVIEWING: "🎤",
            ApplicationStatus.OFFER_RECEIVED: "🎉",
            ApplicationStatus.REJECTED: "❌"
        }
        return emoji_map.get(status, "?")
    
    def _load_applications(self) -> List[Application]:
        """Load applications from file"""
        if not self.applications_file.exists():
            return []
        
        try:
            with open(self.applications_file, 'r') as f:
                data = json.load(f)
                
            applications = []
            for app_data in data:
                # Convert date strings to datetime
                if 'applied_date' in app_data:
                    app_data['applied_date'] = datetime.fromisoformat(app_data['applied_date'])
                
                # Convert status string to enum
                if 'status' in app_data:
                    app_data['status'] = ApplicationStatus(app_data['status'])
                
                applications.append(Application(**app_data))
            
            return applications
        except Exception as e:
            self.console.print(f"[red]Error loading applications: {e}[/red]")
            return []
    
    def export_summary(self, applications: List[Application]) -> str:
        """Export summary to markdown file"""
        metrics = self._calculate_metrics(applications)
        
        content = f"""# Job Hunt Summary
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview
- **Total Applications:** {metrics['total']}
- **Applied:** {metrics['applied']}
- **Interviewing:** {metrics['interviewing']}
- **Offers:** {metrics['offers']}
- **Rejected:** {metrics['rejected']}

## Performance
- **Days Active:** {metrics['days_active']}
- **Average per Day:** {metrics['avg_per_day']:.2f}
- **Response Rate:** {(metrics['interviewing'] / metrics['applied'] * 100 if metrics['applied'] > 0 else 0):.1f}%
- **Success Rate:** {(metrics['offers'] / metrics['applied'] * 100 if metrics['applied'] > 0 else 0):.1f}%

## Recent Applications
"""
        
        recent = sorted(applications, key=lambda x: x.applied_date, reverse=True)[:20]
        for app in recent:
            content += f"- **{app.company}** - {app.role} ({app.status.value}) - {app.applied_date.strftime('%Y-%m-%d')}\n"
        
        # Save to file
        summary_file = Path.cwd() / "job_hunt_summary.md"
        with open(summary_file, 'w') as f:
            f.write(content)
        
        return str(summary_file)
