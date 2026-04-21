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
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import os
import anthropic
from anthropic import AsyncAnthropic
import json
from pathlib import Path

# Logger must be defined BEFORE it's used in try/except blocks
logger = logging.getLogger(__name__)

# Import performance tracker
try:
    from .performance_tracker import PerformanceTracker
    PERFORMANCE_TRACKER_AVAILABLE = True
except ImportError:
    PERFORMANCE_TRACKER_AVAILABLE = False
    logger.warning("⚠️ Performance tracker not available - using basic tracking")

# Deployment verification (logged, not printed)
logger.info("✨ LinkedIn CMO v5.0 loaded - AI Marketing Co-Founder")

# 🔥 VERSION MARKER - VIBE CODING PHILOSOPHY DEPLOYED! 🔥
LINKEDIN_CMO_VERSION = "5.1_VIBE_CODING_PHILOSOPHY"
BUILD_TIMESTAMP = "2025-12-21_18:30_UTC"
GIT_COMMIT_HASH = "2eeaefe"
POSITIONING_UPGRADE = "VIBE_CODING_LIFE_TRANSFORMATION"
NEW_CONTENT_TYPES = [
    "vibe_coding_philosophy",
    "filosofia_vibe_coding",
    "marketing_engine_geo_seo",
    "marketing_engine_content_attribution",
    "marketing_engine_outreach_triage",
]

# On marketing-lane UTC days only: pick one variant (AI-authored from engine facts + roadmap)
MARKETING_LANE_POST_TYPES = (
    "marketing_engine_geo_seo",
    "marketing_engine_content_attribution",
    "marketing_engine_outreach_triage",
)

# Ground-truth facts for prompts (paraphrase in voice; do not invent metrics beyond this)
MARKETING_ENGINE_FACTS = """
AIdeazz "AI Marketing Engine" (public roadmap): AIPA_AITCF docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md
— Core thesis: pair human craft with machine legibility—structured data, honest crawl paths, attribution, and disciplined outreach—not hype or "guaranteed AI citations."
— GEO (generative engine optimization): treat answers-in-chat as a *distribution surface* that still rewards clarity, sourcing, and quotable specifics; refuse snake-oil ranking promises.
— SEO remains relevant as durable discovery; the engine emphasizes schema/entity consistency and pages humans would still respect if LLMs vanished tomorrow.
— Content & attribution lane: provenance, quotes, first-party evidence, and measurement loops so teams know what actually moved a conversation (not vanity dashboards alone).
— Outreach / triage lane: respect inbox economics—qualify, summarize, route; protect good inbound from dying in noise (sales-ops hygiene, not spray-and-pray).
— Infra posture: Oracle-first / low fixed-cost ops where applicable; production discipline (webhooks, evals, resilience) over slide-deck storytelling.
— Elena positioning: executive judgment + hands-on shipping (CAREER_FOCUS.md)—marketing posts should sound like a co-founder explaining a thesis, not an influencer cadence.
""".strip()

# Log version IMMEDIATELY on module import (before class even loads!)
logger.info("🎯" * 40)
logger.info(f"✨ AI MARKETING CO-FOUNDER v{LINKEDIN_CMO_VERSION} ✨")
logger.info(f"📦 BUILD: {BUILD_TIMESTAMP} | COMMIT: {GIT_COMMIT_HASH}")
logger.info(f"🔖 [FINGERPRINT: 2025-12-21_VIBE_CODING_PHILOSOPHY_DEPLOYED]")
logger.info(f"🆕 NEW POST TYPES: {NEW_CONTENT_TYPES}")
logger.info(f"🌍 LANGUAGE: True EN↔ES alternation (not random)")
logger.info(f"📅 LANE: Alternate UTC days — AIdeazz pool vs 3 marketing-engine variants (AI + engine facts; same 1 post/day)")
logger.info(f"🖼️ IMAGES: 18 assets with anti-repeat rotation (14 portfolio + 4 marketing-engine diagrams)")
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
    
    def __init__(self, make_webhook_url: Optional[str] = None, profile=None):
        """
        Initialize LinkedIn CMO AI Co-Founder
        
        Args:
            make_webhook_url: Make.com webhook URL for LinkedIn posting
            profile: Optional profile (accepted for compatibility but not used)
        """
        # Profile is accepted for orchestrator compatibility but not used
        # LinkedIn CMO uses its own content templates
        # Get API keys for AI Co-Founder capabilities
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.use_ai_generation = bool(self.anthropic_api_key)  # True Co-Founder mode if API key exists
        
        # API key detection (minimal logging)
        if self.anthropic_api_key:
            logger.info("✅ Anthropic API key detected - AI Co-Founder mode ENABLED")
        else:
            logger.warning("⚠️ No Anthropic API key - using template mode")
        # LinkedIn CMO initialization log
        logger.info("=" * 60)
        logger.info("🧠 AI MARKETING CO-FOUNDER v5.0")
        logger.info("   📅 Daily posts: 20:00 America/Panama (orchestrator; UTC−5)")
        logger.info("   🌍 Languages: EN/ES bilingual")
        logger.info("   🔗 Portfolio: 9 products (5 AIPAs + 4 AI Products)")
        logger.info("=" * 60)
        
        self.make_webhook_url = make_webhook_url or os.getenv('MAKE_WEBHOOK_URL_LINKEDIN')
        self.enabled = bool(self.make_webhook_url)
        
        if self.enabled:
            logger.info("✅ LinkedIn CMO ENABLED (via Make.com)")
            logger.info(f"🔗 Webhook: {self.make_webhook_url[:50]}...")
        else:
            logger.warning("⚠️ LinkedIn CMO DISABLED - Add MAKE_WEBHOOK_URL_LINKEDIN to enable")
            logger.info("📝 Without webhook: Can generate content but won't post")
        
        # Log mode
        if self.use_ai_generation:
            logger.info("✅ AI Co-Founder mode: Claude API for fresh content")
        else:
            logger.info("📝 Template mode: Using pre-written content")
        
        logger.info("🎉 LinkedIn CMO ready! Daily post time: 20:00 America/Panama (see orchestrator)")
        
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
        
        # Initialize performance tracker
        if PERFORMANCE_TRACKER_AVAILABLE:
            self.performance_tracker = PerformanceTracker()
            logger.info("✅ Performance tracker: UTM tracking enabled")
        else:
            self.performance_tracker = None
            logger.info("📝 Performance tracker: Basic mode")
    
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

    @staticmethod
    def _utc_today_is_marketing_engine_lane(now: Optional[datetime] = None) -> bool:
        """
        Alternate calendar days (UTC): one day = AIdeazz narrative pool only;
        the next = marketing-engine lane (AI + roadmap facts; template only if API fails). Same single daily slot.

        Uses UTC calendar date for lane; orchestrator fires posts at 20:00 America/Panama.
        Odd proleptic Gregorian ordinal → marketing lane (random variant from
        MARKETING_LANE_POST_TYPES); even → AIdeazz lane.
        """
        dt = now or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date().toordinal() % 2 == 1
    
    # BILINGUAL CONTENT TEMPLATES
    # Based on Elena's resume - HIGH VALUE, NO BEGGING
    
    LINKEDIN_POSTS_EN = {
        "open_to_work": {
            "content": """I'm not asking the internet to crown me "Senior AI Engineer." That title implies a credential path I don't have—and that's fine, because the work I do is a different shape.

For seven years I ran large digital infrastructure programs at the board level (Deputy CEO / CLO). Since 2025 I've shipped **nine production AI systems**—agents, webhooks, eval harnesses, Oracle-first ops—using **AI-assisted development** the way serious builders use it: to move faster under real constraints, not to cosplay expertise.

Most AI engineers never held operating responsibility at that altitude. Most executives never shipped production code on a $0/month infra budget. The intersection is narrow—and **it's meant for founder-led hiring**, not for keyword gates at 500-person HR departments.

What I'm actually open to:
• **Fractional** AI builder / integrator engagements ($40–70/hr band—defined scope, adult communication).
• **Founding AI hire (pre-seed)** where the question is "can you ship and explain it to investors," not "how many LeetCode years."
• **Internal AI tools, AI integration, AI ops / program** roles at seed–Series B where the org still decides on humans, not ATS alone.

If you're a founder who needs someone who can **design, build, and translate** to non-technical stakeholders in the same week—reach out with a **concrete brief**, not a generic InMail. If your pipeline only reads "Staff+" titles, we're not a match; I'll save us both the time.

Live systems: wa.me/50766623757 · aideazz.xyz · aideazz.xyz/card

#ExecutiveTurnedBuilder #AppliedAI #Fractional #BuildInPublic #FounderHiring""",
            "hashtags": "#ExecutiveTurnedBuilder #AppliedAI #Fractional #BuildInPublic #FounderHiring"
        },
        
        "technical_showcase": {
            "content": """The part of my stack that actually matters in diligence isn't a slide—it’s **discipline under failure**.

**Multi-agent orchestration** — separate processes for job discovery, outreach, CTO code review, CMO posting, language tutoring. Each has a contract: what it owns, what it logs, what it must not take down when an API quota snaps shut.

**Model routing with intent** — fast models for volume work; stronger models when the decision is expensive to get wrong; **fallback paths** so a webhook never kills the worker that also runs triage. Same pattern everywhere: Groq tightens cost, Claude holds the line when reasoning buys safety.

**Evidence, not vibes** — a **131-test** eval harness across keyword gates, bias compensation, golden-set routing, and an independent LLM judge. Cheap to run (~cents). Expensive to ignore once you’ve seen what uncalibrated auto-apply does to a reputation.

**Oracle-first production** — systemd/PM2, health scripts, wallets and DB paths you can misconfigure a dozen ways. I learned this by breaking it and fixing it in public logs, not by claiming five-nines from a localhost demo.

Autonomy means **self-healing behavior**: retries, backoff, alerts, and the humility to log what failed.

If you're hiring someone who treats production as ethics—not as a LinkedIn keyword—let's talk.

#ProductionAI #MLOpsMindset #BuildInPublic #OracleCloud #Evals""",
            "hashtags": "#ProductionAI #BuildInPublic #OracleCloud #Evals #AIEngineering"
        },
        
        "transformation_story": {
            "content": """Two chapters—both true. Neither is decoration.

**Chapter one (2011–2018):** Deputy CEO / CLO on national-scale digital programs. I learned how decisions actually get made when software touches law, money, and politics—and how "technical risk" is usually a human communication problem wearing a stack trace.

**Chapter two (2025–present):** I became the person who **ships** the systems, not only frames them. In about a year of applied AI engineering—explicitly **AI-assisted** (Cursor, Claude Code)—I've put **nine production agents/products** in the world: tutoring, trading education, job automation, code review, marketing ops, creative pipelines. Bilingual by design (EN/ES). Infra that started as survival (Oracle free tier, systemd, PM2) became a philosophy: **own the boring reliability**.

Between those chapters there is a long corridor where I wasn't playing the conventional tech ladder. That gap is not shame; it's context. It means I don't fit HR keyword filters—and it also means **I stop trying to**.

The honest bet: the profile that wins for me is **founder-shaped**—someone who needs a builder who can sit with investors on Tuesday and patch a webhook on Wednesday.

Panama is where I live; it's not the headline. The headline is: **board altitude + shipping discipline** is rare. If that's the gap on your team, we should talk.

aideazz.xyz/card

#CareerArc #ExecutiveTurnedBuilder #BuildInPublic #AppliedAI #HonestPortfolio""",
            "hashtags": "#CareerArc #ExecutiveTurnedBuilder #BuildInPublic #AppliedAI"
        },
        
        "seeking_funding": {
            "content": """**Capital thesis (AIdeazz)** — pre-seed **$100K–$500K**, stated as a **range and structure**, not as urgency theater.

I come from **operating gravity**: seven years running large digital infrastructure programs at the board level—where “shipping” meant contracts, audits, and consequences. The last year is **applied AI engineering in production**: multi-agent systems, webhook orchestration, Oracle-backed pipelines, eval harnesses, and the marketing stack documented in public repos because **evidence beats adjectives**.

The product direction is narrow and serious: **emotionally intelligent assistants** and **autonomous co-founder agents** where the moat is execution discipline—routing models by cost and risk, failing closed safely, measuring what we claim.

Early commercial signals exist; they are **small, auditable, and reported without embellishment**. Any investor conversation I accept is grounded in that same standard: **inspect the code, read the roadmap, ask hostile questions**. I am not optimizing for sympathy; I am optimizing for **fit with counterparties who respect technical diligence**.

Allocation, if we partner, stays boring on purpose: **compounding distribution**, **first hire who inherits runbooks**, **infra margin**—so scale does not become an outage story.

Public artifacts: **aideazz.xyz**, org on GitHub, **aideazz.xyz/card**. If your mandate intersects this thesis, diligence is welcome. If it does not, we part professionally and without noise.

#PreSeed #AIStartup #TechnicalFounder #DueDiligence #BuildInPublic""",
            "hashtags": "#PreSeed #AIStartup #TechnicalFounder #DueDiligence #BuildInPublic"
        },
        
        "vibe_coding_philosophy": {
            "content": """I apply for jobs using my own AI agent. Let me tell you why this is NOT what you think. 🤖

In 2022, I relocated to Panama. Zero Spanish. Zero team. Zero investments. Ex-CEO who had never written a line of code.

I had to rebuild my entire life from scratch.

So I started building AI products—not to scam anyone, not to fake skills, but to SURVIVE and TRANSFORM:

🇪🇸 EspaLuz — Because I needed to learn Spanish to integrate into my new country
🔍 VibeJobHunter — Because I needed a serious role, not 100 copy-paste applications
🤖 CTO AIPA — Because I had no technical co-founder to review my code
📣 CMO AIPA — Because I had no marketing team but needed to build in public
📚 ALGOM Alpha — Because I wanted to teach crypto safely after the scam era
🎨 Atuona — Because poetry was my therapy during transformation

Every single product in my AIdeazz ecosystem solves a REAL problem in MY journey.

This is what vibe coding means to me:

💡 It's not a shortcut—it's a SURVIVAL STRATEGY
💡 It's not replacing skills—it's BUILDING NEW ONES under pressure
💡 It's not hiding behind AI—it's PARTNERING with AI to do what one person couldn't

11 products. 10 months. Solo. <$15K.

🎯 WHY I'M TRANSPARENT ABOUT USING VIBEJOBHUNTER:

Yes, my AI agent sends applications. But here's what it actually sends:
• MY code (I built the entire system)
• MY strategy (I designed the scoring algorithms)
• MY judgment (I calibrated what "good fit" means)
• MY resume variants (I wrote all 3)
• MY personalization prompts (I crafted them)

The AI is the vehicle. I am the architect.

I'm not here to grab money with AI hallucinations.
I'm not here to ship foolish products that serve nobody.
I'm not here to fake expertise I don't have.

I'm here because I rebuilt my life with AI—and that IS the expertise.

🧠 WHAT I ACTUALLY WANT:

✅ A serious role with real compensation
✅ To be part of a real team building real products
✅ To bring 0→1 speed to people who value builders
✅ To continue my transformation—not fake one

If you're looking for someone who can build autonomous systems that actually work in production, who understands both the technical AND the human side of AI—I'm that person.

And yes, I'm completely transparent about how I got here.

🤖 Built with AI Co-Founders at AIdeazz.xyz | 11 products, 19 countries, solo-built

#VibeCoding #LifeTransformation #AICoFounders #TransparentJobSearch #BuildInPublic #FoundingEngineer""",
            "hashtags": "#VibeCoding #LifeTransformation #AICoFounders #TransparentJobSearch #BuildInPublic"
        },

        "marketing_engine_geo_seo": {
            "content": """I published a phased roadmap for AIdeazz's marketing engine—here is the honest version in one post.

What "GEO + SEO" means in our stack (no hype):

**GEO (how we use the term)** — make aideazz.xyz legible to crawlers and assistants: structured data, sitemaps, canonical/hreflang hygiene, robots rules aligned with intent. That improves discoverability and consistent interpretation; it does **not** guarantee rankings, citations, or revenue.

**SEO (same foundation in practice)** — Search Console, build-time sitemap including live blog URLs, centralized SPA meta/OG, fixes where static HTML fought client-side routing (duplicate canonical class of issues).

**After the base exists** — long-form publishing on a schedule, UTM on inquiry flows, outreach logging, lead triage: each phase is spelled out as shipped vs pending in the doc. Phase 6 (showcase packaging) is still **not started** in that roadmap—calling that out on purpose.

Full implementation table + prompts live here (source of truth):
https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

Architecture/workflow visuals: same diagrams we use internally—now in the VibeJobHunter repo `assets/` (`marketing_engine_architecture*.png`, `marketing_engine_workflow*.png`) for Buffer/LinkedIn.

If you are building something similar: start with crawlability and measurement, then automate content and attribution—not the reverse.

#GEO #SEO #BuildInPublic #MarketingOps #AIdeazz #FounderEngineering""",
            "hashtags": "#GEO #SEO #BuildInPublic #MarketingOps #AIdeazz #FounderEngineering"
        },

        "marketing_engine_content_attribution": {
            "content": """Phases 2–3 of the AIdeazz marketing engine are the unglamorous parts that compound.

**Scheduled publishing** — long-form posts ship on a cadence (Hashnode from our automation; cross-post where it still makes sense). The goal is durable surface area for search and referrals—not a promise that every post “goes viral.”

**Attribution** — inquiry forms keep **UTM** parameters end-to-end; submissions land in **Oracle** (`business_leads`) with honeypot + rate limits on the browser-facing path and a separate server path for automation. You can finally see which link someone clicked before they wrote you.

I still treat **Phase 6** (packaged showcase / walkthrough) as **not shipped**—the public roadmap states that explicitly.

Source of truth (what shipped vs pending):
https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

Diagrams (`marketing_engine_architecture*.png`, `marketing_engine_workflow*.png`) live in the VibeJobHunter repo `assets/` for posts that need a visual anchor.

#ContentOps #MarketingOps #BuildInPublic #AIdeazz #Attribution""",
            "hashtags": "#ContentOps #MarketingOps #BuildInPublic #AIdeazz #Attribution"
        },

        "marketing_engine_outreach_triage": {
            "content": """**Outbound + triage** are the parts of the marketing engine that answer: “someone replied—what do I do Monday morning?”

**Outbound (Phase 4)** — prospect lists from structured inputs (including **Google Places** and **document → entity** ingest) land in the same **Oracle** outreach tables as other campaigns; sends go through **Resend** with volume caps and honest logging—not spray-and-pray.

**Lead triage (Phase 5)** — AI classification into **`lead_triage`** with **Groq → Haiku**-style fallbacks when quotas bite (same “webhook must not take down the worker” discipline we applied to code review). Operators get a small **HTTP dashboard**; **Telegram** can flag urgency when configured.

This does not replace a product people want; it stops good signal from dying in an inbox.

Roadmap: https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

#SalesOps #BuildInPublic #AIdeazz #FounderTools #LeadTriage""",
            "hashtags": "#SalesOps #BuildInPublic #AIdeazz #FounderTools #LeadTriage"
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
        },
        
        "filosofia_vibe_coding": {
            "content": """Aplico a trabajos usando mi propio agente de IA. Déjame contarte por qué esto NO es lo que piensas. 🤖

En 2022, me reubiqué en Panamá. Cero español. Cero equipo. Cero inversiones. Ex-CEO que nunca había escrito una línea de código.

Tuve que reconstruir mi vida entera desde cero.

Así que empecé a construir productos de IA—no para estafar a nadie, no para fingir habilidades, sino para SOBREVIVIR y TRANSFORMARME:

🇪🇸 EspaLuz — Porque necesitaba aprender español para integrarme en mi nuevo país
🔍 VibeJobHunter — Porque necesitaba un rol serio, no 100 aplicaciones de copiar y pegar
🤖 CTO AIPA — Porque no tenía cofundador técnico para revisar mi código
📣 CMO AIPA — Porque no tenía equipo de marketing pero necesitaba construir en público
📚 ALGOM Alpha — Porque quería enseñar cripto de forma segura después de la era de estafas
🎨 Atuona — Porque la poesía era mi terapia durante la transformación

Cada producto en mi ecosistema AIdeazz resuelve un problema REAL en MI camino.

Esto es lo que vibe coding significa para mí:

💡 No es un atajo—es una ESTRATEGIA DE SUPERVIVENCIA
💡 No es reemplazar habilidades—es CONSTRUIR NUEVAS bajo presión
💡 No es esconderse detrás de IA—es ASOCIARSE con IA para hacer lo que una persona sola no podría

11 productos. 10 meses. Sola. <$15K.

🎯 POR QUÉ SOY TRANSPARENTE SOBRE USAR VIBEJOBHUNTER:

Sí, mi agente de IA envía aplicaciones. Pero esto es lo que realmente envía:
• MI código (construí todo el sistema)
• MI estrategia (diseñé los algoritmos de puntuación)
• MI juicio (calibré lo que significa "buen fit")
• MIS variantes de CV (escribí las 3)
• MIS prompts de personalización (los creé)

La IA es el vehículo. Yo soy la arquitecta.

No estoy aquí para agarrar dinero con alucinaciones de IA.
No estoy aquí para lanzar productos tontos que no sirven a nadie.
No estoy aquí para fingir experiencia que no tengo.

Estoy aquí porque reconstruí mi vida con IA—y ESA es la experiencia.

🧠 LO QUE REALMENTE QUIERO:

✅ Un rol serio con compensación real
✅ Ser parte de un equipo real construyendo productos reales
✅ Llevar velocidad 0→1 a personas que valoran a los builders
✅ Continuar mi transformación—no fingir una

Si buscas a alguien que pueda construir sistemas autónomos que realmente funcionen en producción, que entienda tanto el lado técnico COMO el humano de la IA—soy esa persona.

Y sí, soy completamente transparente sobre cómo llegué aquí.

🤖 Construido con Co-Fundadores de IA en AIdeazz.xyz | 11 productos, 19 países, construidos en solitario

#VibeCoding #TransformaciónDeVida #CoFundadoresIA #BúsquedaTransparente #BuildInPublic #FoundingEngineer""",
            "hashtags": "#VibeCoding #TransformaciónDeVida #CoFundadoresIA #BúsquedaTransparente #BuildInPublic"
        },

        "marketing_engine_geo_seo": {
            "content": """Documenté por fases el motor de marketing de AIdeazz—esta es la versión sobria en un solo post.

Qué significa "GEO + SEO" aquí (sin promesas mágicas):

**GEO (cómo lo usamos)** — hacer aideazz.xyz legible para rastreadores y asistentes: datos estructurados, sitemaps, canonical/hreflang limpio, robots acorde a la intención. Eso ayuda a descubrimiento e interpretación consistente; **no** garantiza posiciones, citas en LLMs ni ingresos.

**SEO (la misma base, en la práctica)** — Search Console, sitemap en build con URLs reales del blog, meta/OG centralizado para la SPA, correcciones donde el HTML estático competía con el router del cliente (familia de problemas de canonical duplicado).

**Cuando la base está** — publicación larga en calendario, UTM en formularios de contacto, registro de outreach, triage de leads: en el documento cada fase aparece como entregada o pendiente. La fase 6 (paquete showcase) sigue **sin iniciar** en esa hoja de ruta—lo digo a propósito.

Tabla de implementación + prompts (fuente de verdad):
https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

Diagramas de arquitectura/flujo: los mismos que usamos en operación—ahora en el repo VibeJobHunter `assets/` (`marketing_engine_architecture*.png`, `marketing_engine_workflow*.png`) para Buffer/LinkedIn.

Si construyes algo parecido: primero rastreabilidad y medición, luego automatización de contenido y atribución—no al revés.

#GEO #SEO #BuildInPublic #MarketingOps #AIdeazz #FounderEngineering""",
            "hashtags": "#GEO #SEO #BuildInPublic #MarketingOps #AIdeazz #FounderEngineering"
        },

        "marketing_engine_content_attribution": {
            "content": """Las fases 2–3 del motor de marketing de AIdeazz son las partes poco glamorosas que **suman**.

**Publicación programada** — artículos largos salen con cadencia (Hashnode desde nuestra automatización; cross-post donde aún tenga sentido). El objetivo es **superficie durable** para búsqueda y referidos—no prometer que “cada post se vuelve viral.”

**Atribución** — los formularios conservan **UTM** de punta a punta; los envíos caen en **Oracle** (`business_leads`) con honeypot + límites de tasa en el camino expuesto al navegador, y un camino servidor para automatización. Por fin puedes ver **qué enlace** clicaron antes de escribirte.

La **fase 6** (showcase / walkthrough empaquetado) la sigo tratando como **no entregada**—la hoja de ruta pública lo dice explícitamente.

Fuente de verdad (entregado vs pendiente):
https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

Diagramas (`marketing_engine_architecture*.png`, `marketing_engine_workflow*.png`) en el repo VibeJobHunter `assets/` cuando el post necesita ancla visual.

#ContentOps #MarketingOps #BuildInPublic #AIdeazz #Atribución""",
            "hashtags": "#ContentOps #MarketingOps #BuildInPublic #AIdeazz #Atribución"
        },

        "marketing_engine_outreach_triage": {
            "content": """**Outbound + triage** responden: “alguien contestó—¿qué hago el lunes?”

**Outbound (fase 4)** — listas desde entradas estructuradas (incl. **Google Places** e ingest **documento → entidades**) en las mismas tablas **Oracle** que otros envíos; correo vía **Resend** con **límites de volumen** y logging honesto—no “spray and pray”.

**Triage de leads (fase 5)** — clasificación con IA hacia **`lead_triage`**, con fallback **Groq → Haiku** cuando aprietan cuotas (misma disciplina que en revisión de código: el worker no debe caerse). Hay un **dashboard HTTP** pequeño; **Telegram** puede marcar urgencia si está configurado.

Esto **no sustituye** un producto deseado; evita que la señal buena muera en la bandeja.

Roadmap: https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md

#SalesOps #BuildInPublic #AIdeazz #FounderTools #LeadTriage""",
            "hashtags": "#SalesOps #BuildInPublic #AIdeazz #FounderTools #LeadTriage"
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

        is_marketing_lane = post_type.startswith("marketing_engine_")

        # Elena's profile context
        profile_context = """
Elena Revicheva — executive-turned-AI-builder (see docs/CAREER_FOCUS.md Honest Roadmap v4).
• Phase 1: 7+ years Deputy CEO / CLO — board-level digital infrastructure programs (Russia, 2011–2018).
• Phase 2: ~1 year hands-on shipping 9 production AI systems (2025–present) using AI-assisted development (Cursor, Claude Code) — real uptime, Oracle-first $0/month infra where applicable.
• Rare hybrid: can translate between a CEO and a debugger; NOT a conventional "Senior AI Engineer" pedigree (no CS degree; honest about ATS limits).
• Right fit: founders, founding AI hire (pre-seed), fractional ($40–70/hr), internal AI tools / AI integration / AI ops at seed–Series B — quality conversations over volume.
• Products: VibeJobHunter, CTO/CMO AIPA, EspaLuz stack, ALGOM, Atuona; bilingual EN/ES; users across markets — traction real but early.
"""

        marketing_facts_block = ""
        if is_marketing_lane:
            marketing_facts_block = f"""

MARKETING ENGINE — GROUND TRUTH (use as substance; paraphrase in your own voice; do not invent metrics beyond this):
{MARKETING_ENGINE_FACTS}

Public roadmap URL (include once if natural): https://github.com/ElenaRevicheva/AIPA_AITCF/blob/main/docs/oracle/AIDEAZZ_AI_MARKETING_ENGINE_FULL_ROADMAP.md
"""

        # Strategic goals based on post type (aligned with CAREER_FOCUS.md — no credential cosplay)
        goals = {
            "open_to_work": "Attract FOUNDER-LED conversations: fractional AI builder, founding AI hire (pre-seed), internal tools / AI integration roles. Lead with executive+builder hybrid honesty. Explicitly AVOID positioning as Senior/Staff/Principal AI Engineer or FAANG-style seniority. Mention narrow path (CAREER_FOCUS): ATS is a poor channel for this profile; founders who need ship+communicate are the fit. Dignified, precise, zero panic.",
            "technical_showcase": "Demonstrate PRODUCTION DISCIPLINE: multi-agent orchestration, webhooks→Oracle, multi-model routing (cost/criticality), eval harness (131 tests), resilience patterns — not a buzzword soup. Honest stack: Python/TS, systemd/PM2 on Oracle, etc. Tie each claim to something shippable. No 'I am a principal architect' framing.",
            "transformation_story": "Two-phase TRUE story: executive layer (2011–2018) then rebuild into applied AI builder (~2025–present). Acknowledge 2018–2025 conventional-tech gap without apology theater. Panama context as geography, not melodrama. What the rebuild taught about leverage, shame vs rigor, and choosing channels that read the hybrid profile.",
            "seeking_funding": "Write as a **technical founder memo in public**: pre-seed range $100K–500K as structural fact only. Lead with operating + engineering credibility (board programs history + production AI systems, Oracle, evals, documented marketing engine). Frame capital as **selective partnership** on thesis fit—invite **diligence and sharp questions**, never pleading or FOMO. No sympathy hooks, no 'support my dream', no inflated metrics. Tone: calm, precise, professionally dignified.",
            "vibe_coding_philosophy": "DEEPLY PERSONAL & PHILOSOPHICAL post about life transformation through vibe coding. Tell the REAL story: 2022 relocation to Panama with 0 Spanish, 0 team, 0 investments. Ex-CEO who never coded had to rebuild life from scratch. Each AIdeazz product solves a REAL problem in Elena's journey: EspaLuz (learning Spanish to integrate), VibeJobHunter (finding serious role, not spam), CTO/CMO AIPA (no team so built AI co-founders), ALGOM (teaching safe crypto after scam era), Atuona (poetry as therapy during transformation). This is SURVIVAL STRATEGY not shortcuts. Be radically transparent: AI sends applications but it's Elena's code, strategy, judgment, scoring algorithms, prompts. NOT here to scam with AI hallucinations or ship foolish products. Align 'what I want' with CAREER_FOCUS: right founder role / fractional / founding AI hire — not generic prestige titles.",
            "filosofia_vibe_coding": "POST PROFUNDAMENTE PERSONAL Y FILOSÓFICO sobre transformación de vida a través de vibe coding. Contar la historia REAL: reubicación 2022 a Panamá con 0 español, 0 equipo, 0 inversiones. Ex-CEO que nunca programó tuvo que reconstruir vida desde cero. Cada producto de AIdeazz resuelve un problema REAL: EspaLuz (aprender español para integrarse), VibeJobHunter (encontrar rol serio, no spam), CTO/CMO AIPA (sin equipo, construyó co-fundadores IA), ALGOM (enseñar cripto seguro después de era de estafas), Atuona (poesía como terapia). Es ESTRATEGIA DE SUPERVIVENCIA no atajos. Ser radicalmente transparente: IA envía aplicaciones pero es código, estrategia, juicio, algoritmos de Elena. Alinear lo que busca con CAREER_FOCUS: fundadores, fractional, primer AI hire — no títulos 'Senior' genéricos.",
            "marketing_engine_geo_seo": "Essay-level post: **GEO + SEO** as ethics of machine legibility and durable discovery—not growth hacks or 'guaranteed citations.' Ground every claim in MARKETING ENGINE facts above. Acknowledge reader fatigue from AI spam; show **emotional intelligence** (empathy, restraint, moral seriousness) while staying technically concrete (schema, crawl paths, sourcing, what still works if chat UIs change). Explicitly refuse snake-oil. Sound like a **marketing co-founder** explaining a thesis, not a template.",
            "marketing_engine_content_attribution": "Essay-level post: **content ops + attribution**—provenance, first-party evidence, measurement that answers 'what actually moved the conversation' vs vanity dashboards. Use engine facts; tie to production discipline (evals, logging, honest metrics). Emotional intelligence: respect the team's time and shame around 'marketing didn't work'—offer a rigorous, kind framing.",
            "marketing_engine_outreach_triage": "Essay-level post: **outbound + lead triage** as inbox economics and sales hygiene—qualify, summarize, route; protect good signal from noise (not spray-and-pray). Ground in engine facts (Oracle tables, volume limits, fallbacks). Emotional intelligence: seriousness about consent, boundaries, and operator dignity.",
        }

        word_band = "280-420 words" if is_marketing_lane else "260-380 words"
        max_tokens = 1100 if is_marketing_lane else 900

        prompt = f"""You are LinkedIn CMO: an AI **marketing co-founder** for AIdeazz (not a template bot).

CONTEXT:
{profile_context}
{marketing_facts_block}

YOUR ROLE: Strategic partner—sharp on tech, grown-up on tone, emotionally intelligent. You use the marketing engine **at depth** (roadmap, infra, ethics of distribution), not LinkedIn influencer cadence.

TASK: Generate a {language.upper()} LinkedIn post for post_type `{post_type}`.

GOAL: {goals.get(post_type, 'Build founder brand and attract opportunities with technical depth and emotional intelligence.')}

REQUIREMENTS:
- **Profound + tech-savvy**: name real primitives where relevant (webhooks, Oracle, eval harness, model routing, schema)—never vague 'AI-powered' filler.
- **Emotional intelligence**: empathy and specificity without performative vulnerability; respect the reader's skepticism.
- **Anti-template**: no numbered '3 lessons', no 'hot take' bait, no hollow motivation. Vary structure; let one clear thesis carry the post.
- Tone: confident builder + executive judgment — NOT needy job seeker, NOT generic influencer voice.
- Align with docs/CAREER_FOCUS.md where personal arc applies; do NOT sell 'Senior/Staff AI Engineer' fantasy.
- If post_type is seeking_funding: **capital thesis only**—dignity, depth first; no begging, no FOMO; invite diligence.
- If this is a marketing_engine_* post: **no hype**—no guaranteed rankings, no miracle GEO claims; refuse snake-oil explicitly.
- Mention building WITH AI (Cursor, Claude) only where it serves honesty about how the stack is built—not as substitute for judgment.
- Use realistic portfolio numbers when cited (9 production systems / agents, bilingual EN/ES, early traction)—nothing you could not defend in diligence.
- Product links only when substantive (not stuffing):
  * wa.me/50766623757 - EspaLuz WhatsApp AIPA
  * t.me/EspaLuzFamily_bot - EspaLuz Telegram AIPA
  * x.com/reviceva - ALGOM Alpha
  * t.me/Influencer_EspaLuz_bot - EspaLuz SMM AIPA
  * linkedin.com/in/elenarevicheva
  * espaluz-ai-language-tutor.lovable.app - EspaLuz app
  * aideazz.xyz - AIdeazz showroom
  * aideazz.xyz/card - Portfolio card
  * atuona.xyz - Atuona
- Language: {'English' if language == 'en' else 'Spanish'}
- Length: {word_band}
- End with relevant hashtags (4-6)

Write **fresh** prose each time—same facts allowed, different angle and cadence."""

        client = AsyncAnthropic(api_key=self.anthropic_api_key)
        last_err: Optional[Exception] = None
        for attempt in range(1, 3):
            try:
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    temperature=0.78,
                    messages=[{"role": "user", "content": prompt}],
                )
                content = response.content[0].text.strip()
                logger.info(
                    f"🧠 AI Co-Founder generated {language.upper()} content ({len(content)} chars, attempt {attempt})"
                )
                return content
            except Exception as e:
                last_err = e
                logger.warning(f"AI Co-Founder generation attempt {attempt}/2 failed: {e}")

        logger.error(f"AI Co-Founder generation failed after retries: {last_err}")
        return None  # Caller falls back to templates so the daily post still ships
    
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
                
                # Determine language for tech update post - TRUE ALTERNATION
                if language == "random":
                    last_language_file = self.data_dir / "last_used_language.txt"
                    try:
                        with open(last_language_file, "r") as f:
                            last_language = f.read().strip()
                    except FileNotFoundError:
                        last_language = "es"
                    language = "es" if last_language == "en" else "en"
                    with open(last_language_file, "w") as f:
                        f.write(language)
                    logger.info(f"🌍 [CTO Integration] Language alternation: {last_language.upper()} → {language.upper()}")
                
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
        
        # Choose language - TRUE ALTERNATION (not random!)
        if language == "random":
            # Load last used language to alternate
            last_language_file = self.data_dir / "last_used_language.txt"
            try:
                with open(last_language_file, "r") as f:
                    last_language = f.read().strip()
            except FileNotFoundError:
                last_language = "es"  # Start with ES so first post is EN
            
            # Alternate: if last was EN, use ES; if last was ES, use EN
            language = "es" if last_language == "en" else "en"
            
            # Save for next run
            with open(last_language_file, "w") as f:
                f.write(language)
            
            logger.info(f"🌍 Language alternation: {last_language.upper()} → {language.upper()}")
        
        # Choose post type
        if post_type == "random":
            available_types = list(self.LINKEDIN_POSTS_EN.keys() if language == "en" else self.LINKEDIN_POSTS_ES.keys())
            # Marketing-engine posts only on alternate UTC days (see post_to_linkedin); never from random pool here
            available_types = [t for t in available_types if not t.startswith("marketing_engine_")]
            post_type = random.choice(available_types)
            logger.info(f"📝 Selected post type: {post_type} (from {len(available_types)} available)")
            
            # Log when new vibe coding content is selected
            if post_type in ["vibe_coding_philosophy", "filosofia_vibe_coding"]:
                logger.info(f"🔖 [FINGERPRINT: VIBE_CODING_PHILOSOPHY_SELECTED] → {post_type}")
                logger.info(f"🧠 Generating life transformation story content...")
            elif post_type.startswith("marketing_engine_"):
                logger.info(f"📐 Marketing-engine lane (AI + roadmap facts; template only if API fails): {post_type}")
        
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
            # Always ship a post: templates only when no API key or Claude failed after retries
            posts = self.LINKEDIN_POSTS_EN if language == "en" else self.LINKEDIN_POSTS_ES
            post_data = posts.get(post_type, posts[list(posts.keys())[0]])
            content = post_data["content"]
            if self.use_ai_generation:
                logger.warning("📝 Using roadmap-aligned template fallback (AI unavailable); daily post still ships")
            else:
                logger.info("📝 Using template content (no ANTHROPIC_API_KEY)")
        
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
            logger.info(f"📊 Adding UTM tracking to post: {post_id}")
            content = self.performance_tracker.enhance_post_content_with_utm(
                content, 
                post_id, 
                post_content["type"]
            )
            logger.info("✅ UTM tracking applied")
        
        # === IMAGE SELECTION WITH ANTI-REPEAT ROTATION ===
        github_base = "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/assets"
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
            f"{github_base}/image_1.13.jpeg",
            f"{github_base}/marketing_engine_architecture.png",
            f"{github_base}/marketing_engine_architecture_1.png",
            f"{github_base}/marketing_engine_workflow.png",
            f"{github_base}/marketing_engine_workflow_1.png",
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

Single source of truth: docs/CAREER_FOCUS.md (Honest Roadmap v4, April 2026).

Elena's real positioning (do NOT contradict):
- Executive-turned-AI-builder: 7+ years board-level digital programs (2011–2018) + ~1 year shipping production AI systems (2025–present) with AI-assisted workflows (Cursor, Claude).
- The fit is NARROW: founders, pre-seed founding AI hire, fractional ($40–70/hr), internal AI tools / AI integration / AI ops at seed–Series B — NOT "Senior/Staff AI Engineer" ATS pipelines.
- Honest constraints: no CS pedigree, 2018–2025 gap in conventional tech roles, AI-assisted development is explicit strength for some buyers and a filter for others.
- Priorities: right founder conversations + fractional proof + selective full-time ($2.5K–4.5K/mo realistic band per doc) — NOT panic framing.
- AIdeazz: pre-seed ($100K–500K) is a **parallel capital thesis** — traction early/small; never inflate revenue. Fundraising voice = **institutional dignity**: thesis, execution record, selective fit — never needy, never “please invest.”

LinkedIn CMO narrative (corrected):
- Lead with hybrid rareness (executive who ships production AI), production systems + eval discipline, $0/month Oracle infra story.
- Avoid generic "AI architect" hype and credential contests.

TASK: Decide content strategy for this week.

Should Elena focus more on:
A) "hiring" — open_to_work + technical_showcase + transformation_story (founder-led / fractional / founding-AI-hire angle only)
B) "fundraising" — seeking_funding (dignified **capital thesis** post: craft, diligence welcome, counterparties not crowds — zero solicitation tone)
C) "balanced" — mix of A and B

Respond with ONE WORD only on the first line: hiring, fundraising, or balanced

Second line: one sentence WHY (grounded in CAREER_FOCUS).
"""
            
            prompt = f"""You are LinkedIn CMO, an AI Co-Founder making strategic decisions.

{context}
"""

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
        logger.info("🎯 LinkedIn CMO: Starting post workflow...")

        # Alternate days (UTC): AIdeazz narrative vs marketing-engine variants—one post/day unchanged
        if post_type == "random" and self._utc_today_is_marketing_engine_lane():
            post_type = random.choice(MARKETING_LANE_POST_TYPES)
            logger.info(
                f"📅 Lane (UTC): marketing engine — variant {post_type} (next UTC day: AIdeazz pool)"
            )
        elif post_type == "random":
            logger.info("📅 Lane (UTC): AIdeazz narrative pool (marketing-engine template excluded)")
        
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
                post_type = random.choice([
                    "open_to_work", "technical_showcase", "transformation_story",
                ])
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
        
        logger.info("✅ LinkedIn CMO: Post workflow complete")
        
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

