"""
FastAPI application for web dashboard
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from ..core import ProfileManager, get_settings
from ..agents import ApplicationManager, JobMatcher


def create_app() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="VibeJobHunter Dashboard",
        description="AI-powered job hunting automation dashboard",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize managers
    profile_manager = ProfileManager()
    app_manager = ApplicationManager()
    
    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """Dashboard homepage"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>VibeJobHunter Dashboard</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: #333;
                }
                .container {
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                h1 {
                    color: #667eea;
                    margin-bottom: 10px;
                }
                .subtitle {
                    color: #666;
                    margin-bottom: 30px;
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .stat-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }
                .stat-value {
                    font-size: 2.5em;
                    font-weight: bold;
                    margin: 10px 0;
                }
                .stat-label {
                    font-size: 0.9em;
                    opacity: 0.9;
                }
                .section {
                    margin: 30px 0;
                }
                .job-card {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                    transition: transform 0.2s;
                }
                .job-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .job-title {
                    font-size: 1.2em;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 5px;
                }
                .job-company {
                    color: #764ba2;
                    font-weight: 500;
                }
                .job-meta {
                    display: flex;
                    gap: 15px;
                    margin-top: 10px;
                    color: #666;
                    font-size: 0.9em;
                }
                .score {
                    background: #4ade80;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-weight: bold;
                }
                .api-link {
                    display: inline-block;
                    margin: 10px 10px 0 0;
                    padding: 8px 16px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    font-size: 0.9em;
                }
                .api-link:hover {
                    background: #764ba2;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 VibeJobHunter Dashboard</h1>
                <p class="subtitle">AI-powered job hunting automation for Elena Revicheva</p>
                
                <div class="stats-grid" id="stats">
                    <div class="stat-card">
                        <div class="stat-label">Jobs Discovered</div>
                        <div class="stat-value" id="total-jobs">-</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Applications Sent</div>
                        <div class="stat-value" id="total-apps">-</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Response Rate</div>
                        <div class="stat-value" id="response-rate">-</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Avg Match Score</div>
                        <div class="stat-value" id="avg-score">-</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>🎯 Top Job Matches</h2>
                    <div id="top-jobs"></div>
                </div>
                
                <div class="section">
                    <h3>📡 API Endpoints</h3>
                    <a href="/api/stats" class="api-link">View Stats (JSON)</a>
                    <a href="/api/jobs" class="api-link">All Jobs (JSON)</a>
                    <a href="/api/applications" class="api-link">Applications (JSON)</a>
                    <a href="/docs" class="api-link">API Documentation</a>
                </div>
            </div>
            
            <script>
                // Fetch and display stats
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('total-jobs').textContent = data.total_jobs_discovered;
                        document.getElementById('total-apps').textContent = data.total_applications;
                        document.getElementById('response-rate').textContent = data.response_rate + '%';
                        document.getElementById('avg-score').textContent = data.avg_match_score;
                    });
                
                // Fetch and display top jobs
                fetch('/api/jobs/top?limit=5')
                    .then(r => r.json())
                    .then(jobs => {
                        const container = document.getElementById('top-jobs');
                        jobs.forEach(job => {
                            const card = document.createElement('div');
                            card.className = 'job-card';
                            card.innerHTML = `
                                <div class="job-title">${job.title}</div>
                                <div class="job-company">${job.company}</div>
                                <div class="job-meta">
                                    <span class="score">${Math.round(job.match_score)} match</span>
                                    <span>📍 ${job.location}</span>
                                    <span>🔗 ${job.source}</span>
                                </div>
                                ${job.match_reasons ? '<div style="margin-top:10px;color:#666;">• ' + job.match_reasons.slice(0,2).join('<br>• ') + '</div>' : ''}
                            `;
                            container.appendChild(card);
                        });
                    });
            </script>
        </body>
        </html>
        """
    
    @app.get("/api/stats")
    async def get_stats():
        """Get application statistics"""
        return app_manager.get_summary_stats()
    
    @app.get("/api/profile")
    async def get_profile():
        """Get user profile"""
        profile = profile_manager.get_profile()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile.model_dump()
    
    @app.get("/api/jobs")
    async def get_jobs(limit: Optional[int] = 50, min_score: Optional[float] = 0):
        """Get all jobs"""
        jobs = list(app_manager.jobs.values())
        jobs = [j for j in jobs if j.match_score >= min_score]
        jobs.sort(key=lambda j: j.match_score, reverse=True)
        return [job.model_dump() for job in jobs[:limit]]
    
    @app.get("/api/jobs/top")
    async def get_top_jobs(limit: int = 10):
        """Get top matching unapplied jobs"""
        jobs = app_manager.get_top_matches(limit=limit)
        return [job.model_dump() for job in jobs]
    
    @app.get("/api/applications")
    async def get_applications(status: Optional[str] = None):
        """Get applications"""
        if status:
            try:
                from ..core.models import ApplicationStatus
                status_enum = ApplicationStatus(status)
                apps = app_manager.get_applications_by_status(status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")
        else:
            apps = list(app_manager.applications.values())
        
        return [app.model_dump() for app in apps]
    
    @app.get("/api/followups")
    async def get_followups():
        """Get applications needing follow-up"""
        apps = app_manager.get_applications_needing_followup()
        return [app.model_dump() for app in apps]
    
    return app
