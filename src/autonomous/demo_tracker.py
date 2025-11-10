"""
🔥 DEMO TRACKER
Tracks clicks on Elena's demo link (wa.me/50766623757).
Identifies interested founders and triggers follow-ups.
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DemoTracker:
    """
    Tracks demo link engagement
    
    NOTE: Full implementation requires:
    - WhatsApp Business API for webhook tracking
    - Or a link shortener with click tracking (bit.ly, rebrandly)
    
    For now, provides framework and manual tracking capability
    """
    
    def __init__(self):
        self.clicks_file = Path("autonomous_data/demo_clicks.json")
        self.clicks_file.parent.mkdir(exist_ok=True)
        
        self.clicks = self._load_clicks()
        
        logger.info("🔥 Demo Tracker initialized")
    
    def _load_clicks(self) -> Dict[str, Any]:
        """Load click history"""
        if self.clicks_file.exists():
            try:
                with open(self.clicks_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load clicks: {e}")
        
        return {'clicks': [], 'engagement': []}
    
    def _save_clicks(self):
        """Save click history"""
        try:
            with open(self.clicks_file, 'w') as f:
                json.dump(self.clicks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save clicks: {e}")
    
    async def get_new_clicks(self, since_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get new demo clicks in last N minutes
        
        NOTE: This is a placeholder. Real implementation would:
        1. Query WhatsApp Business API for new conversations
        2. Or check link shortener analytics
        3. Or poll a tracking database
        """
        logger.info(f"🔍 Checking for demo clicks in last {since_minutes} minutes...")
        
        # For now, check manually logged clicks
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)
        
        new_clicks = [
            click for click in self.clicks.get('clicks', [])
            if datetime.fromisoformat(click['timestamp']) > cutoff_time
            and not click.get('processed', False)
        ]
        
        # Mark as processed
        for click in new_clicks:
            click['processed'] = True
        
        self._save_clicks()
        
        if new_clicks:
            logger.info(f"🔥 Found {len(new_clicks)} new demo clicks!")
        
        return new_clicks
    
    def log_demo_click(
        self,
        company: str,
        founder_name: str = None,
        source_channel: str = None,
        additional_info: Dict[str, Any] = None
    ):
        """
        Manually log a demo click
        
        Usage:
        - When you notice someone reached out after seeing the demo
        - When tracking link shows a click
        - When WhatsApp Business shows new conversation
        """
        click_data = {
            'company': company,
            'founder_name': founder_name,
            'source_channel': source_channel,
            'timestamp': datetime.now().isoformat(),
            'processed': False,
            'additional_info': additional_info or {}
        }
        
        self.clicks['clicks'].append(click_data)
        self._save_clicks()
        
        logger.info(f"🔥 Demo click logged for {company}")
    
    def log_engagement(
        self,
        company: str,
        engagement_type: str,  # 'demo_tried', 'long_session', 'multiple_messages'
        details: Dict[str, Any] = None
    ):
        """
        Log deeper engagement with the demo
        
        engagement_type:
        - 'demo_tried': Actually tested the AI
        - 'long_session': Spent >5 min with demo
        - 'multiple_messages': Sent multiple messages (real interest!)
        """
        engagement_data = {
            'company': company,
            'type': engagement_type,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self.clicks['engagement'].append(engagement_data)
        self._save_clicks()
        
        logger.info(f"💎 High engagement logged for {company}: {engagement_type}")
    
    def get_hot_leads(self, min_engagement_score: float = 50) -> List[Dict[str, Any]]:
        """
        Identify hot leads based on demo engagement
        
        Scoring:
        - Click demo link: 20 points
        - Try demo: 40 points
        - Long session (>5 min): 30 points
        - Multiple messages: 50 points
        - Responded after demo: 80 points
        """
        company_scores = {}
        
        # Score clicks
        for click in self.clicks.get('clicks', []):
            company = click['company']
            if company not in company_scores:
                company_scores[company] = {
                    'company': company,
                    'score': 0,
                    'signals': []
                }
            
            company_scores[company]['score'] += 20
            company_scores[company]['signals'].append(f"Clicked demo ({click.get('source_channel', 'unknown')} outreach)")
        
        # Score engagement
        for engagement in self.clicks.get('engagement', []):
            company = engagement['company']
            if company not in company_scores:
                continue
            
            engagement_type = engagement['type']
            
            if engagement_type == 'demo_tried':
                company_scores[company]['score'] += 40
                company_scores[company]['signals'].append("Actually tried the demo")
            elif engagement_type == 'long_session':
                company_scores[company]['score'] += 30
                company_scores[company]['signals'].append("Long session (>5 min)")
            elif engagement_type == 'multiple_messages':
                company_scores[company]['score'] += 50
                company_scores[company]['signals'].append("Multiple messages - HIGH INTEREST")
        
        # Filter hot leads
        hot_leads = [
            lead for lead in company_scores.values()
            if lead['score'] >= min_engagement_score
        ]
        
        # Sort by score
        hot_leads.sort(key=lambda x: x['score'], reverse=True)
        
        return hot_leads
    
    def get_stats(self) -> Dict[str, Any]:
        """Get demo tracking statistics"""
        total_clicks = len(self.clicks.get('clicks', []))
        total_engagement = len(self.clicks.get('engagement', []))
        
        # Count by channel
        by_channel = {}
        for click in self.clicks.get('clicks', []):
            channel = click.get('source_channel', 'unknown')
            by_channel[channel] = by_channel.get(channel, 0) + 1
        
        # Recent activity (last 7 days)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_clicks = [
            click for click in self.clicks.get('clicks', [])
            if datetime.fromisoformat(click['timestamp']) > recent_cutoff
        ]
        
        return {
            'total_clicks': total_clicks,
            'total_engagement_events': total_engagement,
            'clicks_by_channel': by_channel,
            'clicks_last_7_days': len(recent_clicks),
            'hot_leads': len(self.get_hot_leads()),
        }
    
    # Integration helpers
    
    def setup_tracking_link(self) -> str:
        """
        Generate a tracked demo link
        
        Options:
        1. Use bit.ly API with click tracking
        2. Use rebrandly API with custom domain
        3. Set up WhatsApp Business API webhooks
        4. Use UTM parameters: wa.me/50766623757?utm_source=autonomous&utm_campaign=outreach
        """
        # For now, return the base link
        # TODO: Implement link shortener integration
        
        return "wa.me/50766623757"
    
    async def poll_whatsapp_business_api(self):
        """
        Poll WhatsApp Business API for new conversations
        
        Requires:
        - WhatsApp Business API access
        - Webhook configuration
        - Or polling endpoint
        """
        # TODO: Implement WhatsApp Business API integration
        logger.info("WhatsApp Business API integration pending")
        pass
    
    def export_clicks_for_crm(self) -> List[Dict[str, Any]]:
        """Export clicks in CRM-friendly format"""
        export_data = []
        
        for click in self.clicks.get('clicks', []):
            export_data.append({
                'Company': click['company'],
                'Contact Name': click.get('founder_name', ''),
                'Source': click.get('source_channel', ''),
                'Date': click['timestamp'],
                'Status': 'Demo Clicked',
                'Next Action': 'Follow up within 24h',
            })
        
        return export_data
