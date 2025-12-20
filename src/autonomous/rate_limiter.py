"""
🛡️ RATE LIMITER FOR RESEND EMAILS
Protects your email reputation by enforcing strict limits.

Resend Limits:
- Free tier: 100 emails/day, 3000/month
- Paid tier: Higher limits but still rate-limited

OUR SAFETY LIMITS (conservative):
- Max 10 founder emails/day (protect reputation)
- Max 3 emails/hour (avoid spam detection)
- Track bounces and auto-disable on issues
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Safety limits
MAX_EMAILS_PER_DAY = int(os.getenv("MAX_EMAILS_PER_DAY", "10"))
MAX_EMAILS_PER_HOUR = int(os.getenv("MAX_EMAILS_PER_HOUR", "3"))
MAX_BOUNCES_BEFORE_DISABLE = int(os.getenv("MAX_BOUNCES_BEFORE_DISABLE", "3"))


@dataclass
class EmailStats:
    """Track email sending statistics"""
    total_sent: int = 0
    total_bounced: int = 0
    sent_today: int = 0
    sent_this_hour: int = 0
    last_sent_at: Optional[str] = None
    last_reset_date: Optional[str] = None
    last_reset_hour: Optional[str] = None
    disabled: bool = False
    disabled_reason: Optional[str] = None
    sent_emails: list = None  # Track individual emails
    
    def __post_init__(self):
        if self.sent_emails is None:
            self.sent_emails = []


class ResendRateLimiter:
    """
    Rate limiter for Resend email API.
    
    Usage:
        limiter = ResendRateLimiter()
        
        # Before sending
        can_send, reason = limiter.can_send_email("john@company.com")
        if not can_send:
            logger.warning(f"Rate limited: {reason}")
            return
        
        # After sending
        limiter.record_sent("john@company.com", "founder")
        
        # On bounce
        limiter.record_bounce("john@company.com")
    """
    
    def __init__(self, stats_file: str = "autonomous_data/email_stats.json"):
        self.stats_file = Path(stats_file)
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats = self._load_stats()
        self._check_resets()
        
        logger.info(f"🛡️ Rate Limiter initialized: {self.stats.sent_today}/{MAX_EMAILS_PER_DAY} today")
    
    def _load_stats(self) -> EmailStats:
        """Load stats from file"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    # Handle sent_emails being None or missing
                    if 'sent_emails' not in data or data['sent_emails'] is None:
                        data['sent_emails'] = []
                    return EmailStats(**data)
            except Exception as e:
                logger.warning(f"Failed to load email stats: {e}")
        return EmailStats()
    
    def _save_stats(self):
        """Save stats to file"""
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(asdict(self.stats), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save email stats: {e}")
    
    def _check_resets(self):
        """Reset counters if new day/hour"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_hour = now.strftime("%Y-%m-%d-%H")
        
        # Reset daily counter
        if self.stats.last_reset_date != today:
            logger.info(f"📅 New day - resetting daily email counter (was {self.stats.sent_today})")
            self.stats.sent_today = 0
            self.stats.last_reset_date = today
            self._save_stats()
        
        # Reset hourly counter
        if self.stats.last_reset_hour != current_hour:
            self.stats.sent_this_hour = 0
            self.stats.last_reset_hour = current_hour
            self._save_stats()
    
    def can_send_email(self, to_email: str) -> Tuple[bool, str]:
        """
        Check if we can send an email.
        
        Returns:
            (can_send: bool, reason: str)
        """
        self._check_resets()
        
        # Check if disabled
        if self.stats.disabled:
            return False, f"Email sending disabled: {self.stats.disabled_reason}"
        
        # Check daily limit
        if self.stats.sent_today >= MAX_EMAILS_PER_DAY:
            return False, f"Daily limit reached ({MAX_EMAILS_PER_DAY}/day)"
        
        # Check hourly limit
        if self.stats.sent_this_hour >= MAX_EMAILS_PER_HOUR:
            return False, f"Hourly limit reached ({MAX_EMAILS_PER_HOUR}/hour)"
        
        # Check if we already emailed this address today
        today = datetime.now().strftime("%Y-%m-%d")
        for email_record in self.stats.sent_emails:
            if email_record.get('email') == to_email and email_record.get('date') == today:
                return False, f"Already emailed {to_email} today"
        
        return True, "OK"
    
    def record_sent(self, to_email: str, email_type: str = "founder"):
        """Record a sent email"""
        self._check_resets()
        
        now = datetime.now()
        
        self.stats.total_sent += 1
        self.stats.sent_today += 1
        self.stats.sent_this_hour += 1
        self.stats.last_sent_at = now.isoformat()
        
        # Track individual emails (keep last 100)
        self.stats.sent_emails.append({
            'email': to_email,
            'type': email_type,
            'date': now.strftime("%Y-%m-%d"),
            'time': now.strftime("%H:%M:%S")
        })
        self.stats.sent_emails = self.stats.sent_emails[-100:]  # Keep last 100
        
        self._save_stats()
        
        remaining_today = MAX_EMAILS_PER_DAY - self.stats.sent_today
        remaining_hour = MAX_EMAILS_PER_HOUR - self.stats.sent_this_hour
        
        logger.info(f"📧 Email sent to {to_email} | Today: {self.stats.sent_today}/{MAX_EMAILS_PER_DAY} | This hour: {self.stats.sent_this_hour}/{MAX_EMAILS_PER_HOUR}")
        
        if remaining_today <= 2:
            logger.warning(f"⚠️ Only {remaining_today} emails remaining today!")
    
    def record_bounce(self, to_email: str):
        """Record a bounced email"""
        self.stats.total_bounced += 1
        
        logger.error(f"❌ BOUNCE recorded for {to_email} | Total bounces: {self.stats.total_bounced}")
        
        # Auto-disable if too many bounces
        if self.stats.total_bounced >= MAX_BOUNCES_BEFORE_DISABLE:
            self.stats.disabled = True
            self.stats.disabled_reason = f"Too many bounces ({self.stats.total_bounced})"
            logger.error(f"🚨 EMAIL SENDING DISABLED: {self.stats.disabled_reason}")
        
        self._save_stats()
    
    def get_status(self) -> Dict:
        """Get current rate limiting status"""
        self._check_resets()
        
        return {
            'enabled': not self.stats.disabled,
            'disabled_reason': self.stats.disabled_reason,
            'sent_today': self.stats.sent_today,
            'max_per_day': MAX_EMAILS_PER_DAY,
            'remaining_today': MAX_EMAILS_PER_DAY - self.stats.sent_today,
            'sent_this_hour': self.stats.sent_this_hour,
            'max_per_hour': MAX_EMAILS_PER_HOUR,
            'remaining_this_hour': MAX_EMAILS_PER_HOUR - self.stats.sent_this_hour,
            'total_sent': self.stats.total_sent,
            'total_bounced': self.stats.total_bounced,
            'bounce_rate': f"{(self.stats.total_bounced / max(1, self.stats.total_sent)) * 100:.1f}%"
        }
    
    def enable(self):
        """Re-enable email sending (after fixing issues)"""
        self.stats.disabled = False
        self.stats.disabled_reason = None
        self._save_stats()
        logger.info("✅ Email sending re-enabled")
    
    def reset_bounce_count(self):
        """Reset bounce count (use after fixing email issues)"""
        self.stats.total_bounced = 0
        self._save_stats()
        logger.info("✅ Bounce count reset to 0")


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> ResendRateLimiter:
    """Get singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ResendRateLimiter()
    return _rate_limiter


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("🧪 RATE LIMITER TEST")
    print("="*60)
    
    limiter = get_rate_limiter()
    
    # Check status
    status = limiter.get_status()
    print(f"\n📊 Current Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Test can_send
    test_email = "test@example.com"
    can_send, reason = limiter.can_send_email(test_email)
    print(f"\n📧 Can send to {test_email}? {can_send} ({reason})")
    
    print("\n✅ Rate limiter working!")
