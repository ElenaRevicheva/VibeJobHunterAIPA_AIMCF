"""
Auto-follow-up scheduler
Tracks applications and sends follow-up reminders
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import json

from ..core.models import Application, ApplicationStatus


class FollowUpScheduler:
    """Schedule and track follow-ups"""
    
    def __init__(self):
        self.schedule_file = Path.cwd() / "data" / "follow_up_schedule.json"
        self.schedule_file.parent.mkdir(exist_ok=True, parents=True)
    
    def schedule_follow_up(self, application: Application, days: int = 3):
        """
        Schedule a follow-up for an application
        
        Args:
            application: Application to follow up on
            days: Days until follow-up
        """
        follow_up_date = datetime.now() + timedelta(days=days)
        
        schedule = self._load_schedule()
        
        schedule[application.id] = {
            'company': application.company,
            'role': application.role,
            'applied_date': application.applied_date.isoformat(),
            'follow_up_date': follow_up_date.isoformat(),
            'status': application.status.value,
            'days_since_apply': days
        }
        
        self._save_schedule(schedule)
    
    def get_pending_follow_ups(self) -> List[Dict]:
        """
        Get all pending follow-ups for today and past due
        
        Returns:
            List of applications needing follow-up
        """
        schedule = self._load_schedule()
        now = datetime.now()
        
        pending = []
        for app_id, data in schedule.items():
            follow_up_date = datetime.fromisoformat(data['follow_up_date'])
            
            # If follow-up date is today or past
            if follow_up_date <= now:
                days_since = (now - datetime.fromisoformat(data['applied_date'])).days
                data['days_since_apply'] = days_since
                data['app_id'] = app_id
                pending.append(data)
        
        # Sort by most overdue first
        pending.sort(key=lambda x: x['follow_up_date'])
        
        return pending
    
    def mark_followed_up(self, app_id: str):
        """Mark an application as followed up"""
        schedule = self._load_schedule()
        
        if app_id in schedule:
            # Reschedule for another 3 days if no response
            follow_up_date = datetime.now() + timedelta(days=3)
            schedule[app_id]['follow_up_date'] = follow_up_date.isoformat()
            schedule[app_id]['last_follow_up'] = datetime.now().isoformat()
            
            self._save_schedule(schedule)
    
    def remove_from_schedule(self, app_id: str):
        """Remove application from follow-up schedule (got response)"""
        schedule = self._load_schedule()
        
        if app_id in schedule:
            del schedule[app_id]
            self._save_schedule(schedule)
    
    def get_follow_up_email_template(self, company: str, role: str, days_since: int) -> str:
        """
        Get follow-up email template
        
        Args:
            company: Company name
            role: Role title
            days_since: Days since application
            
        Returns:
            Email template
        """
        if days_since <= 3:
            # First follow-up (friendly check-in)
            return f"""Subject: Following up - {role} at {company}

Hi [Hiring Manager/Name],

I hope this email finds you well. I applied for the {role} position at {company} a few days ago and wanted to follow up to express my continued interest.

I'm particularly excited about this opportunity because [mention something specific about the company/role]. My experience building 6 production AI applications in 7 months and my background in both strategic leadership and hands-on engineering would allow me to contribute immediately.

If you'd like to see what I've built, you can try my AI assistant at wa.me/50766623757.

I'd love to discuss how I can help {company} achieve [their goal]. Would you be available for a brief call this week?

Best regards,
Elena Revicheva
aipa@aideazz.xyz | wa.me/50766623757 | aideazz.xyz"""
        
        elif days_since <= 7:
            # Second follow-up (value-add)
            return f"""Subject: Quick thought on {role} role at {company}

Hi [Name],

Following up on my application for {role}. I wanted to share a quick thought:

[Add something valuable - insight about their product, relevant article, or connection to their mission]

I've been working on similar challenges in my own projects (you can see live at wa.me/50766623757) and would love to discuss how my experience could help {company}.

Available for a call anytime this week or next.

Best regards,
Elena"""
        
        else:
            # Final follow-up (last attempt)
            return f"""Subject: Final follow-up - {role} at {company}

Hi [Name],

I wanted to reach out one last time regarding the {role} position. I understand you're likely busy, but I remain very interested in this opportunity.

If the role has been filled or if the timing isn't right, I completely understand. However, if you're still considering candidates, I'd love to discuss how my experience building AI products could add value to {company}.

Either way, I wish you and the team continued success!

Best regards,
Elena Revicheva
aipa@aideazz.xyz"""
    
    def get_follow_up_summary(self) -> Tuple[int, int, List[Dict]]:
        """
        Get summary of follow-up status
        
        Returns:
            (total_scheduled, overdue_count, overdue_list)
        """
        schedule = self._load_schedule()
        now = datetime.now()
        
        overdue = []
        for app_id, data in schedule.items():
            follow_up_date = datetime.fromisoformat(data['follow_up_date'])
            if follow_up_date <= now:
                days_overdue = (now - follow_up_date).days
                data['days_overdue'] = days_overdue
                data['app_id'] = app_id
                overdue.append(data)
        
        return len(schedule), len(overdue), overdue
    
    def _load_schedule(self) -> Dict:
        """Load follow-up schedule from file"""
        if not self.schedule_file.exists():
            return {}
        
        try:
            with open(self.schedule_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_schedule(self, schedule: Dict):
        """Save follow-up schedule to file"""
        with open(self.schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
