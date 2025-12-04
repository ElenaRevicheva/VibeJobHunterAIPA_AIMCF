"""
Google Analytics 4 Performance Tracker
Fetches and displays real-time website metrics from GA4
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2.service_account import Credentials

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class GA4PerformanceTracker:
    """Track website performance using Google Analytics 4 API"""
    
    def __init__(self):
        self.console = Console()
        self.property_id = os.getenv('GA4_PROPERTY_ID')
        self.credentials = self._load_credentials()
        self.client = None
        
        if self.credentials and self.property_id:
            self.client = BetaAnalyticsDataClient(credentials=self.credentials)
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load service account credentials from environment"""
        try:
            creds_json = os.getenv('GOOGLE_ANALYTICS_CREDENTIALS')
            if not creds_json:
                self.console.print("[yellow]Warning: GOOGLE_ANALYTICS_CREDENTIALS not set[/yellow]")
                return None
            
            # Parse JSON from environment variable
            creds_data = json.loads(creds_json)
            
            # Create credentials object
            credentials = Credentials.from_service_account_info(
                creds_data,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )
            
            return credentials
            
        except Exception as e:
            self.console.print(f"[red]Error loading credentials: {e}[/red]")
            return None
    
    def get_website_metrics(self, days: int = 7) -> Dict:
        """Fetch website metrics from GA4"""
        if not self.client:
            return self._get_mock_data()
        
        try:
            # Date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Run the report
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimensions=[
                    Dimension(name="date"),
                ],
                metrics=[
                    Metric(name="activeUsers"),
                    Metric(name="sessions"),
                    Metric(name="screenPageViews"),
                    Metric(name="averageSessionDuration"),
                    Metric(name="bounceRate"),
                ]
            )
            
            response = self.client.run_report(request)
            
            # Parse response
            metrics = self._parse_response(response)
            return metrics
            
        except Exception as e:
            self.console.print(f"[red]Error fetching GA4 data: {e}[/red]")
            return self._get_mock_data()
    
    def get_top_pages(self, days: int = 7) -> List[Dict]:
        """Get top performing pages"""
        if not self.client:
            return []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimensions=[
                    Dimension(name="pageTitle"),
                    Dimension(name="pagePath"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="activeUsers"),
                ],
                limit=10
            )
            
            response = self.client.run_report(request)
            
            # Parse pages
            pages = []
            for row in response.rows:
                pages.append({
                    'title': row.dimension_values[0].value,
                    'path': row.dimension_values[1].value,
                    'views': int(row.metric_values[0].value),
                    'users': int(row.metric_values[1].value)
                })
            
            return sorted(pages, key=lambda x: x['views'], reverse=True)
            
        except Exception as e:
            self.console.print(f"[red]Error fetching top pages: {e}[/red]")
            return []
    
    def get_traffic_sources(self, days: int = 7) -> List[Dict]:
        """Get traffic sources"""
        if not self.client:
            return []
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )],
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                ],
                limit=10
            )
            
            response = self.client.run_report(request)
            
            # Parse sources
            sources = []
            for row in response.rows:
                sources.append({
                    'source': row.dimension_values[0].value,
                    'medium': row.dimension_values[1].value,
                    'sessions': int(row.metric_values[0].value),
                    'users': int(row.metric_values[1].value)
                })
            
            return sorted(sources, key=lambda x: x['sessions'], reverse=True)
            
        except Exception as e:
            self.console.print(f"[red]Error fetching traffic sources: {e}[/red]")
            return []
    
    def _parse_response(self, response) -> Dict:
        """Parse GA4 API response into metrics dict"""
        total_users = 0
        total_sessions = 0
        total_pageviews = 0
        total_duration = 0
        total_bounce_rate = 0
        count = 0
        
        for row in response.rows:
            total_users += int(row.metric_values[0].value)
            total_sessions += int(row.metric_values[1].value)
            total_pageviews += int(row.metric_values[2].value)
            total_duration += float(row.metric_values[3].value)
            total_bounce_rate += float(row.metric_values[4].value)
            count += 1
        
        return {
            'users': total_users,
            'sessions': total_sessions,
            'pageviews': total_pageviews,
            'avg_session_duration': total_duration / count if count > 0 else 0,
            'bounce_rate': total_bounce_rate / count if count > 0 else 0,
        }
    
    def _get_mock_data(self) -> Dict:
        """Return mock data for testing"""
        return {
            'users': 0,
            'sessions': 0,
            'pageviews': 0,
            'avg_session_duration': 0,
            'bounce_rate': 0,
        }
    
    def show_dashboard(self, days: int = 7):
        """Display performance dashboard"""
        self.console.clear()
        
        # Header
        self.console.print(Panel(
            f"[bold cyan]📊 AIdeazz.xyz Performance Dashboard[/bold cyan]\n"
            f"[dim]Last {days} days • Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}[/dim]",
            style="cyan"
        ))
        
        # Fetch data
        metrics = self.get_website_metrics(days)
        top_pages = self.get_top_pages(days)
        sources = self.get_traffic_sources(days)
        
        # Overview metrics
        self._show_overview(metrics)
        
        # Top pages table
        if top_pages:
            self.console.print("\n")
            self._show_top_pages(top_pages)
        
        # Traffic sources
        if sources:
            self.console.print("\n")
            self._show_traffic_sources(sources)
    
    def _show_overview(self, metrics: Dict):
        """Show overview metrics"""
        users = metrics.get('users', 0)
        sessions = metrics.get('sessions', 0)
        pageviews = metrics.get('pageviews', 0)
        avg_duration = metrics.get('avg_session_duration', 0)
        bounce_rate = metrics.get('bounce_rate', 0)
        
        # Calculate derived metrics
        pages_per_session = pageviews / sessions if sessions > 0 else 0
        
        overview = f"""
[bold]TRAFFIC OVERVIEW:[/bold]
  Users: [cyan]{users:,}[/cyan] | Sessions: [yellow]{sessions:,}[/yellow] | Pageviews: [green]{pageviews:,}[/green]

[bold]ENGAGEMENT:[/bold]
  Avg Session: [cyan]{avg_duration:.0f}s[/cyan] | Pages/Session: [yellow]{pages_per_session:.2f}[/yellow] | Bounce Rate: [red]{bounce_rate:.1f}%[/red]

[bold]GROWTH:[/bold]
  Daily Avg Users: [cyan]{users/7:.0f}[/cyan] | Daily Avg Sessions: [yellow]{sessions/7:.0f}[/yellow]
"""
        
        self.console.print(Panel(overview, title="📈 Metrics", border_style="green"))
    
    def _show_top_pages(self, pages: List[Dict]):
        """Show top pages table"""
        table = Table(title="🔝 Top Pages", box=box.ROUNDED, show_header=True)
        table.add_column("Page", style="bold", no_wrap=False)
        table.add_column("Views", justify="right", style="cyan")
        table.add_column("Users", justify="right", style="yellow")
        
        for page in pages[:10]:
            title = page['title']
            if len(title) > 50:
                title = title[:47] + "..."
            
            table.add_row(
                title,
                f"{page['views']:,}",
                f"{page['users']:,}"
            )
        
        self.console.print(table)
    
    def _show_traffic_sources(self, sources: List[Dict]):
        """Show traffic sources table"""
        table = Table(title="🌐 Traffic Sources", box=box.ROUNDED, show_header=True)
        table.add_column("Source", style="bold")
        table.add_column("Medium", style="dim")
        table.add_column("Sessions", justify="right", style="cyan")
        table.add_column("Users", justify="right", style="yellow")
        
        for source in sources[:10]:
            table.add_row(
                source['source'],
                source['medium'],
                f"{source['sessions']:,}",
                f"{source['users']:,}"
            )
        
        self.console.print(table)
    
    def export_report(self, days: int = 7) -> str:
        """Export performance report to markdown"""
        metrics = self.get_website_metrics(days)
        top_pages = self.get_top_pages(days)
        sources = self.get_traffic_sources(days)
        
        content = f"""# AIdeazz.xyz Performance Report
**Period:** Last {days} days
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview Metrics
- **Users:** {metrics.get('users', 0):,}
- **Sessions:** {metrics.get('sessions', 0):,}
- **Pageviews:** {metrics.get('pageviews', 0):,}
- **Avg Session Duration:** {metrics.get('avg_session_duration', 0):.0f}s
- **Bounce Rate:** {metrics.get('bounce_rate', 0):.1f}%

## Top Pages
"""
        
        for i, page in enumerate(top_pages[:10], 1):
            content += f"{i}. **{page['title']}** - {page['views']:,} views, {page['users']:,} users\n"
        
        content += "\n## Traffic Sources\n"
        for i, source in enumerate(sources[:10], 1):
            content += f"{i}. **{source['source']}** ({source['medium']}) - {source['sessions']:,} sessions\n"
        
        # Save to file
        report_file = Path.cwd() / f"ga4_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w') as f:
            f.write(content)
        
        return str(report_file)


# CLI Interface
if __name__ == "__main__":
    tracker = GA4PerformanceTracker()
    tracker.show_dashboard(days=7)
