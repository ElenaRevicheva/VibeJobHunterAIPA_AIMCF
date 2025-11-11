"""
✍️ MESSAGE GENERATOR
Generates hyper-personalized outreach messages for each channel.
Uses AI to create context-aware, compelling messages.
"""

import asyncio
import logging
from typing import Dict, Any, List
import anthropic
from datetime import datetime

from ..core.models import Profile
from ..core.config import settings
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

logger = setup_logger(__name__)


class MessageGenerator:
    """
    AI-powered message generation
    Creates personalized messages for LinkedIn, Email, and Twitter
    """
    
    def __init__(self, profile: Profile):
        from pathlib import Path
        self.profile = profile
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        logger.info("✍️ Message Generator initialized")
    
    async def generate_multi_channel_messages(
        self,
        founder_name: str,
        company: str,
        company_intel: Dict[str, Any],
        job_role: str
    ) -> Dict[str, str]:
        """
        Generate personalized messages for all channels
        Returns: {linkedin, email, twitter} messages
        """
        logger.info(f"✍️ Generating messages for {company}...")
        
        # Check cache
        cache_key = f"messages_{company.lower().replace(' ', '_')}_{job_role.lower().replace(' ', '_')}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✅ Using cached messages for {company}")
            return cached
        
        # Generate all messages in parallel
        tasks = [
            self._generate_linkedin_message(founder_name, company, company_intel, job_role),
            self._generate_email_message(founder_name, company, company_intel, job_role),
            self._generate_twitter_message(founder_name, company, company_intel, job_role),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        messages = {}
        for i, channel in enumerate(['linkedin', 'email', 'twitter']):
            if not isinstance(results[i], Exception):
                messages[channel] = results[i]
            else:
                logger.error(f"Failed to generate {channel} message: {results[i]}")
                messages[channel] = self._get_fallback_message(channel, founder_name, company)
        
        # Cache for 7 days
        self.cache.set(cache_key, messages, ttl=604800)
        
        logger.info(f"✅ Generated all messages for {company}")
        return messages
    
    async def _generate_linkedin_message(
        self,
        founder_name: str,
        company: str,
        company_intel: Dict[str, Any],
        job_role: str
    ) -> str:
        """
        Generate LinkedIn connection message
        LinkedIn limit: ~300 characters for initial message
        """
        
        context = self._build_context(company, company_intel, job_role)
        
        prompt = f"""Write a compelling LinkedIn connection request message for Elena.

ELENA'S UNIQUE STRENGTHS:
• 2 LIVE AI agents with PAYING USERS in 19 countries
• Demo link: wa.me/50766623757 (instant credibility!)
• Built 6 production apps solo in 7 months
• Bilingual EN/ES AI products
• Ex-CEO + hands-on AI engineer
• Web3 + AI expertise

TARGET:
Founder: {founder_name}
Company: {company}
Role: {job_role}

{context}

REQUIREMENTS:
1. Start with a compelling hook related to their company
2. Mention the LIVE DEMO link prominently
3. One specific value Elena brings
4. Keep it under 250 characters (LinkedIn limit)
5. Conversational, not salesy

CRITICAL: Make it feel like Elena personally researched them!

Write ONLY the message, no subject line."""

        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20240620",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"LinkedIn message generation failed: {e}")
            return self._get_fallback_message('linkedin', founder_name, company)
    
    async def _generate_email_message(
        self,
        founder_name: str,
        company: str,
        company_intel: Dict[str, Any],
        job_role: str
    ) -> str:
        """
        Generate email outreach
        More space for detail than LinkedIn
        """
        
        context = self._build_context(company, company_intel, job_role)
        
        prompt = f"""Write a compelling cold email for Elena to send to a startup founder.

ELENA'S UNIQUE STRENGTHS:
• 2 LIVE AI agents with PAYING USERS in 19 countries
• Demo: wa.me/50766623757 (they can try it NOW!)
• Revenue: PayPal Subscriptions active
• Speed: 6 production apps in 7 months solo
• Cost: 98% reduction vs traditional dev
• Tech: Claude, GPT, Whisper, TTS, ElizaOS
• Bilingual: EN/ES dual-sided market
• Background: Ex-CEO & CLO (strategic + technical)
• Web3: DAO design + tokenomics

TARGET:
To: {founder_name}
Company: {company}
Role: {job_role}

{context}

EMAIL STRUCTURE:
Subject: [Compelling, specific to their company]

Body:
1. HOOK: Reference something specific about their company (recent funding, product launch, or challenge)
2. DEMO: "Instead of sending my resume, try what I built: wa.me/50766623757"
3. TRACTION: Mention paying users, 19 countries, revenue
4. VALUE: One specific way Elena can help them
5. CTA: Soft ask for 15-min call

TONE: Confident but not arrogant, founder-to-founder

Write the complete email (subject + body)."""

        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20240620",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return self._get_fallback_message('email', founder_name, company)
    
    async def _generate_twitter_message(
        self,
        founder_name: str,
        company: str,
        company_intel: Dict[str, Any],
        job_role: str
    ) -> str:
        """
        Generate Twitter DM
        More casual than email/LinkedIn
        """
        
        context = self._build_context(company, company_intel, job_role)
        
        prompt = f"""Write a casual Twitter DM for Elena to send to a founder.

ELENA'S UNIQUE STRENGTHS:
• 2 live AI agents with paying users (wa.me/50766623757)
• Built solo, already generating revenue
• Ex-CEO turned AI builder
• Web3 + AI combo

TARGET:
Founder: {founder_name}
Company: {company}

{context}

REQUIREMENTS:
1. Super casual, Twitter-style tone
2. Start with their recent tweet/activity if known
3. Mention demo link naturally
4. Under 240 characters
5. Feel like a fellow founder DMing, not a job applicant

Write ONLY the DM text."""

        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20240620",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Twitter message generation failed: {e}")
            return self._get_fallback_message('twitter', founder_name, company)
    
    def _build_context(self, company: str, company_intel: Dict[str, Any], job_role: str) -> str:
        """Build context string from company intelligence"""
        context_parts = [f"They're hiring for: {job_role}"]
        
        # Add AI insights if available
        if 'ai_insights' in company_intel:
            insights = company_intel['ai_insights']
            if isinstance(insights, dict):
                if 'value_proposition' in insights:
                    context_parts.append(f"Company focus: {insights['value_proposition']}")
                if 'best_hook' in insights:
                    context_parts.append(f"Hook idea: {insights['best_hook']}")
        
        # Add keywords
        if 'website_data' in company_intel:
            keywords = company_intel['website_data'].get('keywords', [])
            if keywords:
                context_parts.append(f"Tech keywords: {', '.join(keywords[:5])}")
        
        return "\n".join(context_parts)
    
    def _get_fallback_message(self, channel: str, founder_name: str, company: str) -> str:
        """Fallback messages if AI generation fails"""
        
        fallbacks = {
            'linkedin': f"""Hi {founder_name},

Saw {company} is building in AI. I have 2 live AI agents with paying users in 19 countries.

Try it: wa.me/50766623757

Would love to connect!

- Elena""",
            
            'email': f"""Subject: Built something you might like - live AI demo

Hi {founder_name},

Instead of sending you my resume, I'll show you what I built:

👉 wa.me/50766623757

2 live AI agents, paying users in 19 countries, built solo in 7 months.

I saw {company} is hiring for AI roles. Would love to chat about how I can help you scale.

Quick intro:
• Ex-CEO turned AI engineer
• Built 6 production apps solo
• Claude, GPT, Whisper, ElizaOS
• Bilingual EN/ES products

Open for a 15-min call this week?

Best,
Elena Revicheva
📧 E-mail | 📱 WhatsApp | 🔗 aideazz.xyz""",
            
            'twitter': f"""Hey! Saw {company} is building cool AI stuff. I've got 2 live AI agents with paying users (wa.me/50766623757 - try it!). Would love to chat about how I can help! 🚀"""
        }
        
        return fallbacks.get(channel, f"Hi {founder_name}, would love to connect about {company}!")
    
    async def generate_follow_up_message(
        self,
        original_message: str,
        channel: str,
        days_since: int,
        company: str
    ) -> str:
        """
        Generate follow-up message
        """
        prompt = f"""Generate a follow-up message for Elena.

ORIGINAL MESSAGE (sent {days_since} days ago):
{original_message}

Channel: {channel}
Company: {company}

REQUIREMENTS:
1. Reference the original message subtly
2. Add NEW value (recent product update, new user milestone, etc.)
3. Keep it short and not pushy
4. Include demo link again: wa.me/50766623757
5. Soft CTA

Write ONLY the follow-up message."""

        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-5-sonnet-20240620",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return f"Hi again! Just wanted to follow up. Still would love to chat about {company}. Demo: wa.me/50766623757"
