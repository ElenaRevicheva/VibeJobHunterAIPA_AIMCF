"""
AI-powered job matching and scoring - GOLDEN ROADMAP v2 ALIGNED

Dimensional Scoring (from roadmap):
- AI product ownership: 25 points
- 0→1 autonomy: 25 points  
- Full-stack / infra: 20 points
- Business exposure: 15 points
- Bilingual / global: 5 points
- Web3 (optional): 10 points

Total: 100 points
Threshold: ≥55 to apply (configurable)
"""
import logging
from typing import List, Tuple, Dict
from anthropic import Anthropic

from ..core.models import Profile, JobPosting
from ..core.config import get_settings
from .founding_engineer_scorer import FoundingEngineerScorer

logger = logging.getLogger(__name__)


class JobMatcher:
    """
    Match jobs to Elena's profile using DIMENSIONAL SCORING
    Based on Golden Roadmap v2 criteria
    """
    
    # ─────────────────────────────────────────────────────────
    # DIMENSIONAL SCORING WEIGHTS (from Golden Roadmap v2)
    # ─────────────────────────────────────────────────────────
    DIMENSION_WEIGHTS = {
        "ai_product_ownership": 25,   # AI product experience
        "zero_to_one_autonomy": 25,   # 0→1 building, founding roles
        "fullstack_infra": 20,        # Full-stack, platform, infra
        "business_exposure": 15,      # GTM, strategy, product
        "bilingual_global": 5,        # Remote, international, EN/ES
        "web3_bonus": 10,             # Web3, crypto, blockchain
    }
    
    # ─────────────────────────────────────────────────────────
    # KEYWORD MAPS FOR EACH DIMENSION
    # ─────────────────────────────────────────────────────────
    DIMENSION_KEYWORDS = {
        "ai_product_ownership": {
            "high": ["ai product", "llm product", "ai engineer", "ml engineer", "ai solutions",
                     "machine learning", "nlp", "computer vision", "ai infrastructure",
                     "ai platform", "llm engineer", "ai systems", "solutions architect",
                     "applied ai", "ai researcher"],
            "medium": ["ai", "ml", "gpt", "claude", "openai", "anthropic", "llm", 
                       "neural", "deep learning", "transformer", "embedding", "langchain",
                       "rag", "agent", "chatbot"],
            "low": ["data science", "analytics", "automation", "data engineer"]
        },
        "zero_to_one_autonomy": {
            "high": ["founding engineer", "founding", "0-1", "zero to one", "first engineer",
                     "build from scratch", "greenfield", "staff engineer", "principal",
                     "technical lead", "tech lead", "lead engineer", "senior engineer",
                     "senior software", "staff software"],
            "medium": ["startup", "early stage", "seed", "series a", "small team",
                       "high autonomy", "ownership", "end-to-end", "full ownership",
                       "forward deployed", "fde"],
            "low": ["agile", "autonomous", "self-starter", "independent"]
        },
        "fullstack_infra": {
            "high": ["full-stack", "fullstack", "platform engineer", "infrastructure",
                     "backend", "frontend", "devops", "cloud architect", "solutions architect"],
            "medium": ["python", "typescript", "react", "node", "fastapi", "docker",
                       "kubernetes", "aws", "gcp", "postgresql", "api", "microservices",
                       "rest", "graphql"],
            "low": ["developer", "engineer", "software"]
        },
        "business_exposure": {
            "high": ["product manager", "product engineer", "gtm", "go-to-market",
                     "technical pm", "founder", "co-founder", "cto", "vp engineering",
                     "director", "head of"],
            "medium": ["product", "strategy", "growth", "revenue", "customer",
                       "stakeholder", "roadmap", "metrics", "kpi", "b2b", "enterprise"],
            "low": ["cross-functional", "collaborate", "business"]
        },
        "bilingual_global": {
            "high": ["remote", "global", "international", "distributed", "async",
                     "latam", "spanish", "bilingual", "multilingual"],
            "medium": ["worldwide", "anywhere", "flexible location", "timezone"],
            "low": ["hybrid", "wfh", "work from home"]
        },
        "web3_bonus": {
            "high": ["web3", "blockchain", "crypto", "defi", "dao", "smart contract",
                     "solidity", "ethereum", "polygon", "token"],
            "medium": ["decentralized", "nft", "wallet", "onchain"],
            "low": ["fintech", "digital assets"]
        }
    }
    
    def __init__(self):
        self.settings = get_settings()
        try:
            self.ai = Anthropic(api_key=self.settings.anthropic_api_key)
        except Exception:
            self.ai = None
        self.founding_scorer = FoundingEngineerScorer()
    
    def calculate_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Calculate DIMENSIONAL match score
        
        Returns: (score 0-100, list of reasons)
        """
        # Get dimensional score (primary method)
        dimensional_score, dimensional_reasons = self._dimensional_score(job)
        
        # Get founding engineer bonus
        try:
            founding_score, strengths, talking_points = self.founding_scorer.calculate_founding_fit_score(job, profile)
            job.talking_points = talking_points
        except Exception:
            founding_score = 0
            strengths = []
        
        # Combine: 80% dimensional, 20% founding bonus
        combined_score = (dimensional_score * 0.8) + (founding_score * 0.2)
        
        # Combine reasons
        all_reasons = dimensional_reasons + strengths[:2]
        
        # Flag high-priority jobs
        if combined_score >= 75:
            all_reasons.insert(0, "🚨 HIGH PRIORITY - APPLY IMMEDIATELY!")
        elif combined_score >= 65:
            all_reasons.insert(0, "⭐ STRONG MATCH")
        
        return combined_score, all_reasons
    
    def _dimensional_score(self, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Score job against Elena's 6 dimensions from Golden Roadmap
        
        Returns: (score 0-100, dimension breakdown)
        
        BASE SCORE: 40 points (job passed career gate = has some relevance)
        DIMENSIONAL: Up to 60 additional points
        """
        # Safely extract job text
        try:
            title = getattr(job, 'title', '') or ''
            description = getattr(job, 'description', '') or ''
            company = getattr(job, 'company', '') or ''
            job_text = f"{title} {description} {company}".lower()
        except Exception as e:
            logger.warning(f"Error extracting job data: {e}")
            job_text = str(job).lower() if job else ""
        
        # BASE SCORE: 40 points for passing career gate
        base_score = 40.0
        
        scores: Dict[str, float] = {}
        reasons: List[str] = []
        
        # If job_text is too short, log warning and use base score
        if len(job_text) < 50:
            logger.debug(f"⚠️ Short job text ({len(job_text)} chars): {title[:30]}...")
            reasons.append("📋 Passed career gate (limited data)")
            return base_score, reasons
        
        for dimension, weight in self.DIMENSION_WEIGHTS.items():
            keywords = self.DIMENSION_KEYWORDS.get(dimension, {})
            
            # Check keyword matches
            high_matches = [kw for kw in keywords.get("high", []) if kw in job_text]
            medium_matches = [kw for kw in keywords.get("medium", []) if kw in job_text]
            low_matches = [kw for kw in keywords.get("low", []) if kw in job_text]
            
            # Calculate dimension score (scale to 60% of weight since base=40)
            if high_matches:
                dim_score = weight * 0.6  # 60% of weight (max dimensional = 60)
                reasons.append(f"✅ {dimension.replace('_', ' ').title()}: {', '.join(high_matches[:2])}")
            elif medium_matches:
                dim_score = weight * 0.4  # 40% of weight
                if len(medium_matches) >= 3:
                    dim_score = weight * 0.5  # 50% if multiple
                reasons.append(f"✓ {dimension.replace('_', ' ').title()}: {', '.join(medium_matches[:2])}")
            elif low_matches:
                dim_score = weight * 0.2  # 20% of weight
            else:
                dim_score = 0
            
            scores[dimension] = dim_score
        
        # Calculate total: BASE + DIMENSIONAL
        dimensional_score = sum(scores.values())
        total_score = base_score + dimensional_score
        
        # Cap at 100
        total_score = min(total_score, 100)
        
        # If no reasons, add base reason
        if not reasons:
            reasons.append("📋 Passed career gate filters")
        
        # Log for debugging (only INFO level for visibility)
        if total_score >= 60:
            logger.info(f"🎯 MATCH ({total_score:.0f}): {company} - {title[:40]}")
        
        return total_score, reasons
        
        prompt = f"""Analyze this job posting against the candidate's profile and provide:
1. A match score from 0-100 (higher is better)
2. 3-5 specific reasons why this is a good/bad match
3. Key skills/experience that align with the job

Candidate Profile:
- Name: {profile.name}
- Location: {profile.location}
- Experience: {profile.experience_years} years TOTAL (7 years C-suite exec + 10 months hands-on AI/ML engineering)

UNIQUE DIFFERENTIATORS (emphasize these!):
- 🔥 11 AI products (7 LIVE AI agents) with PAYING USERS in 19 countries
- 🤖 AI Co-Founders: CTO AIPA (autonomous code reviews, 8 repos) + CMO AIPA (LinkedIn automation) - $0/month operational cost
- 💰 Revenue: PayPal Subscriptions ACTIVE (not just demo!)
- ⚡ Speed: 11 production apps in 10 months (March-Dec 2025, solo-built)
- 💎 Cost: 99%+ reduction ($15K vs $900K traditional estimate)
- 🤖 Tech: Claude, GPT, Groq (Llama 3.3 70B), Whisper, TTS, OCR, ElizaOS, HeyGen, MCP, Oracle Cloud
- 🌎 Bilingual: EN/ES dual-sided market
- 👔 Executive: Ex-CEO & CLO at E-Government Russia (7 years strategic leadership)
- 🦄 Unique: Web3 + AI combination (DAO LLC, tokenomics + LLM)
- 🏢 Enterprise: Oracle Autonomous Database 26ai, mTLS encryption
- 💬 Live Demo: wa.me/50766623757 (instant credibility!)

- Skills: {', '.join(profile.skills[:15])}
- Key Achievements:
{chr(10).join([f"  • {ach}" for ach in profile.key_achievements[:5]])}
- Target Roles: {', '.join(profile.target_roles)}
- Languages: {', '.join(profile.languages)}

Job Posting:
- Title: {job.title}
- Company: {job.company}
- Location: {job.location}
- Remote: {job.remote_allowed}
- Description: {job.description[:1000]}
- Requirements: {chr(10).join([f"  • {req}" for req in job.requirements[:8]])}

Return JSON format:
{{
  "score": <0-100>,
  "reasons": ["reason1", "reason2", ...],
  "aligned_skills": ["skill1", "skill2", ...],
  "missing_skills": ["skill1", "skill2", ...],
  "recommendation": "apply|maybe|skip"
}}

Consider:
- Skill match (technical and soft skills)
- Experience level fit
- Location/remote compatibility
- Company culture fit based on achievements
- Growth potential
- Role alignment with target roles

SCORING PRIORITY FOR ELENA:
+30 points: Founding Engineer / AI Product Manager / LLM Engineer roles
+25 points: YC companies or Seed/Series A startups
+20 points: Mentions equity (0.5-3%)
+15 points: Values traction/PMF (she has 19 countries proof!)
+15 points: Fast-paced/builder culture (she ships 10x faster)
+10 points: Web3 + AI combination
-20 points: Big corp (Google, Meta, etc.) - not her fit
-15 points: Pure maintenance role - she's a 0→1 builder
"""

        try:
            response = self.ai.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            result_text = response.content[0].text
            
            # Extract JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            score = float(result.get("score", 0))
            reasons = result.get("reasons", [])
            
            # Add aligned skills to reasons
            aligned = result.get("aligned_skills", [])
            if aligned:
                reasons.append(f"Aligned skills: {', '.join(aligned[:3])}")
            
            # BOOST score with founding engineer bonus
            combined_score = (score * 0.7) + (founding_score * 0.3)  # 70% AI, 30% founding fit
            
            # Add founding engineer strengths to reasons
            if strengths:
                reasons.extend(strengths[:3])  # Top 3 strengths
            
            # Flag high-priority jobs
            if self.founding_scorer.should_apply_immediately(job, combined_score):
                reasons.insert(0, "🚨 HIGH PRIORITY - APPLY IMMEDIATELY!")
            
            return combined_score, reasons
        
        except Exception as e:
            print(f"Error calculating match score: {e}")
            # Fallback to basic scoring
            return self._basic_match_score(profile, job)
    
    def _basic_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        FALLBACK: Simple keyword matching when dimensional scoring fails
        Uses base score of 40 + bonuses
        """
        score = 40.0  # Base for jobs that passed gate
        reasons = []
        
        job_text = (job.title + " " + job.description).lower()
        
        # PRIMARY ROLE MATCH (+25 max)
        primary_roles = {
            'founding engineer': 25, 'founding': 23,
            'ai engineer': 22, 'ai product manager': 22, 'llm engineer': 22,
            'staff engineer': 20, 'principal engineer': 20,
            'technical lead': 18, 'tech lead': 18,
            'full-stack': 15, 'product engineer': 15,
            'ml engineer': 15, 'software engineer': 12
        }
        
        for keyword, points in primary_roles.items():
            if keyword in job_text:
                score += points
                reasons.append(f"✅ Role: {keyword.title()}")
                break
        
        # AI/ML TECH (+15 max)
        ai_keywords = ['ai', 'llm', 'gpt', 'claude', 'ml', 'machine learning', 
                       'nlp', 'openai', 'anthropic', 'transformer']
        ai_found = [kw for kw in ai_keywords if kw in job_text]
        if ai_found:
            score += min(len(ai_found) * 5, 15)
            reasons.append(f"✅ AI/ML: {', '.join(ai_found[:2])}")
        
        # STARTUP/AUTONOMY (+10 max)
        startup_kw = ['startup', 'seed', 'equity', 'yc', '0-1', 'founding', 'early stage']
        startup_found = [kw for kw in startup_kw if kw in job_text]
        if startup_found:
            score += min(len(startup_found) * 5, 10)
            reasons.append(f"✅ Stage: {', '.join(startup_found[:2])}")
        
        # REMOTE (+5)
        if job.remote_allowed or 'remote' in job_text:
            score += 5
            reasons.append("✅ Remote")
        
        # WEB3 BONUS (+5)
        web3_kw = ['web3', 'blockchain', 'crypto', 'defi', 'dao']
        if any(kw in job_text for kw in web3_kw):
            score += 5
            reasons.append("✅ Web3")
        
        if not reasons:
            reasons.append("📋 Passed career gate")
        
        return min(score, 100), reasons
    
    async def score_jobs(self, profile: Profile, jobs: List[JobPosting]) -> List[JobPosting]:
        """Score and sort jobs by relevance"""
        for job in jobs:
            score, reasons = self.calculate_match_score(profile, job)
            job.match_score = score
            job.match_reasons = reasons
        
        # Sort by score
        jobs.sort(key=lambda j: j.match_score, reverse=True)
        return jobs
    
    def filter_jobs(
        self,
        jobs: List[JobPosting],
        min_score: float = 50.0,
        exclude_keywords: List[str] = None
    ) -> List[JobPosting]:
        """Filter jobs by criteria"""
        filtered = []
        
        exclude_keywords = exclude_keywords or self.settings.excluded_keywords
        exclude_lower = [k.lower() for k in exclude_keywords]
        
        for job in jobs:
            # Check minimum score
            if job.match_score < min_score:
                continue
            
            # Check excluded keywords
            job_text_lower = (job.title + " " + job.description).lower()
            if any(kw in job_text_lower for kw in exclude_lower):
                continue
            
            filtered.append(job)
        
        return filtered
