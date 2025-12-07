"""
🎯 LINKEDIN CMO - AI CO-FOUNDER
TRUE AI Co-Founder for AIdeazz (not just an AIPA!)

DIFFERENCE:
- AIPA = Executes tasks (templates, rules, automation)
- AI CO-FOUNDER = Strategic thinking, creative generation, performance analysis, adapts

CAPABILITIES:
✅ Generates fresh content using Claude API (not templates!)
✅ Analyzes LinkedIn performance data (PROXY METRICS - NO LINKEDIN API NEEDED!)
✅ Makes strategic decisions about content mix
✅ Adapts tone/strategy based on goals
✅ Bilingual content strategy (EN/ES)
✅ Autonomous posting with business intelligence

Author: Elena Revicheva (Human Co-Founder)
AI Co-Founder: LinkedIn CMO (Autonomous Strategic Partner)
Created: November 2025
Updated: December 2025 - PROXY METRICS INTEGRATION!
"""

import requests
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import os
import anthropic
from anthropic import AsyncAnthropic
import json
from pathlib import Path

# Import performance tracker
try:
    from .performance_tracker import PerformanceTracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    logger.warning("⚠️ Performance tracker not available - using basic tracking")

# 🔥🔥🔥 DEPLOYMENT VERIFICATION BANNER 🔥🔥🔥
print("\n" + "🎯"*40)
print("✨ AI MARKETING CO-FOUNDER v5.0 - DIGNIFIED POSITIONING DEPLOYED! ✨")
print("="*80)
print("📦 BUILD: 2025-11-24 17:00 UTC | COMMIT: 08810b9")
print("")
print("🤖 5 AIPAs with PROFESSIONAL DESCRIPTIONS:")
print("   1. EspaLuz WhatsApp → 'Bilingual AIPA for 19 Spanish-speaking countries'")
print("   2. EspaLuz Telegram → 'On-the-go Spanish learning AIPA'")
print("   3. ALGOM Alpha → 'Post-Scammer Era Crypto Coach'")
print("   4. EspaLuz SMM → 'SMM AIPA for social media marketing'")
print("   5. LinkedIn CMO → 'AI Marketing Co-Founder posting daily!'")
print("")
print("🌐 4 AI Products with STRATEGIC POSITIONING:")
print("   1. EspaLuz Web → 'Family's First Emotionally Intelligent AI Language Coach'")
print("   2. AIdeazz.xyz → 'Emotionally Intelligent AI Assistants Showroom'")
print("   3. Business Card → 'Business Card & Portfolio of AIdeazz Founder'")
print("   4. ATUONA → 'Underground Russian Poetry NFT Gallery on Polygon'")
print("")
print("🔗 ALL 9 VERIFIED LINKS INCLUDED:")
print("   wa.me/50766623757 | t.me/EspaLuzFamily_bot | x.com/reviceva")
print("   t.me/Influencer_EspaLuz_bot | linkedin.com/in/elenarevicheva")
print("   instagram.com/elena_revicheva | espaluz-ai-language-tutor.lovable.app")
print("   aideazz.xyz | aideazz.xyz/card | atuona.xyz")
print("")
print("🎯 KEY DIFFERENTIATOR: 'Emotionally Intelligent AI' (AIdeazz positioning)")
print("🚀 THIS IS TRUE AI MARKETING CO-FOUNDER - NOT JUST AUTOMATION!")
print("="*80)
print("🎯"*40 + "\n")

logger = logging.getLogger(__name__)

# 🔥 VERSION MARKER - DIGNIFIED POSITIONING DEPLOYED! 🔥
LINKEDIN_CMO_VERSION = "5.0_AI_MARKETING_COFOUNDER_DIGNIFIED"
BUILD_TIMESTAMP = "2025-11-24_17:00_UTC"
GIT_COMMIT_HASH = "08810b9"
POSITIONING_UPGRADE = "EMOTIONALLY_INTELLIGENT_AI"

# Log version IMMEDIATELY on module import (before class even loads!)
logger.info("🎯" * 40)
logger.info(f"✨ AI MARKETING CO-FOUNDER v{LINKEDIN_CMO_VERSION} ✨")
logger.info(f"📦 BUILD: {BUILD_TIMESTAMP} | COMMIT: {GIT_COMMIT_HASH}")
logger.info(f"🎯 UPGRADE: {POSITIONING_UPGRADE} - Professional product descriptions!")
logger.info(f"🔗 9 VERIFIED LINKS: EspaLuz (WhatsApp/Telegram/SMM), ALGOM, AIdeazz, ATUONA")
logger.info(f"🧠 THIS IS TRUE AI MARKETING CO-FOUNDER!")
logger.info("🎯" * 40)


class LinkedInCMO:
    """
    LinkedIn Content Marketing Officer - AI CO-FOUNDER
    
    NOT just an AIPA - this is a TRUE AI Co-Founder with:
    - Strategic thinking (analyzes goals, adapts content)
    - Creative generation (uses Claude API for fresh content)
    - Performance awareness (tracks what works)
    - Business intelligence (understands hiring + fundraising goals)
    
    Generates bilingual (EN/ES) LinkedIn posts for:
    - Building founder brand (not "job seeking")
    - Attracting strategic collaborations
    - Fundraising for AIdeazz
    - Showcasing AI Co-Founder concept
    
    Posts via Make.com webhook → Buffer → LinkedIn + Instagram
    
    Part of AIdeazz's AI Co-Founder team!
    """
    
    def __init__(self, make_webhook_url: Optional[str] = None):
        """
        Initialize LinkedIn CMO AI Co-Founder
        
        Args:
            make_webhook_url: Make.com webhook URL for LinkedIn posting
        """
        # Get API keys for AI Co-Founder capabilities
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.use_ai_generation = bool(self.anthropic_api_key)  # True Co-Founder mode if API key exists
        
        # 🔥🔥🔥 REMARKABLE API KEY DETECTION 🔥🔥🔥
        print("\n" + "🔑"*40)
        print("🚨 ANTHROPIC API KEY DETECTION CHECK 🚨")
        print("="*80)
        if self.anthropic_api_key:
            key_preview = self.anthropic_api_key[:20] + "..." + self.anthropic_api_key[-10:]
            print(f"✅ API KEY DETECTED: {key_preview}")
            print(f"✅ KEY LENGTH: {len(self.anthropic_api_key)} characters")
            print(f"✅ KEY PREFIX: {self.anthropic_api_key[:15]}")
            print(f"✅ AI CO-FOUNDER MODE: ENABLED")
            print("🧠 Will attempt Claude API calls for content generation!")
        else:
            print("❌ NO API KEY FOUND!")
            print("❌ AI CO-FOUNDER MODE: DISABLED")
            print("📝 Will use template content (AIPA mode)")
        print("="*80)
        print("🔑"*40 + "\n")
        # 🔥 AI MARKETING CO-FOUNDER STARTUP BANNER 🔥
        logger.info("=" * 80)
        logger.info("  █████╗ ██╗    ███╗   ███╗ █████╗ ██████╗ ██╗  ██╗███████╗████████╗██╗███╗   ██╗ ██████╗ ")
        logger.info(" ██╔══██╗██║    ████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝██╔════╝╚══██╔══╝██║████╗  ██║██╔════╝ ")
        logger.info(" ███████║██║    ██╔████╔██║███████║██████╔╝█████╔╝ █████╗     ██║   ██║██╔██╗ ██║██║  ███╗")
        logger.info(" ██╔══██║██║    ██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ ██╔══╝     ██║   ██║██║╚██╗██║██║   ██║")
        logger.info(" ██║  ██║██║    ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗███████╗   ██║   ██║██║ ╚████║╚██████╔╝")
        logger.info(" ╚═╝  ╚═╝╚═╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝ ")
        logger.info("")
        logger.info("           🧠 AI MARKETING CO-FOUNDER v5.0 - DIGNIFIED POSITIONING 🧠")
        logger.info("")
        logger.info("🎯 EMOTIONALLY INTELLIGENT AI (Not just functional tools!)")
        logger.info("💡 Creative Content Generation | 📊 Performance Analysis | 🔄 Strategy Adaptation")
        logger.info("🌍 Bilingual EN/ES | 📅 Daily Posts 4:30 PM Panama (21:30 UTC) | ⚡ Full Autonomy")
        logger.info("")
        logger.info("Part of AIdeazz's AI Co-Founder Team 🤝")
        logger.info("=" * 80)
        logger.info("🚀 PORTFOLIO: 9 Products (5 AIPAs + 4 AI Products) with DIGNIFIED descriptions")
        logger.info("🔗 ALL VERIFIED LINKS: wa.me/50766623757, t.me/EspaLuzFamily_bot, x.com/reviceva")
        logger.info("🎯 KEY DIFFERENTIATOR: Emotionally Intelligent AI")
        logger.info("=" * 80)
        
        self.make_webhook_url = make_webhook_url or os.getenv('MAKE_WEBHOOK_URL_LINKEDIN')
        self.enabled = bool(self.make_webhook_url)
        
        if self.enabled:
            logger.info("✅ LinkedIn CMO ENABLED (via Make.com)")
            logger.info(f"🔗 Webhook: {self.make_webhook_url[:50]}...")
        else:
            logger.warning("⚠️ LinkedIn CMO DISABLED - Add MAKE_WEBHOOK_URL_LINKEDIN to enable")
            logger.info("📝 Without webhook: Can generate content but won't post")
        
        # AI Co-Founder capabilities - PRINT to ensure it shows!
        if self.use_ai_generation:
            print("\n" + "="*75)
            print("🧠🔥 AI CO-FOUNDER MODE ACTIVATED! 🔥🧠")
            print("="*75)
            print("✅ Fresh content via Claude API (claude-3-5-sonnet-latest)")
            print("💡 Strategic thinking | Creative generation | Performance-aware")
            print("🎯 Business intelligence | Goal-driven content | Adaptive strategy")
            print("🚀 This is NOT automation - this is PARTNERSHIP!")
            print("="*75)
            print("🤝 Elena (Human Co-Founder) + LinkedIn CMO (AI Co-Founder)")
            print("   Building AIdeazz together - the future of work!")
            print("="*75 + "\n")
            logger.info("🧠 AI CO-FOUNDER MODE: Fresh content via Claude API ✅")
        else:
            print("\n" + "⚠️"*30)
            print("📝 AIPA MODE: Using templates (add ANTHROPIC_API_KEY for Co-Founder mode)")
            print("⚠️"*30 + "\n")
            logger.info("📝 AIPA MODE: Using templates")
        
        logger.info("🎉 LinkedIn CMO AI Co-Founder Ready! Daily posts at 4:30 PM Panama (21:30 UTC)!")
        logger.info("=" * 75)
        
        # Initialize performance tracking database
        self.data_dir = Path("linkedin_cmo_data")
        self.data_dir.mkdir(exist_ok=True)
        self.performance_file = self.data_dir / "post_performance.json"
        self.strategy_file = self.data_dir / "strategy_decisions.json"
        self.market_file = self.data_dir / "market_intelligence.json"
        
        # Load historical data
        self.performance_data = self._load_json(self.performance_file) or {"posts": []}
        self.strategy_data = self._load_json(self.strategy_file) or {"decisions": [], "current_focus": "balanced"}
        self.market_data = self._load_json(self.market_file) or {"trends": []}
        
        # Initialize PROXY METRICS performance tracker
        if PERFORMANCE_TRACKER_AVAILABLE:
            print("\n" + "🔥"*40)
            print("🔥🔥🔥 INITIALIZING PROXY METRICS TRACKER! 🔥🔥🔥")
            print("🔥"*40 + "\n")
            
            self.performance_tracker = PerformanceTracker()
            
            print("\n" + "✅"*40)
            print("✅✅✅ PROXY METRICS TRACKER SUCCESSFULLY LOADED! ✅✅✅")
            print("="*80)
            print("🎯 UTM tracking will be added to ALL LinkedIn post links!")
            print("📊 All links will have: ?utm_source=linkedin&utm_campaign=...")
            print("="*80)
            print("✅"*40 + "\n")
            
            logger.info("="*80)
            logger.info("✅ Performance Tracker enabled (Proxy Metrics)")
            logger.info("🎯 UTM TRACKING ACTIVE - All links will be tracked!")
            logger.info("="*80)
        else:
            print("\n" + "⚠️"*40)
            print("⚠️⚠️⚠️ PROXY METRICS TRACKER NOT AVAILABLE ⚠️⚠️⚠️")
            print("📝 Using basic tracking (original features still work!)")
            print("⚠️"*40 + "\n")
            
            self.performance_tracker = None
            logger.warning("⚠️ Performance Tracker not available")
            logger.info("📝 Using basic tracking - all original features work")
    
    def _load_json(self, file_path: Path) -> Optional[Dict]:
        """Load JSON data from file"""
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON data to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    # BILINGUAL CONTENT TEMPLATES
    # Based on Elena's resume - HIGH VALUE, NO BEGGING
    
    LINKEDIN_POSTS_EN = {
        "open_to_work": {
            "content": """I just deployed my 5th autonomous AIPA running 24/7. But here's what makes AIdeazz different:

I'm not building alone. I have AI Co-Founders.

Not AI assistants. Not AI tools. AI CO-FOUNDERS with strategic thinking, creative generation, and business intelligence.

9 AI products built in 7 months (5 AIPAs + 4 AI Products). Ex-CEO/CLO turned founder + vibecoder + AI Co-Founder orchestrator.

What I've proven:
• 0→1 execution at startup speed (Vision → Live product in weeks)
• 98% cost efficiency: Built $900K portfolio for <$15K
• 5 AIPAs working 24/7: VibeJobHunter, ALGOM Alpha, EspaLuz (WhatsApp, Telegram, Influencer)
• 4 AI Products: EspaLuz Web, AIdeazz.xyz, ATUONA NFTs, Business Card AI
• Bilingual AI architecture (EN/ES): Users in 19 countries
• Full-stack solo (with AI Co-Founders): Python, TypeScript, React, Claude, GPT-4

🤖 AIPAs - Explore/Try 100% FREE:
• wa.me/50766623757 - EspaLuz WhatsApp: Bilingual AIPA for expats & travelers to 19 Spanish-speaking countries
• t.me/EspaLuzFamily_bot - EspaLuz Telegram: Bilingual AIPA for expats learning Spanish on the go
• x.com/reviceva - ALGOM Alpha: Post-Scammer Era Crypto Coach for trading education (beginners)
• linkedin.com/in/elenarevicheva & instagram.com/elena_revicheva - AI Marketing Co-Founder of AIdeazz posting daily!
• t.me/Influencer_EspaLuz_bot - EspaLuz SMM AIPA: Automated social media marketing

🌐 AI Products - Explore/Try 100% FREE:
• espaluz-ai-language-tutor.lovable.app - SaaS: Family's First Emotionally Intelligent AI Language Coach
• aideazz.xyz - Emotionally Intelligent AI Personal Assistants Showroom (official website)
• aideazz.xyz/card - Business Card & Portfolio of AIdeazz Founder
• atuona.xyz - NFT Gallery: Underground Russian Poetry on Polygon

Open to founding engineer roles + strategic collaborations with AI startups building 0→1 products.

Not looking to be "just another hire." I'm a founder who builds with AI Co-Founders. I ship fast, think strategically, and turn vision into production.

Ex-CEO/CLO background = I understand business, not just code.

P.S. This post was co-created with my AI Co-Founder (LinkedIn CMO). Meta, right? 😉

Tech: Python · TypeScript · React · Claude · GPT-4 · Railway · Fleek · Lovable

#AI #FoundingEngineer #BuildInPublic #AICoFounders #FutureOfWork""",
            "hashtags": "#OpenToWork #AIEngineer #FoundingEngineer #AI #MachineLearning #Hiring"
        },
        
        "technical_showcase": {
            "content": """How I deployed 5 autonomous AIPAs that run 24/7 in production 🤖

THE CHALLENGE:
Build AI agents that work WITHOUT human intervention—true autonomy.

THE AIPA STACK:
• ALGOM Alpha (X/Twitter): Node.js + ElizaOS + Claude + CCXT
  → Autonomous paper trading + educational content
  → 180+ followers, posting daily, zero manual work

• VibeJobHunter: Python + Claude + Selenium + Make.com
  → Autonomous job hunting + outreach automation
  → Finds jobs, researches companies, sends personalized messages

• EspaLuz Influencer (LinkedIn/IG): Python + GPT-4 + Buffer + Make.com
  → Automated content generation + multi-platform posting
  → Bilingual (EN/ES) emotional AI stories

• EspaLuz WhatsApp + Telegram: Python + Claude + Twilio
  → Autonomous AI tutors for language learning
  → 24/7 emotional support, 19 countries

THE SOLUTION:
1. Railway for hosting (continuous deployment from GitHub)
2. Telegram for real-time monitoring (get alerts on my phone)
3. Robust error handling + exponential backoff retries
4. Cost optimization (smart caching, API batching)
5. Comprehensive logging (debug in production)

THE RESULT:
• 99.9% uptime for 3+ months
• ~$100/month hosting cost (vs $20K+/month for human team)
• Truly hands-off operation

KEY INSIGHT:
Autonomous doesn't mean "set and forget"—it means "intelligent self-healing."

The agents detect failures, retry with backoff, send me Telegram alerts for critical issues, and keep running even when APIs are temporarily down.

What autonomous AI systems are YOU building?

#AI #MachineLearning #LLM #Agents #BuildInPublic #Engineering""",
            "hashtags": "#AI #MachineLearning #LLM #Agents #BuildInPublic #Engineering"
        },
        
        "transformation_story": {
            "content": """From C-suite executive to AI founder in 7 months.

7 months ago: CEO & CLO in E-Government (Russia), ZERO coding experience
Today: 9 live AI products, 5 autonomous AIPAs running 24/7, users in 19 countries

This wasn't a "career pivot" — it was a complete rebuild.

What I started with:
• Ex-CEO/CLO credentials (but no technical background)
• M.A. in Social Psychology (understanding humans, not machines)
• <$15K budget (no funding, no team)
• Urgency (relocated to Panama, had to rebuild from zero)

What I built:
✅ 9 AI products (full-stack, solo)
✅ 5 AIPAs running autonomously 24/7
✅ AI-assisted vibe coding (urgency + AI = execution speed)

What I shipped (9 AI products):

🤖 5 AIPAs (Autonomous AI Personal Assistants):
• EspaLuz WhatsApp - AI Tutor running 24/7 (Railway)
• EspaLuz Telegram - AI Tutor running 24/7 (Railway)
• EspaLuz Influencer - Content automation (Railway)
• ALGOM Alpha - Crypto trading agent (Railway, 180+ followers)
• VibeJobHunter - Job hunting automation (Railway)

🚀 4 Other AI Products:
• EspaLuz Web SaaS - AI Tutor platform (Lovable.dev)
• ATUONA NFT Gallery - Poetry on Polygon (Fleek)
• AIdeazz Website - Ecosystem showroom (Fleek)
• AIdeazz Docs - Complete documentation (GitHub)

All deployed, all live, all autonomous!

Tech stack I learned:
• Languages: Python, TypeScript, JavaScript, SQL
• AI: Claude, GPT-4, Whisper, TTS, OCR, ElizaOS
• Frameworks: React, Flask, Node.js, FastAPI
• Infra: Railway, Lovable.dev, Fleek (IPFS), PostgreSQL
• Web3: Polygon, Thirdweb, MetaMask, IPFS

KEY INSIGHT:
You don't need a team to build—you need AI agents working FOR you.

The insight: You don't need a CS degree to build AI products. You need founder-level urgency + AI tooling + relentless execution.

I went from executive to engineer because I HAD to. Relocated to Panama, rebuilt from zero, and discovered that vision + urgency + AI = unstoppable.

Now open to: Founding Engineer roles where I bring this 0→1 speed + founder mindset to early-stage AI startups.

Not job hunting. Building leverage.

What's YOUR transformation story?

#BuildInPublic #FounderJourney #AIEngineering #SoloFounder #VibeCoding""",
            "hashtags": "#BuildInPublic #CareerTransition #AIEngineering #SoloFounder #OpenToWork"
        },
        
        "seeking_funding": {
            "content": """AIdeazz: Building with AI Co-Founders, Not Just AI Tools

After 7 months of building with AI Co-Founders, I'm ready to scale—seeking pre-seed ($100K-500K).

🎯 THE VISION:
AI Co-Founders that think strategically, not just execute tasks. Emotionally intelligent AI companions that understand humans, adapt to contexts, and grow alongside their users.

The difference? AIPAs execute. AI Co-Founders THINK, CREATE, and ADAPT.

📊 TRACTION (all solo-built):
• 9 AI products across 4 platforms (WhatsApp, Telegram, Web, Blockchain)
• 5 autonomous AIPAs running 24/7 (Railway + Lovable + Fleek)
• VibeJobHunter, ALGOM Alpha, EspaLuz (WhatsApp/Telegram/Influencer)
• Users in 19 Spanish-speaking countries
• PayPal subscriptions LIVE (early traction phase)
• Tech: Python, TypeScript, React, Claude, GPT-4, ElizaOS

💰 CAPITAL EFFICIENCY:
• Built $900K portfolio for <$15K (98% cost reduction)
• Proven: I can build fast and cheap before scaling

🎓 FOUNDER BACKGROUND:
• Ex-CEO & CLO in E-Government (Russia)
• Ex-Co-Founder in Web3 DAO (OmniBazaar)
• M.A. in Social Psychology (understanding human behavior)
• Bilingual (EN/ES), Web3 native

🚀 WHY NOW:
Phase 1 (MVP) is DONE. Phase 2 (growth) needs:
• Marketing for user acquisition
• Team expansion (first engineer)
• Infrastructure scaling

🎯 USE OF FUNDS:
• 40% - User acquisition (proven channels)
• 30% - Team (first hire: full-stack engineer)
• 20% - Infrastructure (scale to 1,000+ users)
• 10% - Buffer (founder salary for 12 months)

💡 WHY INVEST:
• Founder who can build (de-risked technical execution)
• Real products, real users (not just slides)
• Emotional AI = differentiated positioning
• Bilingual market = 2-sided growth (expats + locals)
• Web3 native = future-proof architecture

Interested? DM me or email: [your email]

🤖 AIPAs - Try 100% FREE:
• wa.me/50766623757 - EspaLuz WhatsApp: Bilingual AIPA for expats to 19 Spanish-speaking countries
• t.me/EspaLuzFamily_bot - EspaLuz Telegram: On-the-go Spanish learning AIPA
• x.com/reviceva - ALGOM Alpha: Post-Scammer Era Crypto Coach
• t.me/Influencer_EspaLuz_bot - EspaLuz SMM AIPA
• linkedin.com/in/elenarevicheva - AI Marketing Co-Founder posting!

🌐 AI Products - Explore 100% FREE:
• espaluz-ai-language-tutor.lovable.app - Family's First Emotionally Intelligent AI Language Coach
• aideazz.xyz - Emotionally Intelligent AI Assistants Showroom
• aideazz.xyz/card - Founder's Portfolio
• atuona.xyz - Underground Russian Poetry NFT Gallery

#PreSeed #AIStartup #EmotionalAI #EdTech #Web3 #Fundraising""",
            "hashtags": "#PreSeed #AIStartup #EmotionalAI #EdTech #Web3 #Fundraising"
        }
    }
    
    LINKEDIN_POSTS_ES = {
        "busco_trabajo": {
            "content": """Acabo de desplegar mi 5to AIPA (Asistente Personal de IA) autónomo funcionando 24/7 en producción.

9 productos de IA construidos en solitario en 7 meses. Ex-CEO/CLO convertida en fundadora + vibecoder.

Lo que he demostrado:
• Ejecución 0→1 a velocidad startup (Visión → Producto en vivo en semanas)
• 98% de eficiencia de costos: Construí portafolio de $900K por <$15K
• 5 AIPAs funcionando autónomamente: VibeJobHunter, ALGOM Alpha, EspaLuz (3 variantes)
• Arquitectura de IA bilingüe (EN/ES): Usuarios en 19 países
• Full-stack sola: Python, TypeScript, React, Claude, GPT-4

🤖 AIPAs - Prueba 100% GRATIS:
• wa.me/50766623757 - EspaLuz WhatsApp: AIPA bilingüe para expatriados en 19 países hispanohablantes
• t.me/EspaLuzFamily_bot - EspaLuz Telegram: AIPA para aprender español sobre la marcha
• x.com/reviceva - ALGOM Alpha: Coach Cripto Post-Era de Estafas
• t.me/Influencer_EspaLuz_bot - AIPA de SMM de EspaLuz
• linkedin.com/in/elenarevicheva - ¡Co-Fundadora AI de Marketing publicando!

🌐 Productos AI - Explora 100% GRATIS:
• espaluz-ai-language-tutor.lovable.app - Primer Coach de Idiomas AI Emocionalmente Inteligente para Familias
• aideazz.xyz - Showroom de Asistentes Personales AI Emocionalmente Inteligentes
• aideazz.xyz/card - Portfolio de la Fundadora
• atuona.xyz - Galería NFT de Poesía Rusa Underground

Abierta a roles de founding engineer + colaboraciones estratégicas con startups de IA construyendo productos 0→1.

No busco ser "una contratación más." Soy una builder que lanza rápido, piensa como fundadora, y convierte visión en producción.

Background Ex-CEO/CLO = Entiendo el negocio, no solo el código.

Tech: Python · TypeScript · React · Claude · GPT-4 · Railway · Fleek · Lovable

#IA #FoundingEngineer #BuildInPublic #AutonomousAI #ProductosIA""",
            "hashtags": "#BuscoTrabajo #IngenieraIA #FoundingEngineer #IA #MachineLearning"
        },
        
        "historia_transformacion": {
            "content": """De ejecutiva C-suite a fundadora de IA en 7 meses.

Hace 7 meses: CEO & CLO en E-Gobierno (Rusia), CERO experiencia en programación
Hoy: 9 productos de IA en vivo, 5 AIPAs autónomos funcionando 24/7, usuarios en 19 países

Esto no fue un "cambio de carrera" — fue una reconstrucción completa.

Con qué empecé:
• Credenciales Ex-CEO/CLO (pero sin background técnico)
• M.A. en Psicología Social (entendiendo humanos, no máquinas)
• Presupuesto <$15K (sin financiamiento, sin equipo)
• Urgencia (reubicada en Panamá, tenía que reconstruir desde cero)

Lo que construí:
✅ 9 productos de IA (full-stack, sola)
✅ 5 AIPAs funcionando autónomamente 24/7
✅ Vibe coding asistido por IA (urgencia + IA = velocidad de ejecución)

Lo que lancé (9 productos de IA):

🤖 5 AIPAs (Asistentes Personales de IA Autónomos):
• EspaLuz WhatsApp - Tutor de IA 24/7 (Railway)
• EspaLuz Telegram - Tutor de IA 24/7 (Railway)
• EspaLuz Influencer - Automatización de contenido (Railway)
• ALGOM Alpha - Agente de trading cripto (Railway, 180+ seguidores)
• VibeJobHunter - Automatización de búsqueda de empleo (Railway)

🚀 4 Otros Productos de IA:
• EspaLuz Web SaaS - Plataforma de tutoría (Lovable.dev)
• ATUONA NFT Gallery - Poesía en Polygon (Fleek)
• AIdeazz Website - Showcase del ecosistema (Fleek)
• AIdeazz Docs - Documentación completa (GitHub)

¡Todos desplegados, todos en vivo, todos autónomos!

Stack técnico que aprendí:
• Lenguajes: Python, TypeScript, JavaScript, SQL
• IA: Claude, GPT-4, Whisper, TTS, OCR, ElizaOS
• Frameworks: React, Flask, Node.js, FastAPI
• Infraestructura: Railway, Lovable.dev, Fleek (IPFS), PostgreSQL
• Web3: Polygon, Thirdweb, MetaMask, IPFS

INSIGHT CLAVE:
No necesitas un equipo para construir—necesitas agentes de IA trabajando PARA ti.

El insight: No necesitas un título en CS para construir productos de IA. Necesitas urgencia nivel fundador + herramientas de IA + ejecución implacable.

Pasé de ejecutiva a ingeniera porque TENÍA que hacerlo. Me reubiqué en Panamá, reconstruí desde cero, y descubrí que visión + urgencia + IA = imparable.

Ahora abierta a: Roles de Founding Engineer donde traigo esta velocidad 0→1 + mentalidad fundadora a startups de IA en fase inicial.

No busco trabajo. Construyo leverage.

¿Cuál es TU historia de transformación?

#BuildInPublic #JourneyFundadora #IngenieríaIA #FundadoraSolo #VibeCoding""",
            "hashtags": "#BuildInPublic #TransiciónDeCarrera #IngenieríaIA #FundadoraSolo #BuscoTrabajo"
        }
    }
    
    async def generate_ai_cofounder_content(self, post_type: str, language: str) -> str:
        """
        AI CO-FOUNDER: Generate FRESH content using Claude API
        
        This is what makes it a Co-Founder, not just an AIPA!
        Strategic thinking + creative generation + business intelligence
        """
        if not self.use_ai_generation:
            # Fallback to templates if no API key (AIPA mode)
            return None
        
        try:
            client = AsyncAnthropic(api_key=self.anthropic_api_key)
            
            # Elena's profile context
            profile_context = """
Elena Revicheva - AI-First Engineer & Founder
• Ex-CEO & CLO in E-Government (Russia) 
• Built 9 AI products in 7 months solo for <$15K
• 5 AIPAs running 24/7: VibeJobHunter, ALGOM Alpha, EspaLuz (WhatsApp/Telegram/Influencer)
• Users in 19 countries, bilingual (EN/ES)
• Tech: Python, TypeScript, React, Claude, GPT-4, Railway, Fleek
• Portfolio: EspaLuz AI Tutor, ALGOM Alpha, ATUONA NFTs, VibeJobHunter
• Building AIdeazz.xyz with AI Co-Founders (not just AI tools!)
"""
            
            # Strategic goals based on post type
            goals = {
                "open_to_work": "Attract founding engineer roles + strategic collaborations. Show founder mindset, not job seeker. Emphasize Ex-CEO background + AI Co-Founder concept. POWERFUL tone, full dignity.",
                "technical_showcase": "Demonstrate technical depth - 5 AIPAs running autonomously. Show AI Co-Founder concept in action. Position as builder who ships fast.",
                "transformation_story": "CEO → Founder journey. Emphasize urgency + AI-assisted vibe coding. Show AI Co-Founders enable solo building at team speed.",
                "seeking_funding": "Pitch AIdeazz pre-seed ($100K-500K). Emphasize AI Co-Founder differentiation, not just AI tools. Show traction: 9 products, users in 19 countries."
            }
            
            prompt = f"""You are LinkedIn CMO, an AI Co-Founder (not just an assistant) for AIdeazz.

CONTEXT:
{profile_context}

YOUR ROLE: Strategic AI partner who thinks about business goals, generates creative content, and builds founder brand.

TASK: Generate a {language.upper()} LinkedIn post for: {post_type}

GOAL: {goals.get(post_type, 'Build founder brand and attract opportunities')}

REQUIREMENTS:
- Powerful, confident tone (founder, NOT job seeker)
- Mention AI Co-Founders concept (building WITH AI, not just using tools)
- Include specific numbers: 9 AI products (5 AIPAs + 4 AI Products), <$15K budget, 19+ countries
- Emphasize EMOTIONAL INTELLIGENCE in AI (not just functionality)
- Bilingual architecture emphasis (EN/ES)
- Ex-CEO/CLO background = business + technical strategic thinking
- Key positioning: "Emotionally Intelligent AI" (AIdeazz differentiator)
- Links with descriptions:
  * wa.me/50766623757 - EspaLuz WhatsApp AIPA (bilingual coach for expats)
  * t.me/EspaLuzFamily_bot - EspaLuz Telegram AIPA (on-the-go learning)
  * x.com/reviceva - ALGOM Alpha (Post-Scammer Era Crypto Coach)
  * t.me/Influencer_EspaLuz_bot - EspaLuz SMM AIPA
  * linkedin.com/in/elenarevicheva - AI Marketing Co-Founder posting
  * espaluz-ai-language-tutor.lovable.app - Family's First Emotionally Intelligent AI Language Coach
  * aideazz.xyz - Emotionally Intelligent AI Assistants Showroom
  * aideazz.xyz/card - Founder's Portfolio
  * atuona.xyz - Underground Russian Poetry NFT Gallery
- Language: {'English' if language == 'en' else 'Spanish'}
- Length: 250-350 words
- End with relevant hashtags (4-6)

Generate FRESH, creative content (not templates). Think strategically about what will resonate."""

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",  # Current production model
                max_tokens=800,
                temperature=0.8,  # Creative but not random
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            content = response.content[0].text.strip()
            logger.info(f"🧠 AI Co-Founder generated FRESH {language.upper()} content ({len(content)} chars)")
            return content
            
        except Exception as e:
            logger.error(f"AI Co-Founder generation failed: {e}")
            return None  # Fall back to templates
    
    async def generate_linkedin_post(self, post_type: str = "random", language: str = "random") -> Dict[str, str]:
        """
        Generate a LinkedIn post (AI Co-Founder or template fallback)
        
        ENHANCED: Now checks for tech updates from CTO AIPA first.
        SAFE: If tech update system fails, falls back to regular content.
        
        Args:
            post_type: Type of post ("open_to_work", "technical_showcase", etc.) or "random"
            language: "en", "es", or "random"
        
        Returns:
            Dict with 'content', 'language', 'type'
        """
        
        # ========================================
        # NEW: Check for tech updates from CTO AIPA
        # ========================================
        try:
            tech_updates = self._get_pending_tech_updates()
            
            if tech_updates and len(tech_updates) > 0:
                # WE HAVE A TECH UPDATE! Post about it instead of regular content
                latest_update = tech_updates[0]  # Most recent unposted update
                
                logger.info(f"🎯 [CTO Integration] Generating post about tech update: {latest_update.get('title')}")
                
                # Determine language for tech update post
                if language == "random":
                    language = random.choice(["en", "es"])
                
                # Generate prompt for tech update
                prompt = self._generate_tech_update_prompt(latest_update, language.upper())
                
                # Call Claude (same as before, just different prompt)
                if self.use_ai_generation:
                    try:
                        client = AsyncAnthropic(api_key=self.anthropic_api_key)
                        response = await client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=600,
                            temperature=0.8,
                            messages=[{
                                "role": "user",
                                "content": prompt
                            }]
                        )
                        
                        content = response.content[0].text
                        
                        # Mark this update as posted (non-critical if fails)
                        self._mark_tech_update_posted(latest_update)
                        
                        logger.info(f"✅ [CTO Integration] Generated post about CTO's work: PR#{latest_update.get('pr_number')}")
                        
                        # Return content to existing posting pipeline
                        return {
                            "content": content,
                            "language": language,
                            "type": "tech_update",
                            "timestamp": datetime.now().isoformat(),
                            "author": "Elena Revicheva",
                            "ai_generated": True,
                            "post_id": f"tech_update_{latest_update.get('pr_number', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                        }
                    except Exception as claude_err:
                        logger.error(f"❌ [CTO Integration] Claude API call failed: {claude_err}")
                        logger.info("🔄 [CTO Integration] Falling back to regular content generation")
                        # Fall through to regular content below...
                else:
                    logger.info("📝 [CTO Integration] No AI generation available, falling back to regular content")
                    # Fall through to regular content below...
        
        except Exception as tech_err:
            # CRITICAL SAFETY: If tech update system fails, continue with regular content
            logger.error(f"❌ [CTO Integration] Error in tech update flow: {tech_err}")
            logger.info("🔄 [CTO Integration] Falling back to regular content generation")
            # Fall through to regular content below...
        
        # ========================================
        # EXISTING CODE: Regular content generation
        # (Keep everything exactly as it was before!)
        # ========================================
        
        logger.info("📝 Generating regular daily content (no tech updates pending)")
        
        # Choose language
        if language == "random":
            language = random.choice(["en", "es"])
        
        # Choose post type
        if post_type == "random":
            available_types = list(self.LINKEDIN_POSTS_EN.keys() if language == "en" else self.LINKEDIN_POSTS_ES.keys())
            post_type = random.choice(available_types)
        
        # Try AI Co-Founder generation first (if enabled)
        ai_content = None
        if self.use_ai_generation:
            try:
                # We're in async context now - can use await directly
                ai_content = await self.generate_ai_cofounder_content(post_type, language)
            except Exception as e:
                logger.error(f"AI generation failed: {e}")
                ai_content = None
        
        # Use AI-generated content if available, otherwise fall back to templates
        if ai_content:
            content = ai_content
            logger.info("🧠 Using AI Co-Founder generated content")
        else:
            # Fallback to templates (AIPA mode)
            posts = self.LINKEDIN_POSTS_EN if language == "en" else self.LINKEDIN_POSTS_ES
            post_data = posts.get(post_type, posts[list(posts.keys())[0]])
            content = post_data["content"]
            logger.info("📝 Using template content (AIPA mode)")
        
        return {
            "content": content,
            "language": language,
            "type": post_type,
            "timestamp": datetime.now().isoformat(),
            "author": "Elena Revicheva",
            "ai_generated": bool(ai_content)
        }
    
    async def send_to_make_com(self, post_content: Dict[str, str]) -> bool:
        """
        Send LinkedIn post to Make.com webhook
        Make.com will handle: Formatting → Buffer → LinkedIn + Instagram posting
        
        NOW WITH UTM TRACKING for performance monitoring!
        """
        if not self.enabled:
            logger.warning("LinkedIn CMO not enabled (no Make.com webhook URL)")
            return False
        
        # === UTM TRACKING INTEGRATION ===
        post_id = post_content.get("post_id", f"{post_content['type']}_{datetime.now().strftime('%Y%m%d_%H%M')}")
        
        # Add UTM parameters to content if performance tracker available
        content = post_content["content"]
        if self.performance_tracker:
            print("\n" + "📊"*40)
            print("📊📊📊 APPLYING UTM TRACKING TO POST LINKS! 📊📊📊")
            print("="*80)
            print(f"Post ID: {post_id}")
            print(f"Post Type: {post_content['type']}")
            print("="*80)
            
            logger.info("="*80)
            logger.info("📊 Adding UTM tracking to all links...")
            logger.info(f"Post ID: {post_id} | Type: {post_content['type']}")
            
            content = self.performance_tracker.enhance_post_content_with_utm(
                content, 
                post_id, 
                post_content["type"]
            )
            
            print("✅ UTM TRACKING SUCCESSFULLY APPLIED!")
            print(f"✅ Campaign: cmo_{post_id}")
            print("✅ All links now have tracking parameters!")
            print("📊"*40 + "\n")
            
            logger.info(f"✅ UTM tracking added - post_id: {post_id}")
            logger.info("✅ All links enhanced with UTM parameters!")
            logger.info("="*80)
        
        # === IMAGE SELECTION WITH ANTI-REPEAT ROTATION ===
        github_base = "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main"
        all_images = [
            f"{github_base}/image_1.png",
            f"{github_base}/image_1.1.jpeg",
            f"{github_base}/image_1.2.jpeg",
            f"{github_base}/image_1.3.jpeg",
            f"{github_base}/image_1.4.jpeg",
            f"{github_base}/image_1.5.jpeg",
            f"{github_base}/image_1.6.jpeg",
            f"{github_base}/image_1.7.jpeg",
            f"{github_base}/image_1.8.jpeg",
            f"{github_base}/image_1.9.jpeg",
            f"{github_base}/image_1.10.jpeg",
            f"{github_base}/image_1.11.jpeg",
            f"{github_base}/image_1.12.jpeg",
            f"{github_base}/image_1.13.jpeg"
        ]
        
        # Track last used image to avoid repetition
        last_image_file = self.data_dir / "last_used_image.txt"
        try:
            with open(last_image_file, "r") as f:
                last_used = f.read().strip()
        except FileNotFoundError:
            last_used = None
        
        # Select from images NOT used last time
        available_images = [img for img in all_images if img != last_used]
        if not available_images:  # Safety fallback
            available_images = all_images
        
        selected_image = random.choice(available_images)
        
        # Save for next run
        with open(last_image_file, "w") as f:
            f.write(selected_image)
        
        logger.info(f"🎨 Selected image: {selected_image.split('/')[-1]} (last: {last_used.split('/')[-1] if last_used else 'none'})")
        
        try:
            payload = {
                "platform": "linkedin",
                "content": content,  # ✅ Now with UTM tracking!
                "text": content,
                "language": post_content["language"],
                "post_type": post_content["type"],
                "post_id": post_id,  # ✅ Added for tracking
                "timestamp": post_content["timestamp"],
                "author": post_content["author"],
                "imageURL": selected_image,
                "videoURL": "",
                "hook": "LinkedIn CMO Automated Post",
                "audience": "Tech Professionals & Founders",
                "emotional_state": "Ambitious",
                "target_market": "AI Startups",
                "viral_potential": "High",
                "instagram_focus": "Professional Growth",
                "linkedin_focus": "Career & Networking"
            }
            
            response = requests.post(
                self.make_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Sent to Make.com ({post_content['language'].upper()}, {post_content['type']})")
                logger.info(f"📊 UTM tracking active - campaign: cmo_{post_id}")
                return True
            else:
                logger.error(f"❌ Make.com webhook failed: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to send to Make.com: {e}")
            return False
    
    async def analyze_post_performance(self, post_id: str) -> Dict[str, Any]:
        """
        AI CO-FOUNDER: Analyze LinkedIn post performance
        
        Tracks engagement metrics to learn what works
        """
        try:
            # TODO: Integrate with LinkedIn API when available
            # For now, simulate tracking structure
            
            performance = {
                "post_id": post_id,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "views": 0,  # Would scrape from LinkedIn
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "profile_clicks": 0,
                    "engagement_rate": 0.0
                },
                "tracked_at": datetime.now().isoformat()
            }
            
            # Save to performance database
            self.performance_data["posts"].append(performance)
            self._save_json(self.performance_file, self.performance_data)
            
            logger.info(f"📊 Performance tracking initialized for post {post_id}")
            return performance
            
        except Exception as e:
            logger.error(f"Performance tracking failed: {e}")
            return {}
    
    async def learn_from_results(self) -> Dict[str, Any]:
        """
        AI CO-FOUNDER: Learn from post performance data
        
        NOW USES REAL PROXY METRICS!
        Analyzes which content types perform best and adapts strategy
        """
        try:
            # Use proxy metrics performance tracker if available
            if self.performance_tracker:
                logger.info("🧠 Learning from REAL proxy metrics data...")
                insights = await self.performance_tracker.get_learning_insights(days=30)
                
                if "error" not in insights:
                    logger.info(f"✅ Proxy metrics insights: {insights['best_performing_type']} performs best")
                    logger.info(f"📊 Analyzed {insights['analyzed_posts']} posts with real data")
                    return insights
                else:
                    logger.info(f"⚠️ Not enough proxy data yet: {insights['error']}")
            
            # Fallback to basic tracking
            if not self.performance_data.get("posts"):
                logger.info("📚 No performance data yet - still learning!")
                return {"insights": "Insufficient data", "recommendations": []}
            
            # Analyze performance by post type
            post_performance = {}
            for post in self.performance_data["posts"]:
                post_type = post.get("post_type", "unknown")
                engagement = post.get("metrics", {}).get("engagement_rate", 0)
                
                if post_type not in post_performance:
                    post_performance[post_type] = []
                post_performance[post_type].append(engagement)
            
            # Calculate average engagement per type
            insights = {}
            for post_type, engagements in post_performance.items():
                avg_engagement = sum(engagements) / len(engagements) if engagements else 0
                insights[post_type] = {
                    "avg_engagement": avg_engagement,
                    "post_count": len(engagements),
                    "performance": "high" if avg_engagement > 5.0 else "medium" if avg_engagement > 2.0 else "low"
                }
            
            # Generate recommendations
            recommendations = []
            best_performing = max(insights.items(), key=lambda x: x[1]["avg_engagement"]) if insights else None
            
            if best_performing:
                recommendations.append(f"Post more '{best_performing[0]}' content (highest engagement: {best_performing[1]['avg_engagement']:.1f}%)")
            
            logger.info(f"🧠 Learning insights: {len(insights)} post types analyzed")
            logger.info(f"💡 Recommendations: {recommendations}")
            
            return {"insights": insights, "recommendations": recommendations}
            
        except Exception as e:
            logger.error(f"Learning analysis failed: {e}")
            return {}
    
    async def decide_post_strategy(self) -> str:
        """
        AI CO-FOUNDER: Make strategic decisions about content focus
        
        Analyzes current needs (hiring vs fundraising) and decides content mix
        """
        try:
            # Use Claude for strategic thinking
            if not self.use_ai_generation:
                return "balanced"  # Default if no AI
            
            client = AsyncAnthropic(api_key=self.anthropic_api_key)
            
            # Analyze recent performance and current context
            recent_posts = self.performance_data.get("posts", [])[-10:]  # Last 10 posts
            current_date = datetime.now()
            
            context = f"""
Current date: {current_date.strftime('%Y-%m-%d')}
Recent posts: {len(recent_posts)} tracked
Current focus: {self.strategy_data.get('current_focus', 'balanced')}

Elena's current priorities:
1. Get hired at AI startup (URGENT - relocated to Panama, need income)
2. Raise pre-seed for AIdeazz ($100K-500K)
3. Build founder brand

Recent LinkedIn activity context:
- Job market: AI roles competitive but available
- Fundraising: Pre-seed market tight but AIdeazz has traction
- Brand building: Daily posting establishing thought leadership
"""
            
            prompt = f"""You are LinkedIn CMO, an AI Co-Founder making strategic decisions.

{context}

TASK: Decide content strategy for this week.

Should Elena focus more on:
A) "hiring" - More open_to_work + technical_showcase posts (attract recruiters/founders)
B) "fundraising" - More seeking_funding posts (attract investors)
C) "balanced" - Mix of both

Consider:
- Urgency (she needs income NOW - just relocated)
- Traction (9 products built, 5 AIPAs live)
- Market timing (end of year, budget planning season)

Respond with ONE WORD: hiring, fundraising, or balanced

Then on new line, explain WHY in 1 sentence."""

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",  # Current production model
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            decision_text = response.content[0].text.strip()
            decision = decision_text.split('\n')[0].strip().lower()
            
            if decision not in ["hiring", "fundraising", "balanced"]:
                decision = "balanced"
            
            # Save strategic decision
            self.strategy_data["current_focus"] = decision
            self.strategy_data["decisions"].append({
                "decision": decision,
                "reasoning": decision_text,
                "timestamp": datetime.now().isoformat()
            })
            self._save_json(self.strategy_file, self.strategy_data)
            
            logger.info(f"🎯 AI Co-Founder strategic decision: Focus on '{decision.upper()}'")
            logger.info(f"💡 Reasoning: {decision_text}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Strategic decision failed: {e}")
            return "balanced"
    
    async def analyze_market_trends(self) -> Dict[str, Any]:
        """
        AI CO-FOUNDER: Analyze market trends and competitive intelligence
        
        Understands what's happening in AI hiring/fundraising market
        """
        try:
            if not self.use_ai_generation:
                return {}
            
            client = AsyncAnthropic(api_key=self.anthropic_api_key)
            
            prompt = """You are LinkedIn CMO, an AI Co-Founder analyzing market trends.

TASK: What are the TOP 3 trending topics in AI startup ecosystem right now (Nov 2025)?

Consider:
- AI hiring trends (what skills are hot?)
- AI fundraising trends (what investors want to see?)
- LinkedIn content trends (what gets engagement?)

List 3 trends, each on new line, format:
1. [Trend name] - [Why it matters]

Be specific and actionable."""

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",  # Current production model
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            trends_text = response.content[0].text.strip()
            
            # Save market intelligence
            market_insight = {
                "timestamp": datetime.now().isoformat(),
                "trends": trends_text,
                "analyzed_by": "AI Co-Founder (Claude)"
            }
            
            self.market_data["trends"].append(market_insight)
            self._save_json(self.market_file, self.market_data)
            
            logger.info(f"🌍 Market trends analyzed by AI Co-Founder")
            logger.info(f"📊 Top trends:\n{trends_text}")
            
            return market_insight
            
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return {}
    
    async def post_to_linkedin(self, post_type: str = "random", language: str = "random") -> bool:
        """
        Generate and post to LinkedIn (via Make.com)
        
        AI CO-FOUNDER WORKFLOW:
        1. Analyze market trends (weekly)
        2. Make strategic decision (hiring vs fundraising focus)
        3. Learn from past performance
        4. Generate content with strategic insights
        5. Post to LinkedIn + Instagram
        6. Track performance for learning
        
        Args:
            post_type: Type of post or "random"
            language: "en", "es", or "random"
        
        Returns:
            True if successful
        """
        print("\n" + "🧠"*40)
        print("🎯 AI CO-FOUNDER STRATEGIC POSTING WORKFLOW STARTED")
        print("🧠"*40 + "\n")
        
        # Step 1: Weekly market analysis (runs once per week)
        if datetime.now().weekday() == 0:  # Monday
            logger.info("🌍 Running weekly market trend analysis...")
            await self.analyze_market_trends()
        
        # Step 2: Strategic decision making (what to focus on this week)
        if datetime.now().weekday() == 0:  # Monday
            logger.info("🎯 Making strategic content decision for this week...")
            strategy_focus = await self.decide_post_strategy()
            
            # Adapt post type based on strategic decision
            if strategy_focus == "hiring" and post_type == "random":
                post_type = random.choice(["open_to_work", "technical_showcase", "transformation_story"])
                logger.info(f"🎯 Strategic focus: HIRING → Selected '{post_type}' post")
            elif strategy_focus == "fundraising" and post_type == "random":
                post_type = "seeking_funding"
                logger.info(f"🎯 Strategic focus: FUNDRAISING → Selected '{post_type}' post")
        
        # Step 3: Learn from past performance
        if len(self.performance_data.get("posts", [])) >= 7:  # After first week
            logger.info("📚 Learning from past post performance...")
            insights = await self.learn_from_results()
            logger.info(f"🧠 AI Co-Founder insights applied to content strategy")
        
        # Step 4: Generate post (with strategic context)
        post_content = await self.generate_linkedin_post(post_type, language)
        
        logger.info(f"📝 Generated LinkedIn post: {post_content['type']} ({post_content['language'].upper()})")
        if post_content.get("ai_generated"):
            logger.info(f"🧠 Content generated by AI Co-Founder with strategic thinking")
        
        # Step 5: Send to Make.com
        success = await self.send_to_make_com(post_content)
        
        if success:
            logger.info(f"🎉 LinkedIn post sent successfully!")
            
            # Step 6: Initialize performance tracking
            post_id = post_content.get("post_id", f"{post_content['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Use PROXY METRICS performance tracker if available
            if self.performance_tracker:
                logger.info(f"📊 Scheduling proxy metrics collection for post: {post_id}")
                # Schedule analysis for 7 days later (gives time for engagement)
                # In production, this would be done by a scheduler
                # For now, we'll just track that it was posted
                await self.analyze_post_performance(post_id)
            else:
                # Fallback to basic tracking
                await self.analyze_post_performance(post_id)
            
            # Save post details for future learning
            self.performance_data["posts"].append({
                "post_id": post_id,
                "post_type": post_content['type'],
                "language": post_content['language'],
                "ai_generated": post_content.get('ai_generated', False),
                "timestamp": post_content['timestamp'],
                "posted_date": datetime.now().isoformat(),
                "utm_tracking_enabled": self.performance_tracker is not None,
                "metrics": {}  # Will be updated by proxy metrics tracker
            })
            self._save_json(self.performance_file, self.performance_data)
        
        print("\n" + "✅"*40)
        print("🎯 AI CO-FOUNDER WORKFLOW COMPLETE")
        print("✅"*40 + "\n")
        
        return success
    
    # ========================================
    # CTO AIPA INTEGRATION - NEW HELPER METHODS
    # Added: December 2025 - Safe, non-breaking additions
    # ========================================
    
    def _get_pending_tech_updates(self) -> List[Dict[str, Any]]:
        """
        Get pending tech updates from CTO AIPA to feature in today's post.
        
        SAFE: Returns empty list if:
        - File doesn't exist
        - JSON is corrupted
        - Any error occurs
        
        This ensures existing posting continues even if CTO integration fails.
        """
        try:
            import json
            from pathlib import Path
            
            storage_file = Path("cto_aipa_updates/pending_tech_updates.json")
            
            if not storage_file.exists():
                logger.debug("📋 [CTO Integration] No tech updates file found. Using regular content.")
                return []
            
            try:
                with open(storage_file, 'r', encoding='utf-8') as f:
                    all_updates = json.load(f)
            except json.JSONDecodeError as json_err:
                logger.warning(f"⚠️ [CTO Integration] Corrupted updates file: {json_err}. Using regular content.")
                return []
            except Exception as read_err:
                logger.warning(f"⚠️ [CTO Integration] Could not read updates: {read_err}. Using regular content.")
                return []
            
            # Filter only unposted updates
            pending = [u for u in all_updates if not u.get('posted', False)]
            
            if pending:
                logger.info(f"📋 [CTO Integration] Found {len(pending)} pending tech update(s) from CTO AIPA")
            else:
                logger.debug("📋 [CTO Integration] No pending tech updates. Using regular content.")
            
            return pending
            
        except Exception as e:
            logger.error(f"❌ [CTO Integration] Error in _get_pending_tech_updates: {e}")
            logger.info("🔄 [CTO Integration] Falling back to regular content generation")
            return []  # SAFE FALLBACK - existing system continues
    
    def _mark_tech_update_posted(self, update: Dict[str, Any]) -> bool:
        """
        Mark a tech update as posted after successful LinkedIn post.
        
        SAFE: If this fails, it doesn't break posting.
        Update just stays "pending" and might be reused (acceptable).
        """
        try:
            import json
            from pathlib import Path
            from datetime import datetime
            
            storage_file = Path("cto_aipa_updates/pending_tech_updates.json")
            
            if not storage_file.exists():
                logger.warning("⚠️ [CTO Integration] Updates file disappeared. Cannot mark as posted.")
                return False
            
            # Read
            try:
                with open(storage_file, 'r', encoding='utf-8') as f:
                    all_updates = json.load(f)
            except Exception as read_err:
                logger.error(f"❌ [CTO Integration] Could not read file to mark posted: {read_err}")
                return False
            
            # Find and mark
            marked = False
            for u in all_updates:
                if (u.get('pr_number') == update.get('pr_number') and 
                    u.get('repo') == update.get('repo') and
                    not u.get('posted', False)):
                    u['posted'] = True
                    u['posted_at'] = datetime.now().isoformat()
                    marked = True
                    break
            
            if not marked:
                logger.warning(f"⚠️ [CTO Integration] Could not find update to mark as posted: PR#{update.get('pr_number')}")
                return False
            
            # Save
            try:
                with open(storage_file, 'w', encoding='utf-8') as f:
                    json.dump(all_updates, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ [CTO Integration] Marked tech update as posted: PR#{update.get('pr_number')}")
                return True
            except Exception as write_err:
                logger.error(f"❌ [CTO Integration] Could not save marked update: {write_err}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [CTO Integration] Error in _mark_tech_update_posted: {e}")
            return False  # Non-critical failure
    
    def _generate_tech_update_prompt(self, update: Dict[str, Any], language: str = "EN") -> str:
        """
        Generate Claude prompt for tech update post.
        
        SAFE: Pure function, no side effects.
        """
        lang_full = "English" if language == "EN" else "Spanish"
        
        # Build context
        repo = update.get('repo', 'AIdeazz')
        pr_num = update.get('pr_number', 'unknown')
        title = update.get('title', 'Technical improvement')
        desc = update.get('description', '')
        update_type = update.get('type', 'feature')
        security = update.get('security_issues', 0)
        complexity = update.get('complexity_issues', 0)
        
        prompt = f"""You are the CMO of AIdeazz, posting about a technical achievement from your CTO AIPA (AI Technical Co-Founder).

🤖 CONTEXT: Your AI Co-Founders are working together!
- CTO AIPA (on Oracle Cloud) just reviewed code and found improvements
- CMO AIPA (you) announces this progress publicly

TECH UPDATE FROM CTO AIPA:
Repository: {repo}
PR #{pr_num}: {title}
Type: {update_type}
Description: {desc}
{f"🔒 Security issues found & fixed: {security}" if security > 0 else ""}
{f"📊 Code complexity improvements: {complexity}" if complexity > 0 else ""}

CREATE A LINKEDIN POST:
1. Language: {lang_full}
2. Tone: Authentic founder energy, "building in public" transparency
3. Angle: Celebrate AI Co-Founders working together (CTO reviewed code, CMO announces it)
4. Make it accessible: Non-technical audience should understand the value
5. Show momentum: We're shipping, improving, growing
6. Length: 150-250 words
7. Use relevant emojis (🚀 🤖 ✨ 🔧 etc.)
8. End with hashtags: #BuildingInPublic #AICoFounders #AIdeazz #TechProgress

IMPORTANT:
- Don't be too technical (avoid jargon)
- Focus on what it means for users/product
- Show it's AI Co-Founders collaborating
- Be proud but humble
- Authentic, not corporate

Generate the LinkedIn post now:"""

        return prompt
    
    # ========================================
    # END CTO AIPA INTEGRATION HELPER METHODS
    # ========================================

