"""
Application tracking and management
"""
import json
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path

from ..core.models import (
    Application,
    JobPosting,
    ApplicationStatus,
    Profile,
    DailyStats
)
from ..core.config import get_settings


class ApplicationManager:
    """Manage job applications and tracking"""
    
    def __init__(self):
        self.settings = get_settings()
        self.applications_dir = self.settings.data_dir / "applications"
        self.jobs_dir = self.settings.data_dir / "jobs"
        self.stats_dir = self.settings.data_dir / "stats"
        
        # Ensure directories exist
        self.applications_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.stats_dir.mkdir(parents=True, exist_ok=True)
        
        self.applications: Dict[str, Application] = {}
        self.jobs: Dict[str, JobPosting] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load applications and jobs from disk"""
        # Load applications
        for app_file in self.applications_dir.glob("*.json"):
            try:
                with open(app_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    app = Application(**data)
                    self.applications[app.id] = app
            except Exception as e:
                print(f"Error loading application {app_file}: {e}")
        
        # Load jobs
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    job = JobPosting(**data)
                    self.jobs[job.id] = job
            except Exception as e:
                print(f"Error loading job {job_file}: {e}")
    
    def save_job(self, job: JobPosting):
        """Save job posting to disk"""
        self.jobs[job.id] = job
        filepath = self.jobs_dir / f"{job.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(job.model_dump(), f, indent=2, default=str)
    
    def save_application(self, application: Application):
        """Save application to disk"""
        self.applications[application.id] = application
        filepath = self.applications_dir / f"{application.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(application.model_dump(), f, indent=2, default=str)
    
    def create_application(
        self,
        job: JobPosting,
        resume_version: str,
        cover_letter: Optional[str] = None
    ) -> Application:
        """Create new application"""
        application = Application(
            id=job.id,
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            status=ApplicationStatus.APPLIED,
            applied_date=datetime.now(),
            source=job.source,
            application_url=job.url,
            resume_version=resume_version,
            cover_letter_content=cover_letter,
            timeline=[{
                "status": ApplicationStatus.APPLIED.value,
                "timestamp": datetime.now().isoformat(),
                "note": "Application submitted"
            }]
        )
        
        # Mark job as applied
        job.applied = True
        job.application_date = datetime.now()
        job.status = ApplicationStatus.APPLIED
        
        self.save_application(application)
        self.save_job(job)
        
        return application
    
    def update_application_status(
        self,
        application_id: str,
        new_status: ApplicationStatus,
        note: str = ""
    ):
        """Update application status"""
        if application_id not in self.applications:
            raise ValueError(f"Application {application_id} not found")
        
        app = self.applications[application_id]
        app.status = new_status
        app.updated_at = datetime.now()
        
        # Add to timeline
        app.timeline.append({
            "status": new_status.value,
            "timestamp": datetime.now().isoformat(),
            "note": note
        })
        
        # Update job status
        if app.job_id in self.jobs:
            self.jobs[app.job_id].status = new_status
            self.save_job(self.jobs[app.job_id])
        
        self.save_application(app)
    
    def get_applications_by_status(self, status: ApplicationStatus) -> List[Application]:
        """Get all applications with specific status"""
        return [
            app for app in self.applications.values()
            if app.status == status
        ]
    
    def get_applications_needing_followup(self) -> List[Application]:
        """Get applications that need follow-up"""
        now = datetime.now()
        needs_followup = []
        
        for app in self.applications.values():
            # Skip if already responded or rejected
            if app.status in [ApplicationStatus.REJECTED, ApplicationStatus.OFFER]:
                continue
            
            # Check if follow-up is due
            if app.next_follow_up and app.next_follow_up <= now:
                needs_followup.append(app)
            # If no follow-up scheduled and been > 7 days, add it
            elif not app.next_follow_up:
                days_since_applied = (now - app.applied_date).days
                if days_since_applied >= 7:
                    needs_followup.append(app)
        
        return needs_followup
    
    def schedule_followup(self, application_id: str, days_from_now: int = 7):
        """Schedule follow-up for application"""
        if application_id not in self.applications:
            raise ValueError(f"Application {application_id} not found")
        
        app = self.applications[application_id]
        app.next_follow_up = datetime.now() + timedelta(days=days_from_now)
        app.updated_at = datetime.now()
        
        self.save_application(app)
    
    def get_daily_stats(self, date: Optional[str] = None) -> DailyStats:
        """Get statistics for a specific day"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        stats = DailyStats(date=date)
        
        # Count jobs discovered
        for job in self.jobs.values():
            if job.discovered_at.strftime("%Y-%m-%d") == date:
                stats.jobs_discovered += 1
        
        # Count applications sent
        for app in self.applications.values():
            if app.applied_date.strftime("%Y-%m-%d") == date:
                stats.applications_sent += 1
            
            # Count responses
            for event in app.timeline:
                event_date = datetime.fromisoformat(event["timestamp"]).strftime("%Y-%m-%d")
                if event_date == date:
                    if event["status"] in ["interviewing", "offer"]:
                        stats.responses_received += 1
                    if event["status"] == "interviewing":
                        stats.interviews_scheduled += 1
        
        return stats
    
    def get_summary_stats(self) -> dict:
        """Get overall summary statistics"""
        total_jobs = len(self.jobs)
        total_applications = len(self.applications)
        
        status_counts = {}
        for status in ApplicationStatus:
            status_counts[status.value] = len(self.get_applications_by_status(status))
        
        # Calculate response rate
        responses = status_counts.get("interviewing", 0) + status_counts.get("offer", 0)
        response_rate = (responses / total_applications * 100) if total_applications > 0 else 0
        
        # Average match score
        avg_match_score = sum(j.match_score for j in self.jobs.values()) / total_jobs if total_jobs > 0 else 0
        
        return {
            "total_jobs_discovered": total_jobs,
            "total_applications": total_applications,
            "status_breakdown": status_counts,
            "response_rate": round(response_rate, 2),
            "avg_match_score": round(avg_match_score, 2),
            "pending_followups": len(self.get_applications_needing_followup()),
        }
    
    def get_top_matches(self, limit: int = 10) -> List[JobPosting]:
        """Get top matching jobs not yet applied to"""
        unapplied = [j for j in self.jobs.values() if not j.applied]
        unapplied.sort(key=lambda j: j.match_score, reverse=True)
        return unapplied[:limit]
