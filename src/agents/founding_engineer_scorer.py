"""
Advanced scoring specifically for Founding Engineer, AI PM, and AI Engineer roles
Emphasizes Elena's unique value: live products, traction, founding experience
"""
from typing import Tuple, List
from ..core.models import Profile, JobPosting


class FoundingEngineerScorer:
    """
    Specialized scorer for:
    - Founding Engineer
    - AI Product Manager
    - Full-Stack AI Engineer
    - LLM Engineer
    - AI Solutions Architect
    - AI Growth Engineer
    """
    
    def __init__(self):
        self.target_roles = [
            "founding engineer",
            "ai product manager",
            "full-stack ai engineer",
            "llm engineer",
            "ai solutions architect",
            "ai growth engineer",
            "technical co-founder",
            "ai product engineer",
            "product engineer"
        ]
        
        # Elena's unique differentiators
        self.unique_strengths = {
            "live_products": 2,
            "paying_users": True,
            "countries": 19,
            "revenue": "PayPal subscriptions active",
            "cost_efficiency": "98% reduction",
            "speed": "6 products in 7 months",
            "web3": True,
            "bilingual": True,
            "executive": "Ex-CEO & CLO",
            "demo_link": "wa.me/50766623757"
        }
    
    def calculate_founding_fit_score(
        self, 
        job: JobPosting, 
        profile: Profile
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate fit specifically for founding/AI engineer roles
        
        Returns:
            (bonus_score, strengths_to_emphasize, talking_points)
        """
        score = 0.0
        strengths = []
        talking_points = []
        
        job_text = (job.title + " " + job.description).lower()
        
        # 1. ROLE MATCH (Critical - 40 points max)
        role_score, role_strengths = self._score_role_match(job_text)
        score += role_score
        strengths.extend(role_strengths)
        
        # 2. STAGE FIT (30 points max)
        stage_score, stage_strengths = self._score_company_stage(job_text)
        score += stage_score
        strengths.extend(stage_strengths)
        
        # 3. EQUITY MENTION (20 points max)
        equity_score, equity_strengths = self._score_equity(job_text)
        score += equity_score
        strengths.extend(equity_strengths)
        
        # 4. VALUE PROPS (30 points max)
        value_score, value_strengths = self._score_value_propositions(job_text)
        score += value_score
        strengths.extend(value_strengths)
        
        # 5. RED FLAGS (negative points)
        red_flag_penalty = self._check_red_flags(job_text)
        score -= red_flag_penalty
        
        # Generate talking points
        talking_points = self._generate_talking_points(job, strengths)
        
        return min(score, 100), strengths, talking_points
    
    def _score_role_match(self, job_text: str) -> Tuple[float, List[str]]:
        """Score role title match"""
        score = 0.0
        strengths = []
        
        # Exact target roles
        for role in self.target_roles:
            if role in job_text:
                score += 40
                strengths.append(f"🎯 PERFECT MATCH: {role.title()} role!")
                break
        
        # Partial matches
        if score == 0:
            if any(keyword in job_text for keyword in ["ai engineer", "ml engineer", "ai product"]):
                score += 25
                strengths.append("✅ AI Engineer role (good fit)")
            elif any(keyword in job_text for keyword in ["product manager", "pm"]) and "ai" in job_text:
                score += 30
                strengths.append("✅ AI Product Manager (strong fit)")
        
        # Founding keywords (additional bonus)
        if any(keyword in job_text for keyword in ["founding", "founding team", "employee #"]):
            score += 10
            strengths.append("💎 FOUNDING ROLE - emphasize 0→1 experience!")
        
        return score, strengths
    
    def _score_company_stage(self, job_text: str) -> Tuple[float, List[str]]:
        """Score company stage fit"""
        score = 0.0
        strengths = []
        
        # Perfect stages for Elena
        if any(stage in job_text for stage in ["seed", "pre-seed", "series a"]):
            score += 30
            strengths.append("🚀 Early-stage startup (values traction proof!)")
        
        # YC companies (special boost)
        if any(keyword in job_text for keyword in ["y combinator", "yc w", "yc s", "yc f"]):
            score += 20
            strengths.append("⭐ YC COMPANY - PERFECT FIT (emphasize PMF proof!)")
        
        # Startup keywords
        if any(keyword in job_text for keyword in ["startup", "fast-paced", "0-1", "0→1"]):
            score += 10
            strengths.append("✅ Startup environment (your strength!)")
        
        return score, strengths
    
    def _score_equity(self, job_text: str) -> Tuple[float, List[str]]:
        """Score equity offering"""
        score = 0.0
        strengths = []
        
        if "equity" in job_text or "stock options" in job_text:
            score += 20
            strengths.append("💰 Equity offered - highlight founding mindset!")
            
            # Check for specific percentages
            if any(pct in job_text for pct in ["0.5%", "1%", "2%", "3%"]):
                score += 10
                strengths.append("🎯 Significant equity stake mentioned!")
        
        return score, strengths
    
    def _score_value_propositions(self, job_text: str) -> Tuple[float, List[str]]:
        """Score how well Elena's unique value props align"""
        score = 0.0
        strengths = []
        
        # Live products / traction focus
        if any(keyword in job_text for keyword in ["traction", "users", "revenue", "customers", "pmf", "product-market fit"]):
            score += 10
            strengths.append("🔥 LEAD WITH: 2 live AI agents, 19 countries, PayPal subs active")
        
        # Speed / execution focus
        if any(keyword in job_text for keyword in ["ship", "fast", "move quickly", "velocity", "iterate"]):
            score += 8
            strengths.append("⚡ EMPHASIZE: 6 products in 7 months, solo-built")
        
        # Cost efficiency
        if any(keyword in job_text for keyword in ["bootstrap", "capital efficient", "lean", "scrappy"]):
            score += 8
            strengths.append("💡 HIGHLIGHT: 98% cost reduction ($15K vs $900K)")
        
        # Web3 + AI
        if any(keyword in job_text for keyword in ["web3", "blockchain", "crypto", "dao"]) and "ai" in job_text:
            score += 10
            strengths.append("🦄 UNIQUE: Web3 + AI combo (mention DAO, ALGOM, Atuona)")
        
        # Bilingual / international
        if any(keyword in job_text for keyword in ["spanish", "latam", "latin america", "bilingual", "international"]):
            score += 8
            strengths.append("🌎 ADVANTAGE: Bilingual EN/ES, 19 countries experience")
        
        # AI/LLM specific
        if any(keyword in job_text for keyword in ["llm", "gpt", "claude", "language model", "rag", "embeddings"]):
            score += 10
            strengths.append("🤖 TECHNICAL FIT: EspaLuz uses Claude, GPT, Whisper, TTS")
        
        # Product management
        if any(keyword in job_text for keyword in ["product manager", "product strategy", "roadmap", "gtm"]):
            score += 8
            strengths.append("📊 PM EXPERIENCE: Solo founder = product + eng + growth")
        
        return score, strengths
    
    def _check_red_flags(self, job_text: str) -> float:
        """Check for red flags (returns penalty points)"""
        penalty = 0.0
        
        # Big corps (not ideal for founding engineer fit)
        if any(corp in job_text for corp in ["google", "meta", "amazon", "microsoft", "apple", "netflix"]):
            penalty += 30
        
        # Too junior
        if "junior" in job_text or "entry level" in job_text:
            penalty += 20
        
        # No equity at early stage
        if any(stage in job_text for stage in ["seed", "series a"]) and "equity" not in job_text:
            penalty += 15
        
        # Unrealistic requirements
        if "10+ years" in job_text and "required" in job_text:
            penalty += 10
        
        return penalty
    
    def _generate_talking_points(
        self, 
        job: JobPosting, 
        strengths: List[str]
    ) -> List[str]:
        """Generate specific talking points for this role"""
        talking_points = []
        
        job_text = (job.title + " " + job.description).lower()
        
        # Always include demo
        talking_points.append("💬 OPEN WITH: 'Try my live AI assistant: wa.me/50766623757'")
        
        # Role-specific points
        if "founding engineer" in job_text:
            talking_points.append("🎯 PITCH: 'I've been a founding engineer on my own products - 2 live AI agents with paying users'")
            talking_points.append("📈 METRICS: '19 countries reach, PayPal subscriptions active, 98% cost reduction'")
        
        if "ai product manager" in job_text or "product manager" in job_text:
            talking_points.append("🎯 PITCH: 'As a solo founder, I handle product strategy AND engineering'")
            talking_points.append("📊 PM SKILLS: '0→1 product development, user research (bilingual EN/ES market), GTM execution'")
        
        if "llm" in job_text or "language model" in job_text:
            talking_points.append("🤖 TECHNICAL: 'EspaLuz uses Claude for emotional intelligence + GPT for structured tasks'")
            talking_points.append("🔧 LLM EXPERIENCE: 'Prompt engineering, RAG, context management, multi-language support'")
        
        if "growth" in job_text or "growth engineer" in job_text:
            talking_points.append("📈 GROWTH: 'Organic reach to 19 countries through bilingual product + community building'")
            talking_points.append("💰 MONETIZATION: 'PayPal subscriptions from zero to live in 7 months'")
        
        # Always close with this
        talking_points.append("🎁 VALUE PROP: 'I don't just talk about building - you can use my product right now'")
        
        return talking_points
    
    def should_apply_immediately(self, job: JobPosting, score: float) -> bool:
        """
        Determine if this is a "drop everything and apply now" job
        
        Criteria:
        - Founding engineer role at YC/Series A
        - AI + Product role with equity
        - Score > 80
        """
        job_text = (job.title + " " + job.description).lower()
        
        # High-priority signals
        is_founding = "founding" in job_text
        is_yc = "y combinator" in job_text or "yc" in job.company.lower()
        is_early = any(stage in job_text for stage in ["seed", "series a"])
        has_equity = "equity" in job_text
        high_score = score > 80
        
        # Must have at least 3 of these
        priority_count = sum([is_founding, is_yc, is_early, has_equity, high_score])
        
        return priority_count >= 3
