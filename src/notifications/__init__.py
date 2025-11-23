"""
Notification system for VibeJobHunter
Sends real-time alerts via Telegram
"""

from .telegram_notifier import TelegramNotifier
from .linkedin_cmo_v4 import LinkedInCMO  # v4.0 AI CO-FOUNDER - Renamed to bust Railway cache!

__all__ = ["TelegramNotifier", "LinkedInCMO"]
