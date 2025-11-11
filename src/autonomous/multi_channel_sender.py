"""
📤 MULTI-CHANNEL SENDER
Sends messages via LinkedIn, Email, and Twitter.
Tracks delivery and engagement.
"""

import asyncio
import logging
from typing import Dict, Any, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
from pathlib import Path

from ..core.config import settings
from ..utils.logger import setup_logger
from ..utils.rate_limiter import RateLimiter

logger = setup_logger(__name__)


class MultiChannelSender:
    """
    Sends messages across multiple channels
    Respects rate limits and tracks results
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter(max_calls=20, period=3600)  # 20 per hour
        self.sent_log_file = Path("autonomous_data/sent_messages.json")
        self.sent_log_file.parent.mkdir(exist_ok=True)
        
        # Load sent history
        self.sent_history = self._load_sent_history()
        
        logger.info("📤 Multi-Channel Sender initialized")
    
    def _load_sent_history(self) -> Dict[str, Any]:
        """Load history of sent messages"""
        if self.sent_log_file.exists():
            try:
                with open(self.sent_log_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load sent history: {e}")
        return {'messages': []}
    
    def _save_sent_history(self):
        """Save sent message history"""
        try:
            with open(self.sent_log_file, 'w') as f:
                json.dump(self.sent_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sent history: {e}")
    
    async def send_multi_channel(
        self,
        founder: Dict[str, Any],
        messages: Dict[str, str],
        company: str
    ) -> Dict[str, bool]:
        """
        Send message via all available channels
        Returns: {channel: success}
        """
        logger.info(f"📤 Sending multi-channel outreach to {company}...")
        
        # Check if already contacted recently
        if self._already_contacted_recently(company):
            logger.warning(f"⚠️ Already contacted {company} recently, skipping")
            return {'linkedin': False, 'email': False, 'twitter': False}
        
        # Respect rate limits
        await self.rate_limiter.acquire()
        
        # Send via all channels in parallel
        tasks = []
        channels = []
        
        if messages.get('linkedin') and founder.get('linkedin'):
            tasks.append(self._send_linkedin_message(founder, messages['linkedin'], company))
            channels.append('linkedin')
        
        if messages.get('email') and (founder.get('email') or founder.get('email_patterns')):
            tasks.append(self._send_email(founder, messages['email'], company))
            channels.append('email')
        
        if messages.get('twitter') and founder.get('twitter'):
            tasks.append(self._send_twitter_dm(founder, messages['twitter'], company))
            channels.append('twitter')
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        send_results = {}
        for i, channel in enumerate(channels):
            success = not isinstance(results[i], Exception) and results[i]
            send_results[channel] = success
            
            if success:
                logger.info(f"✅ {channel.upper()} message sent to {company}")
            else:
                error = results[i] if isinstance(results[i], Exception) else "Unknown error"
                logger.error(f"❌ {channel.upper()} failed for {company}: {error}")
        
        # Log sent message
        self._log_sent_message(company, founder, channels, send_results)
        
        return send_results
    
    def _already_contacted_recently(self, company: str, days: int = 14) -> bool:
        """Check if company was contacted in last N days"""
        for msg in self.sent_history.get('messages', []):
            if msg['company'].lower() == company.lower():
                sent_date = datetime.fromisoformat(msg['timestamp'])
                if (datetime.now() - sent_date).days < days:
                    return True
        return False
    
    async def _send_linkedin_message(
        self,
        founder: Dict[str, Any],
        message: str,
        company: str
    ) -> bool:
        """
        Send LinkedIn connection request with message
        
        NOTE: Real implementation requires Phantombuster or LinkedIn Sales Navigator API
        For now, this logs the message for manual sending
        """
        try:
            # TODO: Integrate Phantombuster API
            # For now, log for manual action
            
            linkedin_log = Path("autonomous_data/linkedin_queue.txt")
            linkedin_log.parent.mkdir(exist_ok=True)
            
            with open(linkedin_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Company: {company}\n")
                f.write(f"LinkedIn: {founder.get('linkedin', 'N/A')}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"\nMESSAGE:\n{message}\n")
                f.write(f"{'='*60}\n")
            
            logger.info(f"📝 LinkedIn message logged for {company} (manual action required)")
            
            # Return True since we successfully logged it
            return True
        
        except Exception as e:
            logger.error(f"LinkedIn logging failed: {e}")
            return False
    
    async def _send_email(
        self,
        founder: Dict[str, Any],
        message: str,
        company: str
    ) -> bool:
        """
        Send email via SMTP
        """
        try:
            # Check if email is configured
            if not settings.email_address or not settings.email_password:
                logger.warning("Email credentials not configured, logging for manual send")
                return await self._log_email_for_manual_send(founder, message, company)
            
            # Parse subject and body from message
            lines = message.split('\n')
            subject = lines[0].replace('Subject:', '').strip() if lines[0].startswith('Subject:') else f"Interested in {company}"
            body = '\n'.join(lines[1:]).strip() if lines[0].startswith('Subject:') else message
            
            # Get recipient email
            recipient = founder.get('email')
            if not recipient and founder.get('email_patterns'):
                # Use first pattern
                recipient = founder['email_patterns'][0]
            
            if not recipient:
                logger.error("No recipient email available")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = settings.email_address
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Send via SMTP
            await asyncio.to_thread(self._send_smtp, msg, recipient)
            
            logger.info(f"✅ Email sent to {recipient}")
            return True
        
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            # Log for manual send as fallback
            await self._log_email_for_manual_send(founder, message, company)
            return False
    
    def _send_smtp(self, msg: MIMEMultipart, recipient: str):
        """Send email via SMTP (synchronous)"""
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.email_address, settings.email_password)
            server.send_message(msg)
    
    async def _log_email_for_manual_send(
        self,
        founder: Dict[str, Any],
        message: str,
        company: str
    ) -> bool:
        """Log email for manual sending"""
        try:
            email_log = Path("autonomous_data/email_queue.txt")
            email_log.parent.mkdir(exist_ok=True)
            
            with open(email_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Company: {company}\n")
                f.write(f"To: {founder.get('email', founder.get('email_patterns', ['N/A'])[0])}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"\n{message}\n")
                f.write(f"{'='*60}\n")
            
            logger.info(f"📝 Email logged for {company} (manual action required)")
            return True
        
        except Exception as e:
            logger.error(f"Email logging failed: {e}")
            return False
    
    async def _send_twitter_dm(
        self,
        founder: Dict[str, Any],
        message: str,
        company: str
    ) -> bool:
        """
        Send Twitter DM
        
        NOTE: Requires Twitter API v2 with DM permissions
        For now, logs for manual sending
        """
        try:
            # TODO: Integrate Twitter API v2
            # For now, log for manual action
            
            twitter_log = Path("autonomous_data/twitter_queue.txt")
            twitter_log.parent.mkdir(exist_ok=True)
            
            with open(twitter_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Company: {company}\n")
                f.write(f"Twitter: {founder.get('twitter', 'N/A')}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"\nMESSAGE:\n{message}\n")
                f.write(f"{'='*60}\n")
            
            logger.info(f"📝 Twitter DM logged for {company} (manual action required)")
            return True
        
        except Exception as e:
            logger.error(f"Twitter logging failed: {e}")
            return False
    
    def _log_sent_message(
        self,
        company: str,
        founder: Dict[str, Any],
        channels: List[str],
        results: Dict[str, bool]
    ):
        """Log sent message to history"""
        self.sent_history['messages'].append({
            'company': company,
            'founder_name': founder.get('name', 'Unknown'),
            'channels': channels,
            'results': results,
            'timestamp': datetime.now().isoformat(),
        })
        
        # Keep only last 1000 messages
        if len(self.sent_history['messages']) > 1000:
            self.sent_history['messages'] = self.sent_history['messages'][-1000:]
        
        self._save_sent_history()
    
    def get_sent_stats(self) -> Dict[str, Any]:
        """Get statistics on sent messages"""
        total = len(self.sent_history.get('messages', []))
        
        channels = {'linkedin': 0, 'email': 0, 'twitter': 0}
        for msg in self.sent_history.get('messages', []):
            for channel, success in msg.get('results', {}).items():
                if success:
                    channels[channel] += 1
        
        return {
            'total_messages': total,
            'by_channel': channels,
        }
