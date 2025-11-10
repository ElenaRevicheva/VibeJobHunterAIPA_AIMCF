"""
Role-specific resume optimizations
Emphasizes different strengths based on target role
"""
from typing import Dict


class RoleSpecificResumeOptimizer:
    """Optimize resume emphasis based on role type"""
    
    def __init__(self):
        self.role_templates = {
            "founding_engineer": self._founding_engineer_emphasis,
            "ai_product_manager": self._ai_pm_emphasis,
            "llm_engineer": self._llm_engineer_emphasis,
            "ai_solutions_architect": self._architect_emphasis,
            "ai_growth_engineer": self._growth_engineer_emphasis,
            "full_stack_ai_engineer": self._full_stack_emphasis,
        }
    
    def get_role_emphasis(self, job_title: str) -> Dict[str, str]:
        """
        Get specific emphasis sections based on job title
        
        Returns:
            {
                "summary": "Role-specific summary",
                "top_skills": [...],
                "key_projects": [...],
                "emphasis_points": [...]
            }
        """
        job_title_lower = job_title.lower()
        
        # Detect role type
        if any(keyword in job_title_lower for keyword in ["founding engineer", "founding"]):
            return self._founding_engineer_emphasis()
        elif any(keyword in job_title_lower for keyword in ["product manager", "pm", "product"]):
            return self._ai_pm_emphasis()
        elif any(keyword in job_title_lower for keyword in ["llm", "language model"]):
            return self._llm_engineer_emphasis()
        elif any(keyword in job_title_lower for keyword in ["architect", "solutions architect"]):
            return self._architect_emphasis()
        elif any(keyword in job_title_lower for keyword in ["growth", "growth engineer"]):
            return self._growth_engineer_emphasis()
        else:
            return self._full_stack_emphasis()
    
    def _founding_engineer_emphasis(self) -> Dict[str, str]:
        """Emphasis for Founding Engineer roles"""
        return {
            "summary": """AI-First Founder & Engineer building emotionally intelligent AI products. 
            Solo-built 2 live AI agents with paying users in 19 countries. Ex-CEO & CLO bringing 
            7 years executive strategy + hands-on AI engineering. 0→1 builder with proven traction: 
            PayPal subscriptions active, 98% cost reduction, 10x faster execution.""",
            
            "top_skills": [
                "0→1 Product Development (6 apps in 7 months)",
                "Live Product Traction (19 countries, paying users)",
                "Revenue Generation (PayPal subscriptions active)",
                "Cost-Efficient Execution (98% reduction vs traditional)",
                "Full-Stack AI (Claude, GPT, Whisper, TTS, ElizaOS)",
                "Product Strategy (Ex-CEO perspective)",
                "Python, TypeScript, React",
                "Bilingual Product (EN/ES dual-sided market)"
            ],
            
            "key_projects": [
                "EspaLuz - AI Spanish Tutor: LIVE with paying users in 19 countries. PayPal subscriptions active. Bilingual EN/ES architecture.",
                "ALGOM Alpha - AI Crypto Mentor: Autonomous AI agent on X teaching safe trading. 24/7 operation.",
                "6 production apps in 7 months for <$15K (98% cost reduction vs $900K traditional estimate)"
            ],
            
            "emphasis_points": [
                "💎 Founding engineer on own products (not just employee)",
                "💰 Revenue-generating (PayPal subs), not just demo",
                "🚀 Proven execution speed (6 apps in 7 months)",
                "🌍 International scale (19 countries reach)",
                "🎯 PMF proof (paying customers returning)",
                "💬 Live demo: wa.me/50766623757"
            ]
        }
    
    def _ai_pm_emphasis(self) -> Dict[str, str]:
        """Emphasis for AI Product Manager roles"""
        return {
            "summary": """AI Product Manager & Builder with exec background. Ex-CEO & CLO bringing 7 years 
            of product strategy + hands-on AI engineering. Solo-built 2 live AI products with paying users 
            in 19 countries. Unique: can define product vision AND build it. 0→1 specialist with proven GTM: 
            PayPal subscriptions live, organic growth to 19 countries.""",
            
            "top_skills": [
                "Product Strategy (Ex-CEO, 7 years exec)",
                "0→1 Product Development (concept → revenue)",
                "GTM Execution (19 countries, organic growth)",
                "Monetization (PayPal subscriptions active)",
                "User Research (bilingual EN/ES markets)",
                "Technical Product Management (can code)",
                "AI/ML Product Design",
                "Cross-functional Leadership"
            ],
            
            "key_projects": [
                "EspaLuz Product Strategy: Identified dual-sided market (expats + locals). Built bilingual AI tutor. Achieved 19-country reach with zero marketing budget.",
                "Monetization: Launched PayPal subscriptions. Recurring revenue model proven.",
                "Product-Led Growth: Organic expansion through WhatsApp/Telegram. Viral coefficient >1.0."
            ],
            
            "emphasis_points": [
                "🎯 Product Manager who can build (rare combo)",
                "📊 Strategic thinking (7 years exec) + execution",
                "💰 Proven monetization (PayPal subs live)",
                "🌍 International product (19 countries)",
                "👥 User-centric (bilingual, emotionally intelligent AI)",
                "💬 Live product: wa.me/50766623757"
            ]
        }
    
    def _llm_engineer_emphasis(self) -> Dict[str, str]:
        """Emphasis for LLM Engineer roles"""
        return {
            "summary": """LLM Engineer with production experience building emotionally intelligent AI assistants. 
            2 live AI agents using Claude, GPT, Whisper in production. Specialized in conversational AI, 
            multi-language support (EN/ES), and context management. Built persistent memory system, 
            emotion detection, and voice synthesis integration. Real users in 19 countries.""",
            
            "top_skills": [
                "LLM Integration (Claude, GPT in production)",
                "Prompt Engineering (conversational AI)",
                "Multi-language Support (EN/ES)",
                "Context Management (persistent memory)",
                "Voice AI (Whisper, TTS synthesis)",
                "RAG & Embeddings",
                "Production AI Systems (99%+ uptime)",
                "Python, LangChain, ElizaOS"
            ],
            
            "key_projects": [
                "EspaLuz LLM Architecture: Claude for emotional intelligence, GPT for structured responses. Bilingual prompt engineering (EN/ES). Persistent memory across sessions.",
                "Voice Integration: Whisper (speech-to-text) + TTS (text-to-speech). Real-time conversation handling.",
                "Context Management: Built memory system tracking emotional state, learning preferences, conversation history."
            ],
            
            "emphasis_points": [
                "🤖 Production LLM experience (not just demos)",
                "🗣️ Voice + text AI (Whisper, TTS, OCR)",
                "🧠 Persistent memory & emotional intelligence",
                "🌍 Bilingual LLM (EN/ES) handling",
                "⚡ Production-grade (99%+ uptime, real users)",
                "💬 Try the LLM: wa.me/50766623757"
            ]
        }
    
    def _architect_emphasis(self) -> Dict[str, str]:
        """Emphasis for AI Solutions Architect roles"""
        return {
            "summary": """AI Solutions Architect with end-to-end system design experience. Built complete AI 
            product architecture from voice input (Whisper) to text processing (Claude/GPT) to memory 
            (PostgreSQL) to monetization (PayPal). Production systems serving 19 countries with 99%+ uptime. 
            Specialized in scalable, cost-efficient AI architectures.""",
            
            "top_skills": [
                "End-to-End AI Architecture",
                "Multi-modal AI (voice, text, image OCR)",
                "Microservices Design",
                "Database Design (PostgreSQL, Supabase)",
                "API Integration (8+ AI services)",
                "Scalability (19 countries, growing)",
                "Cost Optimization (98% reduction)",
                "Infrastructure (Docker, Railway, Vercel)"
            ],
            
            "key_projects": [
                "EspaLuz Architecture: Voice (Whisper) → Processing (Claude/GPT) → Memory (PostgreSQL) → Response (TTS). Multi-platform (WhatsApp, Telegram, SaaS web).",
                "Payment Integration: PayPal subscriptions + crypto payment testing. Reliable recurring billing.",
                "Scalability: Serving 19 countries with 99%+ uptime on $15K infrastructure budget."
            ],
            
            "emphasis_points": [
                "🏗️ Complete system design (voice to monetization)",
                "📡 Multi-modal AI (voice, text, OCR)",
                "💰 Cost-efficient ($15K vs $900K traditional)",
                "⚡ Production-grade (99%+ uptime)",
                "🌍 International scale (19 countries)",
                "💬 Live architecture: wa.me/50766623757"
            ]
        }
    
    def _growth_engineer_emphasis(self) -> Dict[str, str]:
        """Emphasis for AI Growth Engineer roles"""
        return {
            "summary": """AI Growth Engineer combining product development with growth hacking. Achieved organic 
            growth to 19 countries with zero marketing budget. Built viral loops into product (bilingual AI 
            tutor). Monetization: PayPal subscriptions from zero to live in 7 months. Technical growth: 
            automated content generation, social media bots, community building.""",
            
            "top_skills": [
                "Product-Led Growth (19 countries, organic)",
                "Monetization (PayPal subs, zero to revenue)",
                "Growth Engineering (automation, bots)",
                "A/B Testing & Analytics",
                "Community Building (bilingual EN/ES)",
                "Content Automation (AI-generated)",
                "Social Media Automation",
                "Viral Loop Design"
            ],
            
            "key_projects": [
                "EspaLuz Growth: 0 to 19 countries through product-led growth. Viral coefficient >1.0. Bilingual strategy (EN/ES markets).",
                "Monetization: Launched PayPal subscriptions. Converted free users to paying in 7 months.",
                "Automation: Built AI content generator + social media bot (LinkedIn, Instagram auto-posting). Scaled reach 10x."
            ],
            
            "emphasis_points": [
                "📈 Organic growth to 19 countries (no marketing budget)",
                "💰 0→revenue in 7 months (PayPal subs)",
                "🤖 Growth automation (AI content, social bots)",
                "🌍 International expansion (EN/ES markets)",
                "🎯 Product-led growth (viral loops)",
                "💬 Growing product: wa.me/50766623757"
            ]
        }
    
    def _full_stack_emphasis(self) -> Dict[str, str]:
        """Emphasis for Full-Stack AI Engineer roles"""
        return {
            "summary": """Full-Stack AI Engineer building production AI products end-to-end. Solo-built 6 apps 
            in 7 months: frontend (React, TypeScript), backend (Python, Node.js), AI (Claude, GPT, Whisper), 
            infrastructure (Docker, Railway). 2 live AI agents with paying users in 19 countries. 50,000+ 
            lines of production code.""",
            
            "top_skills": [
                "Frontend: React, TypeScript, Tailwind CSS",
                "Backend: Python, Node.js, Flask",
                "AI/ML: Claude, GPT, Whisper, TTS, ElizaOS",
                "Databases: PostgreSQL, Supabase",
                "APIs: WhatsApp, Telegram, PayPal, Twitter",
                "Infrastructure: Docker, Railway, Vercel",
                "Web3: Polygon, Thirdweb, MetaMask, IPFS",
                "50,000+ lines of production code"
            ],
            
            "key_projects": [
                "EspaLuz Full-Stack: React frontend, Python backend, Claude/GPT AI layer, PostgreSQL database, WhatsApp/Telegram APIs, PayPal integration.",
                "ALGOM Alpha: Node.js bot with ElizaOS framework, CCXT trading API, Twitter API. Autonomous 24/7 operation.",
                "6 production apps: 2 AI agents (live), 1 influencer bot, 1 NFT gallery, 1 SaaS platform, 1 main website. All solo-built in 7 months."
            ],
            
            "emphasis_points": [
                "💻 True full-stack (frontend + backend + AI + infra)",
                "🚀 Solo-built 6 production apps in 7 months",
                "🤖 AI integration expert (8+ services)",
                "💰 Revenue-generating (PayPal subs live)",
                "🌍 Production at scale (19 countries)",
                "💬 Live code: wa.me/50766623757"
            ]
        }
