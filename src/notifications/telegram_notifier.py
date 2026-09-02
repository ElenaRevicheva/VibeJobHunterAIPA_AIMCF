"""
📱 TELEGRAM NOTIFIER
Sends real-time notifications to your phone!

Get instant alerts for:
- 🔥 Hot jobs found (score >85)
- 💎 Demo clicks (someone tried your product!)
- 📧 Responses received
- 📅 Interviews scheduled
- 📊 Daily summary
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, time as dt_time
from pathlib import Path

from ..core.models import JobPosting, Profile
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramNotifier:
    """
    Telegram notification system for real-time job hunting alerts
    
    Uses POLLING mode for better Railway log visibility!
    
    Setup:
    1. Message @BotFather on Telegram
    2. Create a new bot: /newbot
    3. Get your bot token
    4. Start a chat with your bot
    5. Get your chat_id from @userinfobot
    6. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier with polling mode
        
        Args:
            bot_token: Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)
            chat_id: Your Telegram chat ID (or set TELEGRAM_CHAT_ID env var)
        """
        import os
        
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        self.enabled = bool(self.bot_token and self.chat_id)
        self.polling_task = None
        self.last_update_id = 0
        
        if self.enabled:
            # Import telegram library only if enabled
            try:
                from telegram import Bot, Update
                from telegram.error import TelegramError
                self.bot = Bot(token=self.bot_token)
                self.Update = Update
                self.TelegramError = TelegramError
                logger.info("📱 Telegram notifications ENABLED (polling mode)")
            except ImportError:
                logger.warning("⚠️ python-telegram-bot not installed. Run: pip install python-telegram-bot")
                self.enabled = False
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram bot: {e}")
                self.enabled = False
        else:
            logger.info("📱 Telegram notifications DISABLED (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable)")
        
        # Track sent notifications to avoid spam
        self.sent_today = 0
        self.last_daily_summary = None
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode (HTML or Markdown)
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Use async version of send_message
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            self.sent_today += 1
            logger.info(f"📱 Telegram notification sent ({self.sent_today} today)")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_notification(self, text: str) -> bool:
        """
        ✅ PHASE 2.5 FIX: Compatibility alias for send_notification
        Used by founder_finder_v2 for outreach notifications
        
        Args:
            text: Message text (supports HTML formatting)
        
        Returns:
            True if sent successfully
        """
        return await self.send_message(text)
    
    async def notify_hot_job(self, job: JobPosting) -> bool:
        """
        Notify about a hot job (score >85)
        
        🔥 HOT JOB ALERT!
        """
        if not self.enabled or job.match_score < 85:
            return False
        
        message = f"""🔥 <b>HOT JOB FOUND!</b> 🔥

<b>{job.title}</b> at <b>{job.company}</b>
📊 Match Score: <b>{job.match_score:.0f}/100</b>
📍 Location: {job.location}

<b>Why it's perfect:</b>
{self._format_reasons(job.match_reasons[:3])}

<b>Talking Points:</b>
{self._format_talking_points(job.talking_points[:3])}

🔗 Apply: {job.url}

💡 <i>Message generated and ready in autonomous_data/</i>
"""
        
        return await self.send_message(message)
    
    async def notify_demo_click(self, company: str, founder_name: str = None, source: str = None) -> bool:
        """
        Notify when someone clicks your demo link
        
        💎 DEMO CLICK ALERT!
        """
        if not self.enabled:
            return False
        
        founder_text = f" by {founder_name}" if founder_name else ""
        source_text = f" (via {source})" if source else ""
        
        message = f"""💎 <b>DEMO LINK CLICKED!</b> 💎

Someone from <b>{company}</b>{founder_text} just tried your demo{source_text}!

🎯 <b>This is a HOT LEAD!</b>

Next steps:
1. Check if they're still engaged
2. Send follow-up within 24h
3. Offer to schedule a call

🔗 Demo: wa.me/50766623757
"""
        
        return await self.send_message(message)
    
    async def notify_response_received(self, company: str, founder_name: str, sentiment: str = "positive") -> bool:
        """
        Notify when you receive a response
        
        📧 RESPONSE RECEIVED!
        """
        if not self.enabled:
            return False
        
        emoji_map = {
            'positive': '🎉',
            'neutral': '📧',
            'negative': '😐'
        }
        
        emoji = emoji_map.get(sentiment, '📧')
        
        message = f"""{emoji} <b>RESPONSE RECEIVED!</b>

<b>{founder_name}</b> from <b>{company}</b> replied!

Sentiment: <b>{sentiment.upper()}</b>

🎯 <b>Action required:</b> Check your email/LinkedIn and respond!

💡 <i>Use the talking points from autonomous_data/ for your reply</i>
"""
        
        return await self.send_message(message)
    
    async def notify_interview_scheduled(self, company: str, date: datetime, founder_name: str = None) -> bool:
        """
        Notify when an interview is scheduled
        
        📅 INTERVIEW SCHEDULED!
        """
        if not self.enabled:
            return False
        
        founder_text = f" with {founder_name}" if founder_name else ""
        date_str = date.strftime("%A, %B %d at %I:%M %p")
        
        message = f"""📅 <b>INTERVIEW SCHEDULED!</b> 📅

<b>{company}</b>{founder_text}

🗓️ <b>{date_str}</b>

📋 Prepare:
1. Review company research in autonomous_data/
2. Practice talking points
3. Demo ready: wa.me/50766623757
4. Set calendar reminder

🎯 <b>You've got this!</b> 💪
"""
        
        return await self.send_message(message)
    
    async def notify_cycle_complete(self, stats: Dict[str, int]) -> bool:
        """
        Notify when an autonomous cycle completes
        
        📊 CYCLE COMPLETE
        """
        if not self.enabled:
            return False
        
        message = f"""📊 <b>Cycle Complete</b>

✅ Jobs found: {stats.get('jobs_found', 0)}
✅ Companies researched: {stats.get('companies_researched', 0)}
✅ Messages generated: {stats.get('messages_sent', 0)}
✅ Demo clicks: {stats.get('demo_clicks', 0)}
✅ Responses: {stats.get('responses_received', 0)}

💡 <i>Check autonomous_data/ for new messages to send!</i>
"""
        
        return await self.send_message(message)
    
    async def send_daily_summary(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily summary at 8pm
        
        📊 DAILY SUMMARY
        """
        if not self.enabled:
            return False
        
        # Check if already sent today
        today = datetime.now().date()
        if self.last_daily_summary == today:
            return False
        
        message = f"""📊 <b>DAILY SUMMARY</b> - {today.strftime("%B %d, %Y")}

<b>Today's Activity:</b>
🔍 Jobs found: {stats.get('jobs_found', 0)}
🔬 Companies researched: {stats.get('companies_researched', 0)}
📤 Messages sent: {stats.get('messages_sent', 0)}
🔥 Demo clicks: {stats.get('demo_clicks', 0)}
📧 Responses: {stats.get('responses_received', 0)}
📅 Interviews scheduled: {stats.get('interviews_scheduled', 0)}

<b>Next Steps:</b>
1. Review hot leads in autonomous_data/
2. Send top 10 messages
3. Follow up on demo clicks
4. Prepare for upcoming interviews

🚀 <b>Keep crushing it!</b> 💪

---
🤖 VibeJobHunter running 24/7 on Railway
"""
        
        self.last_daily_summary = today
        return await self.send_message(message)
    
    async def notify_startup_success(self) -> bool:
        """
        Notify when autonomous engine starts successfully
        """
        if not self.enabled:
            return False
        
        message = f"""🚀 <b>AUTONOMOUS ENGINE STARTED!</b>

🤖 VibeJobHunter is now running 24/7!

You'll receive notifications for:
• 🔥 Hot jobs (score >85)
• 💎 Demo link clicks
• 📧 Responses from founders
• 📅 Interview scheduling
• 📊 Daily summaries (8pm)

💤 <b>Sit back and relax - the engine is working for you!</b>

---
📱 Want to pause? Just stop the Railway service.
"""
        
        return await self.send_message(message)
    
    async def notify_error(self, error_message: str) -> bool:
        """
        Notify about critical errors
        """
        if not self.enabled:
            return False
        
        # 2026-09-01: this said "Check Railway logs" for a year after the move to
        # Oracle. An alert that points at infrastructure which no longer exists costs
        # the reader the first minute of every incident, and quietly teaches them to
        # distrust the alert. The command below is the one that actually works.
        message = f"""⚠️ <b>ERROR ALERT</b>

Something went wrong with the autonomous engine:

<code>{error_message[:500]}</code>

🔧 Logs (Oracle, not Railway):
<code>sudo journalctl -u vibejobhunter -n 80 --no-pager</code>

💡 The engine will automatically retry on the next cycle.
"""
        
        return await self.send_message(message)
    
    # Helper methods
    
    def _format_reasons(self, reasons: List[str]) -> str:
        """Format match reasons as bullet points"""
        if not reasons:
            return "• High match score"
        return "\n".join([f"• {reason}" for reason in reasons])
    
    def _format_talking_points(self, points: List[str]) -> str:
        """Format talking points"""
        if not points:
            return "• Use your live demo: wa.me/50766623757"
        return "\n".join([f"• {point}" for point in points])
    
    async def _show_pending_outreach(self):
        """Show pending outreach messages from the manual queue"""
        try:
            queue_file = Path("autonomous_data/manual_outreach_queue.json")
            
            if not queue_file.exists():
                await self.send_message("📭 <b>No pending outreach messages</b>\n\nOutreach messages will appear here when generated.")
                return
            
            with open(queue_file, 'r') as f:
                queue = json.load(f)
            
            # Filter only pending messages
            pending = [m for m in queue if m.get('status') == 'pending_manual_send']
            
            if not pending:
                await self.send_message("✅ <b>All outreach messages sent!</b>\n\nNo pending messages in queue.")
                return
            
            # Show the most recent pending messages (max 3)
            for msg in pending[-3:]:
                channel = msg.get('channel', 'unknown').upper()
                company = msg.get('company', 'Unknown')
                contact = msg.get('contact', 'Contact')
                url = msg.get('url') or msg.get('handle', '')
                message_text = msg.get('message', '')
                
                outreach_msg = f"""📨 <b>Pending {channel} Outreach</b>

🏢 Company: {company}
👤 Contact: {contact}
🔗 Link: {url}

📝 <b>Full Message:</b>
<code>{message_text}</code>

<i>👆 Tap to copy, then send manually!</i>"""
                
                await self.send_message(outreach_msg)
            
            if len(pending) > 3:
                await self.send_message(f"📊 <i>Showing 3 of {len(pending)} pending messages</i>")
                
        except Exception as e:
            logger.error(f"❌ Error showing outreach: {e}")
            await self.send_message(f"❌ Error loading outreach queue: {e}")
    
    async def start_polling(self):
        """
        Start polling for incoming messages (for Railway log visibility)
        This runs in background and logs activity to Railway console
        """
        if not self.enabled:
            return
        
        logger.info("🔄 Starting Telegram polling (for Railway logs)...")
        
        while True:
            try:
                # Get updates from Telegram (async version)
                updates = await self.bot.get_updates(
                    offset=self.last_update_id + 1,
                    timeout=10,
                    allowed_updates=["message"]
                )
                
                for update in updates:
                    self.last_update_id = update.update_id
                    
                    if update.message and update.message.text:
                        # Log received messages in Railway
                        logger.info(f"📱 Telegram message received: {update.message.text}")
                        
                        # Handle simple commands
                        text = update.message.text.lower()
                        
                        if text == '/start':
                            await self.send_message("👋 <b>VibeJobHunter Bot Started!</b>\n\nYou'll receive job hunting notifications here!")
                        
                        elif text == '/status':
                            await self.send_message(f"🤖 <b>Bot Status:</b> Running\n📊 Messages sent today: {self.sent_today}")
                        
                        elif text == '/help':
                            await self.send_message("""📚 <b>Available Commands:</b>

/start - Start the bot
/status - Check bot status
/outreach - View pending outreach messages
/help - Show this help

The bot will automatically send you:
🔥 Hot jobs (score >85)
💎 Demo clicks
📧 Responses
📅 Interviews
📊 Daily summaries (8pm)""")
                        
                        elif text == '/outreach':
                            await self._show_pending_outreach()
                
                # Small delay between polls (Railway-friendly)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Telegram polling error: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def test_connection(self) -> bool:
        """
        Test Telegram connection
        
        Returns:
            True if connection works
        """
        if not self.enabled:
            logger.warning("Telegram not enabled")
            return False
        
        test_message = """✅ <b>Telegram Connected!</b>

Your VibeJobHunter notifications are working!

You'll receive real-time alerts for:
🔥 Hot jobs
💎 Demo clicks
📧 Responses
📅 Interviews
📊 Daily summaries

<b>Commands:</b>
/start - Start bot
/status - Check status
/help - Show help

<i>Test successful! Ready to find your dream job! 🚀</i>
"""
        
        success = await self.send_message(test_message)
        
        if success:
            logger.info("✅ Telegram test successful!")
        else:
            logger.error("❌ Telegram test failed")
        
        return success