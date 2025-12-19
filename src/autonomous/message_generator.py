"""
✍️ MESSAGE GENERATOR
Generates hyper-personalized outreach messages for each channel.
Uses AI to create context-aware, compelling messages.

🆕 PHASE 2: Added generate_founder_message method
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
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
    
    🆕 PHASE 2: Now includes founder outreach message generation
    """
    
    def __init__(self, profile: Profile):
        from pathlib import Path
        self.profile = profile
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        logger.info("✍️ Message Generator initialized")
    
    # =========================================================================
    # 🆕 PHASE 2: FOUNDER MESSAGE GENERATION (NEW METHOD)
    # =========================================================================
    
    async def generate_founder_message(
        self,
        company: Dict[str, Any],
        job: Dict[str, Any],
        candidate_background: Optional[Dict] = None,
        ats_confirmation_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        🆕 PHASE 2: Generate personalized founder outreach message
        
        This method was MISSING and causing the error:
        'MessageGenerator' object has no attribute 'generate_founder_message'
        
        Args:
            company: Company info dict with name, founder_name, domain, etc.
            job: Job info dict with title, description, requirements
            candidate_background: Optional candidate info (uses self.profile if not provided)
            ats_confirmation_id: Optional ATS confirmation ID to reference
        
        Returns:
            Dict with 'subject' and 'body' keys
        """
        
        company_name = company.get('name', 'Your Company')
        founder_name = company.get('founder_name', company.get('founder_first_name', 'there'))
        job_title = job.get('title', 'the position')
        
        logger.info(f"✍️ Generating founder message for {company_name}...")
        
        # Check cache
        cache_key = f"founder_msg_{company_name.lower().replace(' ', '_')}_{job_title.lower().replace(' ', '_')}"
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"✅ Using cached founder message for {company_name}")
            return cached
        
        try:
            # Generate with Claude for best quality
            result = await self._generate_founder_message_with_claude(
                company, job, ats_confirmation_id
            )
            
            # Cache for 7 days
            self.cache.set(cache_key, result)
            
            logger.info(f"✅ Generated founder message for {company_name}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Claude generation failed: {e}, using template fallback")
            return self._generate_founder_message_template(company, job, ats_confirmation_id)
    
    async def _generate_founder_message_with_claude(
        self,
        company: Dict[str, Any],
        job: Dict[str, Any],
        ats_confirmation_id: Optional[str]
    ) -> Dict[str, str]:
        """Generate founder message using Claude API"""
        
        company_name = company.get('name', 'the company')
        founder_name = company.get('founder_name', company.get('founder_first_name', 'there'))
        job_title = job.get('title', 'the position')
        job_description = job.get('description', '')[:500]  # First 500 chars
        
        # Infer company focus from job/description
        focus_area = self._infer_company_focus(company, job)
        
        prompt = f"""Generate a founder outreach email for a job application.

COMPANY: {company_name}
FOUNDER: {founder_name}
JOB TITLE: {job_title}
COMPANY FOCUS: {focus_area}
JOB CONTEXT: {job_description}

CANDIDATE (Elena Revicheva):
• 2 LIVE AI agents with PAYING USERS in 19 countries
• Demo link: wa.me/50766623757 (instant credibility!)
• Built 6 production apps solo in 7 months
• Ex-CEO/CLO in E-Government (Russia) - led platform transformations
• Technical depth: Python, Claude, GPT, AI/ML, automation
• Cost optimization expert: 99%+ automation rate
• Bilingual: EN/ES, Web3 native
• Recent: 9 AI products shipped for <$15K

ATS STATUS: {"Application submitted (ID: " + ats_confirmation_id + ")" if ats_confirmation_id else "Application submitted via careers page"}

REQUIREMENTS:
1. Keep it under 150 words total
2. Reference something SPECIFIC about the company's work in {focus_area}
3. Mention that ATS application was submitted
4. Professional but warm, founder-to-founder tone
5. Highlight Elena's LIVE products (demo link) as proof
6. Don't ask for anything - just surface the strong fit
7. Subject line: insight-based, not "Application for X"

FORMAT:
Return JSON:
{{
  "subject": "compelling subject line",
  "body": "email body"
}}

CRITICAL: Make it feel personally researched and founder-to-founder, not applicant-to-employer!"""

        try:
            message = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = message.content[0].text.strip()
            
            # Parse JSON response
            import json
            if '{' in content and '}' in content:
                start = content.index('{')
                end = content.rindex('}') + 1
                json_str = content[start:end]
                result = json.loads(json_str)
                
                logger.info(f"✅ Claude generated founder message for {company_name}")
                return result
            else:
                raise ValueError("Could not parse Claude response as JSON")
        
        except Exception as e:
            logger.error(f"❌ Claude founder message generation failed: {e}")
            raise
    
    def _generate_founder_message_template(
        self,
        company: Dict[str, Any],
        job: Dict[str, Any],
        ats_confirmation_id: Optional[str]
    ) -> Dict[str, str]:
        """Fallback template-based generation"""
        
        company_name = company.get('name', 'your company')
        founder_name = company.get('founder_name', company.get('founder_first_name', 'there'))
        job_title = job.get('title', 'the position')
        focus_area = self._infer_company_focus(company, job)
        
        # Use different templates based on role type
        if any(kw in job_title.lower() for kw in ['ai', 'engineer', 'developer', 'technical', 'staff', 'senior']):
            subject = f"Re: {job_title} application—live AI demo"
            
            body = f"""Hi {founder_name},

Just submitted my application for {job_title} at {company_name}{"" if not ats_confirmation_id else f" (confirmation: {ats_confirmation_id})"}.

Instead of a traditional pitch, here's what I've built:
👉 wa.me/50766623757 (live AI agent, paying users, 19 countries)

Quick context:
• 2 live AI agents in production with revenue
• Built 6 AI products solo in 7 months
• Ex-CEO/CLO with platform transformation experience
• Deep in Python, Claude, AI/ML, automation
• Cost optimization: 99%+ via automation

Given {company_name}'s work in {focus_area}, thought there might be strong alignment beyond what a resume shows.

Happy to elaborate if useful.

Elena Revicheva
https://linkedin.com/in/elenarevicheva
https://aideazz.xyz"""
        
        elif any(kw in job_title.lower() for kw in ['product', 'manager', 'director', 'lead', 'vp']):
            subject = f"Quick thought on {company_name}'s {focus_area}"
            
            body = f"""Hi {founder_name},

Applied for {job_title} at {company_name} today.

While researching the role, I was particularly interested in {company_name}'s approach to {focus_area}.

What I've built that might be relevant:
• 2 live AI agents with paying users (try: wa.me/50766623757)
• Built solo, already generating revenue
• Ex-CEO/CLO background - led large-scale platform transformations

Not trying to bypass your process, just wanted to flag that there might be interesting alignment here.

Worth a conversation?

Elena Revicheva
https://linkedin.com/in/elenarevicheva"""
        
        else:
            subject = f"{job_title} application—founder context"
            
            body = f"""Hi {founder_name},

Just submitted my application for {job_title}.

Quick background:
• 2 live AI agents with paying users (wa.me/50766623757)
• Built 6 AI products in 7 months (solo, <$15K total cost)
• Ex-CEO/CLO - led platform transformations
• Technical: Python, AI/ML, automation, cost optimization
• Bilingual (EN/ES), Web3 native

I know you have a process—just wanted to make sure this doesn't get lost in the queue.

Thanks for building {company_name}.

Elena Revicheva
https://aideazz.xyz"""
        
        logger.info(f"✅ Template generated founder message for {company_name}")
        
        return {
            'subject': subject,
            'body': body
        }
    
    def _infer_company_focus(self, company: Dict, job: Dict) -> str:
        """Infer what the company focuses on"""
        
        text = (job.get('title', '') + ' ' + job.get('description', '')).lower()
        
        if 'ai' in text or 'machine learning' in text or 'ml' in text:
            return 'AI/ML infrastructure'
        elif 'developer' in text or 'productivity' in text:
            return 'developer productivity'
        elif 'infra' in text or 'platform' in text:
            return 'platform infrastructure'
        elif 'product' in text:
            return 'product development'
        else:
            return company.get('industry', 'technical innovation')
    
    # =========================================================================
    # EXISTING METHODS (unchanged)
    # =========================================================================
    
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
        self.cache.set(cache_key, messages)
        
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
                model="claude-sonnet-4-20250514",
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
                model="claude-sonnet-4-20250514",
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
                model="claude-sonnet-4-20250514",
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
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return f"Hi again! Just wanted to follow up. Still would love to chat about {company}. Demo: wa.me/50766623757"