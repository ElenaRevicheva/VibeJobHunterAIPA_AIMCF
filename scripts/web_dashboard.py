#!/usr/bin/env python3
"""
Web-based GA4 Dashboard - Accessible via HTTP
Can be added to Railway as an endpoint
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard.performance_tracker import GA4PerformanceTracker

def generate_html_dashboard(days=7):
    """Generate HTML dashboard"""
    tracker = GA4PerformanceTracker()
    
    # Get data
    metrics = tracker.get_website_metrics(days)
    top_pages = tracker.get_top_pages(days)
    sources = tracker.get_traffic_sources(days)
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIdeazz.xyz - GA4 Performance Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .metric-card h3 {{
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        
        .metric-card .value {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}
        
        .metric-card .label {{
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }}
        
        .section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge-primary {{
            background: #e0e7ff;
            color: #667eea;
        }}
        
        .badge-success {{
            background: #d1fae5;
            color: #059669;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.8;
        }}
        
        .refresh-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
        }}
        
        .refresh-btn:hover {{
            background: #5568d3;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 AIdeazz.xyz Performance Dashboard</h1>
            <p>Last {days} days • Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Active Users</h3>
                <div class="value">{metrics.get('users', 0):,}</div>
                <div class="label">Unique visitors</div>
            </div>
            
            <div class="metric-card">
                <h3>Sessions</h3>
                <div class="value">{metrics.get('sessions', 0):,}</div>
                <div class="label">Total visits</div>
            </div>
            
            <div class="metric-card">
                <h3>Pageviews</h3>
                <div class="value">{metrics.get('pageviews', 0):,}</div>
                <div class="label">Pages viewed</div>
            </div>
            
            <div class="metric-card">
                <h3>Avg Duration</h3>
                <div class="value">{metrics.get('avg_session_duration', 0):.0f}s</div>
                <div class="label">Time on site</div>
            </div>
            
            <div class="metric-card">
                <h3>Bounce Rate</h3>
                <div class="value">{metrics.get('bounce_rate', 0):.1f}%</div>
                <div class="label">Single page visits</div>
            </div>
            
            <div class="metric-card">
                <h3>Pages/Session</h3>
                <div class="value">{(metrics.get('pageviews', 0) / metrics.get('sessions', 1) if metrics.get('sessions', 0) > 0 else 0):.2f}</div>
                <div class="label">Engagement metric</div>
            </div>
        </div>
"""
    
    # Top Pages Section
    if top_pages:
        html += """
        <div class="section">
            <h2>🔝 Top Pages</h2>
            <table>
                <thead>
                    <tr>
                        <th>Page Title</th>
                        <th>Views</th>
                        <th>Users</th>
                    </tr>
                </thead>
                <tbody>
"""
        for page in top_pages[:10]:
            html += f"""
                    <tr>
                        <td>{page['title']}</td>
                        <td><span class="badge badge-primary">{page['views']:,} views</span></td>
                        <td>{page['users']:,} users</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Traffic Sources Section
    if sources:
        html += """
        <div class="section">
            <h2>🌐 Traffic Sources</h2>
            <table>
                <thead>
                    <tr>
                        <th>Source</th>
                        <th>Medium</th>
                        <th>Sessions</th>
                        <th>Users</th>
                    </tr>
                </thead>
                <tbody>
"""
        for source in sources[:10]:
            badge_class = "badge-success" if source['source'] == 'linkedin' else "badge-primary"
            html += f"""
                    <tr>
                        <td><strong>{source['source']}</strong></td>
                        <td>{source['medium']}</td>
                        <td><span class="badge {badge_class}">{source['sessions']:,} sessions</span></td>
                        <td>{source['users']:,} users</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # No Data Message
    if not top_pages and not sources and metrics.get('users', 0) == 0:
        html += """
        <div class="section" style="text-align: center; padding: 60px;">
            <h2 style="color: #999; margin-bottom: 20px;">📊 Waiting for Data</h2>
            <p style="color: #666;">GA4 is collecting data. Check back in 24-48 hours!</p>
            <p style="color: #999; margin-top: 10px; font-size: 14px;">
                Tracking is active on aideazz.xyz. Data will appear here once processed by Google Analytics.
            </p>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>Powered by Google Analytics 4 • AIdeazz Performance Tracker</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def generate_json_api(days=7):
    """Generate JSON API response"""
    tracker = GA4PerformanceTracker()
    
    metrics = tracker.get_website_metrics(days)
    top_pages = tracker.get_top_pages(days)
    sources = tracker.get_traffic_sources(days)
    
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "period_days": days,
        "metrics": metrics,
        "top_pages": top_pages[:10],
        "traffic_sources": sources[:10]
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate web dashboard')
    parser.add_argument('--days', type=int, default=7, help='Number of days')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of HTML')
    parser.add_argument('--output', help='Output file path')
    
    args = parser.parse_args()
    
    if args.json:
        output = json.dumps(generate_json_api(args.days), indent=2)
    else:
        output = generate_html_dashboard(args.days)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"✅ Dashboard saved to: {args.output}")
    else:
        print(output)
