"""
💼 LINKEDIN CMO (Chief Marketing Officer)
Automates LinkedIn content generation and posting via Make.com webhook!

Features:
- 🎯 Generates strategic LinkedIn posts
- 🌍 Multi-language support (English, Spanish)
- 🔄 Different post types (open_to_work, achievement, insight, question)
- 📊 Tracks post performance
- 🤖 Sends to Make.com for automated posting
"""

import asyncio
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class LinkedInCMO:
    """
    LinkedIn Content Management Officer
    
    Automates LinkedIn posting via Make.com webhook
    
    Setup:
    1. Create a Make.com account
    2. Create a scenario with webhook trigger
    3. Get your webhook URL
    4. Set MAKE_WEBHOOK_URL_LINKEDIN in .env
    
    Post Types:
    - open_to_work: Announce you're looking for opportunities
    - achievement: Share wins and milestones
    - insight: Share valuable insights from your experience
    - question: Engage your network with thoughtful questions
    - demo_share: Share your latest demo/project
    """
    
    def __init__(self, webhook_url: Optional[str] = None, language: str = "en"):
        """
        Initialize LinkedIn CMO
        
        Args:
            webhook_url: Make.com webhook URL (or set MAKE_WEBHOOK_URL_LINKEDIN env var)
            language: Default language for posts ('en' or 'es')
        """
        import os
        
        self.webhook_url = webhook_url or os.getenv('MAKE_WEBHOOK_URL_LINKEDIN')
        self.language = language
        self.enabled = bool(self.webhook_url)
        
        if self.enabled:
            logger.info("💼 LinkedIn CMO ENABLED - Ready to generate content!")
        else:
            logger.info("💼 LinkedIn CMO DISABLED (set MAKE_WEBHOOK_URL_LINKEDIN to enable)")
        
        # Track posts
        self.posts_sent = 0
        self.last_post_date = None
        
        # Content templates
        self.templates = {
            'en': {
                'open_to_work': [
                    "🚀 I'm looking for my next opportunity as a {role}!\n\n"
                    "After {experience}, I'm excited to join a mission-driven startup where I can:\n"
                    "✅ {skill_1}\n"
                    "✅ {skill_2}\n"
                    "✅ {skill_3}\n\n"
                    "What I bring:\n"
                    "💡 {strength_1}\n"
                    "💡 {strength_2}\n"
                    "💡 {strength_3}\n\n"
                    "🎯 Looking for: {ideal_role}\n"
                    "📍 Location: {location}\n"
                    "🔗 Check out my demo: {demo_link}\n\n"
                    "Know a great opportunity? Let's connect!\n\n"
                    "#OpenToWork #Hiring #TechJobs #{role_hashtag}",
                    
                    "💼 Open to new opportunities!\n\n"
                    "I'm a {role} passionate about {passion}.\n\n"
                    "Recent highlights:\n"
                    "🎯 {achievement_1}\n"
                    "🎯 {achievement_2}\n"
                    "🎯 {achievement_3}\n\n"
                    "Ideal next role:\n"
                    "• {ideal_1}\n"
                    "• {ideal_2}\n"
                    "• {ideal_3}\n\n"
                    "👉 See what I've built: {demo_link}\n\n"
                    "Let's talk if you know a great fit!\n\n"
                    "#OpenToWork #{role_hashtag} #StartupJobs",
                ],
                'achievement': [
                    "🎉 Exciting milestone!\n\n"
                    "{achievement_description}\n\n"
                    "Key learnings:\n"
                    "1️⃣ {learning_1}\n"
                    "2️⃣ {learning_2}\n"
                    "3️⃣ {learning_3}\n\n"
                    "What helped most: {key_factor}\n\n"
                    "Check it out: {demo_link}\n\n"
                    "#{topic_1} #{topic_2} #{topic_3}",
                ],
                'insight': [
                    "💡 Insight from building {project}:\n\n"
                    "{main_insight}\n\n"
                    "Why it matters:\n"
                    "→ {reason_1}\n"
                    "→ {reason_2}\n"
                    "→ {reason_3}\n\n"
                    "What are your thoughts?\n\n"
                    "#{topic_1} #{topic_2} #TechInsights",
                ],
                'question': [
                    "🤔 Question for my network:\n\n"
                    "{question}\n\n"
                    "Context: {context}\n\n"
                    "I'm curious because {reason}\n\n"
                    "What's your take?\n\n"
                    "#{topic_1} #{topic_2}",
                ],
                'demo_share': [
                    "🚀 Just shipped: {project_name}!\n\n"
                    "{description}\n\n"
                    "Built with:\n"
                    "🔧 {tech_1}\n"
                    "🔧 {tech_2}\n"
                    "🔧 {tech_3}\n\n"
                    "Why I built this: {motivation}\n\n"
                    "Try it: {demo_link}\n\n"
                    "Feedback welcome!\n\n"
                    "#{topic_1} #{topic_2} #{topic_3}",
                ],
            },
            'es': {
                'open_to_work': [
                    "🚀 ¡Busco mi próxima oportunidad como {role}!\n\n"
                    "Después de {experience}, estoy emocionado/a por unirme a una startup con misión donde pueda:\n"
                    "✅ {skill_1}\n"
                    "✅ {skill_2}\n"
                    "✅ {skill_3}\n\n"
                    "Lo que aporto:\n"
                    "💡 {strength_1}\n"
                    "💡 {strength_2}\n"
                    "💡 {strength_3}\n\n"
                    "🎯 Busco: {ideal_role}\n"
                    "📍 Ubicación: {location}\n"
                    "🔗 Mira mi demo: {demo_link}\n\n"
                    "¿Conoces una gran oportunidad? ¡Conectemos!\n\n"
                    "#BuscoEmpleo #Contratación #TechJobs #{role_hashtag}",
                ],
                'achievement': [
                    "🎉 ¡Hito emocionante!\n\n"
                    "{achievement_description}\n\n"
                    "Aprendizajes clave:\n"
                    "1️⃣ {learning_1}\n"
                    "2️⃣ {learning_2}\n"
                    "3️⃣ {learning_3}\n\n"
                    "Lo que más ayudó: {key_factor}\n\n"
                    "Échale un vistazo: {demo_link}\n\n"
                    "#{topic_1} #{topic_2} #{topic_3}",
                ],
                'insight': [
                    "💡 Aprendizaje construyendo {project}:\n\n"
                    "{main_insight}\n\n"
                    "Por qué importa:\n"
                    "→ {reason_1}\n"
                    "→ {reason_2}\n"
                    "→ {reason_3}\n\n"
                    "¿Qué opinan?\n\n"
                    "#{topic_1} #{topic_2} #TechInsights",
                ],
                'question': [
                    "🤔 Pregunta para mi red:\n\n"
                    "{question}\n\n"
                    "Contexto: {context}\n\n"
                    "Me interesa porque {reason}\n\n"
                    "¿Cuál es tu opinión?\n\n"
                    "#{topic_1} #{topic_2}",
                ],
                'demo_share': [
                    "🚀 ¡Acabo de lanzar: {project_name}!\n\n"
                    "{description}\n\n"
                    "Construido con:\n"
                    "🔧 {tech_1}\n"
                    "🔧 {tech_2}\n"
                    "🔧 {tech_3}\n\n"
                    "Por qué lo construí: {motivation}\n\n"
                    "Pruébalo: {demo_link}\n\n"
                    "¡Feedback bienvenido!\n\n"
                    "#{topic_1} #{topic_2} #{topic_3}",
                ],
            }
        }
    
    def generate_linkedin_post(
        self, 
        post_type: str = "open_to_work",
        language: Optional[str] = None,
        **variables
    ) -> Dict[str, Any]:
        """
        Generate a LinkedIn post
        
        Args:
            post_type: Type of post (open_to_work, achievement, insight, question, demo_share)
            language: Language code ('en' or 'es'), defaults to self.language
            **variables: Template variables (role, experience, skills, etc.)
        
        Returns:
            Dict with 'content', 'type', 'language', and 'timestamp'
        """
        lang = language or self.language
        
        if lang not in self.templates:
            logger.warning(f"Language {lang} not supported, falling back to 'en'")
            lang = 'en'
        
        if post_type not in self.templates[lang]:
            logger.warning(f"Post type {post_type} not found, using 'open_to_work'")
            post_type = 'open_to_work'
        
        # Get random template for variety
        import random
        templates = self.templates[lang][post_type]
        template = random.choice(templates)
        
        # Fill in variables (with defaults)
        default_variables = {
            'role': 'Founding Engineer',
            'experience': 'building AI-powered automation tools',
            'skill_1': 'Build and scale products from 0→1',
            'skill_2': 'Lead technical architecture decisions',
            'skill_3': 'Ship fast with high quality',
            'strength_1': 'Full-stack expertise (Python, React, AI/ML)',
            'strength_2': 'Product-minded engineering approach',
            'strength_3': 'Startup experience & hustle mentality',
            'ideal_role': 'Founding Engineer at early-stage startup',
            'location': 'Remote / San Francisco Bay Area',
            'demo_link': 'https://wa.me/50766623757',
            'role_hashtag': 'FoundingEngineer',
            'passion': 'building products that solve real problems',
            'achievement_1': 'Built AI job hunting automation',
            'achievement_2': 'Scaled WhatsApp AI assistant',
            'achievement_3': 'Shipped products used by thousands',
            'ideal_1': 'Work directly with founders',
            'ideal_2': 'Meaningful equity stake',
            'ideal_3': 'High impact from day one',
            'achievement_description': 'Successfully built and launched an AI-powered automation system!',
            'learning_1': 'Start with MVP, iterate fast',
            'learning_2': 'User feedback is gold',
            'learning_3': 'Ship early, ship often',
            'key_factor': 'Focus on solving real user pain points',
            'project': 'my latest project',
            'main_insight': 'Sometimes the simplest solution is the best one.',
            'reason_1': 'Saves time and effort',
            'reason_2': 'Easier to maintain and debug',
            'reason_3': 'Users actually understand it',
            'topic_1': 'Tech',
            'topic_2': 'Startups',
            'topic_3': 'Engineering',
            'question': 'What\'s your biggest challenge when hiring technical talent?',
            'context': 'I\'m exploring the hiring landscape',
            'reason': 'I want to understand what founders struggle with',
            'project_name': 'My Latest Project',
            'description': 'An AI-powered tool that automates job searching and applications.',
            'tech_1': 'Python',
            'tech_2': 'OpenAI API',
            'tech_3': 'Telegram Bot',
            'motivation': 'I wanted to help people find their dream jobs faster',
        }
        
        # Merge with provided variables
        all_variables = {**default_variables, **variables}
        
        # Format template
        try:
            content = template.format(**all_variables)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            content = template  # Return unformatted if error
        
        return {
            'content': content,
            'type': post_type,
            'language': lang,
            'timestamp': datetime.now().isoformat(),
            'character_count': len(content)
        }
    
    async def send_to_linkedin(self, post: Dict[str, Any]) -> bool:
        """
        Send post to LinkedIn via Make.com webhook
        
        Args:
            post: Post dictionary from generate_linkedin_post()
        
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.warning("LinkedIn CMO not enabled (no webhook URL)")
            return False
        
        try:
            # Send to Make.com webhook
            response = requests.post(
                self.webhook_url,
                json=post,
                timeout=10
            )
            
            if response.status_code == 200:
                self.posts_sent += 1
                self.last_post_date = datetime.now()
                logger.info(f"✅ LinkedIn post sent via Make.com ({self.posts_sent} posts sent)")
                return True
            else:
                logger.error(f"Failed to send LinkedIn post: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending LinkedIn post to Make.com: {e}")
            return False
    
    async def post_open_to_work(self, **variables) -> bool:
        """
        Quick method: Generate and post "open to work" announcement
        
        Usage:
            await cmo.post_open_to_work(
                role="Founding Engineer",
                experience="building AI tools for 3 years",
                demo_link="https://wa.me/50766623757"
            )
        """
        post = self.generate_linkedin_post('open_to_work', **variables)
        return await self.send_to_linkedin(post)
    
    async def post_achievement(self, **variables) -> bool:
        """
        Quick method: Generate and post achievement
        
        Usage:
            await cmo.post_achievement(
                achievement_description="Launched my AI job hunting tool!",
                demo_link="https://wa.me/50766623757"
            )
        """
        post = self.generate_linkedin_post('achievement', **variables)
        return await self.send_to_linkedin(post)
    
    async def post_insight(self, **variables) -> bool:
        """
        Quick method: Generate and post insight
        
        Usage:
            await cmo.post_insight(
                project="an AI automation tool",
                main_insight="AI can save you 10+ hours per week on repetitive tasks"
            )
        """
        post = self.generate_linkedin_post('insight', **variables)
        return await self.send_to_linkedin(post)
    
    async def post_demo(self, **variables) -> bool:
        """
        Quick method: Generate and post demo share
        
        Usage:
            await cmo.post_demo(
                project_name="VibeJobHunter",
                description="AI-powered job search automation",
                demo_link="https://wa.me/50766623757"
            )
        """
        post = self.generate_linkedin_post('demo_share', **variables)
        return await self.send_to_linkedin(post)
    
    async def schedule_weekly_posts(self, schedule: List[Dict[str, Any]]) -> bool:
        """
        Schedule a week's worth of LinkedIn posts
        
        Args:
            schedule: List of post configs, e.g.:
                [
                    {'day': 'Monday', 'post_type': 'open_to_work', 'variables': {...}},
                    {'day': 'Wednesday', 'post_type': 'insight', 'variables': {...}},
                    {'day': 'Friday', 'post_type': 'demo_share', 'variables': {...}}
                ]
        
        Returns:
            True if scheduling request sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Generate all posts
            posts = []
            for item in schedule:
                post = self.generate_linkedin_post(
                    item.get('post_type', 'open_to_work'),
                    **item.get('variables', {})
                )
                post['scheduled_day'] = item.get('day', 'Monday')
                posts.append(post)
            
            # Send to Make.com webhook with schedule flag
            response = requests.post(
                self.webhook_url,
                json={
                    'action': 'schedule_weekly',
                    'posts': posts
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Scheduled {len(posts)} LinkedIn posts for the week")
                return True
            else:
                logger.error(f"Failed to schedule posts: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error scheduling LinkedIn posts: {e}")
            return False
    
    def preview_post(self, post_type: str = "open_to_work", language: Optional[str] = None, **variables) -> str:
        """
        Preview a post without sending
        
        Args:
            post_type: Type of post
            language: Language code
            **variables: Template variables
        
        Returns:
            Formatted post content
        """
        post = self.generate_linkedin_post(post_type, language, **variables)
        return post['content']
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get LinkedIn CMO statistics
        
        Returns:
            Dict with posts_sent, last_post_date, enabled
        """
        return {
            'posts_sent': self.posts_sent,
            'last_post_date': self.last_post_date.isoformat() if self.last_post_date else None,
            'enabled': self.enabled,
            'webhook_configured': bool(self.webhook_url)
        }
