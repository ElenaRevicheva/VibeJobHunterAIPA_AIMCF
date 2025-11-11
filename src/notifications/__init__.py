"""
Notification system for VibeJobHunter
Sends real-time alerts via Telegram
"""

from .telegram_notifier import TelegramNotifier

__all__ = ["TelegramNotifier"]
