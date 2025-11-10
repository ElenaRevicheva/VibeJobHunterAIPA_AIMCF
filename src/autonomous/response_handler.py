"""
📧 RESPONSE HANDLER
Monitors responses and auto-schedules interviews.
Handles follow-ups and manages conversation flow.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..core.models import Profile
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ResponseHandler:
    """
    Handles responses and automates next steps
    
    Features:
    - Monitor email/LinkedIn for responses
    - Auto-schedule interviews
    - Send follow-ups
    - Track conversation state
    """
    
    def __init__(self, profile: Profile):
        self.profile = profile
        self.responses_file = Path("autonomous_data/responses.json")
        self.responses_file.parent.mkdir(exist_ok=True)
        
        self.responses = self._load_responses()
        
        logger.info("📧 Response Handler initialized")
    
    def _load_responses(self) -> Dict[str, Any]:
        """Load response history"""
        if self.responses_file.exists():
            try:
                with open(self.responses_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load responses: {e}")
        
        return {'responses': [], 'interviews': []}
    
    def _save_responses(self):
        """Save response history"""
        try:
            with open(self.responses_file, 'w') as f:
                json.dump(self.responses, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save responses: {e}")
    
    async def check_responses(self) -> List[Dict[str, Any]]:
        """
        Check for new responses
        
        NOTE: Full implementation requires:
        - Email IMAP access to check inbox
        - LinkedIn API to check messages
        - Twitter API to check DMs
        
        For now, provides manual logging capability
        """
        logger.info("📧 Checking for responses...")
        
        # TODO: Implement email checking via IMAP
        # TODO: Implement LinkedIn message checking
        # TODO: Implement Twitter DM checking
        
        # For now, return manually logged responses
        new_responses = [
            resp for resp in self.responses.get('responses', [])
            if not resp.get('processed', False)
        ]
        
        # Mark as processed
        for resp in new_responses:
            resp['processed'] = True
        
        self._save_responses()
        
        if new_responses:
            logger.info(f"✅ Found {len(new_responses)} new responses!")
        
        return new_responses
    
    def log_response(
        self,
        company: str,
        founder_name: str,
        response_text: str,
        channel: str,  # 'email', 'linkedin', 'twitter'
        sentiment: str = 'positive'  # 'positive', 'neutral', 'negative'
    ):
        """
        Manually log a response
        
        Usage:
        - When you receive an email reply
        - When founder responds on LinkedIn
        - When you get a Twitter DM back
        """
        response_data = {
            'company': company,
            'founder_name': founder_name,
            'response_text': response_text,
            'channel': channel,
            'sentiment': sentiment,
            'timestamp': datetime.now().isoformat(),
            'processed': False,
        }
        
        self.responses['responses'].append(response_data)
        self._save_responses()
        
        logger.info(f"📧 Response logged from {company} ({sentiment})")
    
    async def auto_schedule_interviews(
        self,
        responses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Auto-schedule interviews from positive responses
        
        Looks for:
        - "Let's schedule a call"
        - "Are you available for"
        - "Would you like to chat"
        
        Actions:
        - Send calendar link
        - Propose time slots
        - Create calendar event
        """
        interviews = []
        
        for response in responses:
            # Check if response indicates interest in call
            if self._indicates_interview_interest(response):
                interview = await self._create_interview_proposal(response)
                if interview:
                    interviews.append(interview)
                    self.responses['interviews'].append(interview)
        
        self._save_responses()
        
        return interviews
    
    def _indicates_interview_interest(self, response: Dict[str, Any]) -> bool:
        """Check if response indicates interest in scheduling a call"""
        text = response.get('response_text', '').lower()
        
        interest_keywords = [
            'schedule', 'call', 'chat', 'meeting', 'available',
            'time to talk', 'quick call', 'interview', 'discuss'
        ]
        
        return any(keyword in text for keyword in interest_keywords)
    
    async def _create_interview_proposal(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create interview proposal response
        """
        try:
            company = response['company']
            founder_name = response['founder_name']
            channel = response['channel']
            
            # Generate response with calendar options
            proposal = {
                'company': company,
                'founder_name': founder_name,
                'channel': channel,
                'timestamp': datetime.now().isoformat(),
                'status': 'proposed',
                'availability_slots': self._generate_availability_slots(),
                'calendar_link': 'https://calendly.com/elena-aideazz',  # TODO: Configure real calendar
            }
            
            # Generate response message
            response_message = self._generate_scheduling_response(proposal)
            proposal['response_message'] = response_message
            
            # Log for manual sending
            await self._log_interview_response(proposal)
            
            logger.info(f"📅 Interview proposal created for {company}")
            return proposal
        
        except Exception as e:
            logger.error(f"Failed to create interview proposal: {e}")
            return None
    
    def _generate_availability_slots(self) -> List[Dict[str, str]]:
        """Generate next available time slots"""
        slots = []
        
        # Generate next 5 business days, 2 slots per day
        current_date = datetime.now()
        
        for i in range(10):
            slot_date = current_date + timedelta(days=i)
            
            # Skip weekends
            if slot_date.weekday() >= 5:
                continue
            
            # Morning slot: 10am
            morning = slot_date.replace(hour=10, minute=0, second=0)
            slots.append({
                'datetime': morning.isoformat(),
                'display': morning.strftime('%A, %B %d at %I:%M %p EST')
            })
            
            # Afternoon slot: 2pm
            afternoon = slot_date.replace(hour=14, minute=0, second=0)
            slots.append({
                'datetime': afternoon.isoformat(),
                'display': afternoon.strftime('%A, %B %d at %I:%M %p EST')
            })
            
            if len(slots) >= 6:
                break
        
        return slots[:6]
    
    def _generate_scheduling_response(self, proposal: Dict[str, Any]) -> str:
        """Generate response message for scheduling"""
        founder_name = proposal['founder_name']
        slots = proposal['availability_slots']
        
        message = f"""Hi {founder_name},

Great to hear from you! I'd love to chat.

I'm available:
"""
        
        for i, slot in enumerate(slots[:3], 1):
            message += f"{i}. {slot['display']}\n"
        
        message += f"""
Or pick any time that works for you: {proposal['calendar_link']}

Looking forward to it!

Elena"""
        
        return message
    
    async def _log_interview_response(self, proposal: Dict[str, Any]):
        """Log interview response for sending"""
        log_file = Path(f"autonomous_data/{proposal['channel']}_responses.txt")
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Company: {proposal['company']}\n")
            f.write(f"To: {proposal['founder_name']}\n")
            f.write(f"Timestamp: {proposal['timestamp']}\n")
            f.write(f"\nRESPONSE:\n{proposal['response_message']}\n")
            f.write(f"{'='*60}\n")
    
    async def send_follow_ups(self):
        """
        Send follow-up messages for cold outreach
        
        Follow-up schedule:
        - Day 3: Soft follow-up
        - Day 7: Value-add follow-up
        - Day 14: Final follow-up
        """
        logger.info("📨 Checking for follow-ups to send...")
        
        # TODO: Implement follow-up logic
        # - Check sent messages
        # - Identify those without responses
        # - Send appropriate follow-up based on days since
        
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get response statistics"""
        total_responses = len(self.responses.get('responses', []))
        
        # Count by sentiment
        by_sentiment = {'positive': 0, 'neutral': 0, 'negative': 0}
        for resp in self.responses.get('responses', []):
            sentiment = resp.get('sentiment', 'neutral')
            by_sentiment[sentiment] += 1
        
        # Count interviews
        total_interviews = len(self.responses.get('interviews', []))
        scheduled = len([i for i in self.responses.get('interviews', []) if i.get('status') == 'scheduled'])
        
        return {
            'total_responses': total_responses,
            'by_sentiment': by_sentiment,
            'total_interviews': total_interviews,
            'scheduled_interviews': scheduled,
            'response_rate': f"{(total_responses / max(1, total_responses)) * 100:.1f}%",
        }
    
    async def monitor_inbox_loop(self, check_interval_minutes: int = 15):
        """
        Continuously monitor inbox for responses
        """
        logger.info(f"📧 Starting inbox monitoring (every {check_interval_minutes} min)")
        
        while True:
            try:
                responses = await self.check_responses()
                
                if responses:
                    # Auto-schedule interviews
                    interviews = await self.auto_schedule_interviews(responses)
                    logger.info(f"📅 {len(interviews)} interviews proposed")
                
                # Wait before next check
                await asyncio.sleep(check_interval_minutes * 60)
            
            except Exception as e:
                logger.error(f"Inbox monitoring error: {e}")
                await asyncio.sleep(60)
