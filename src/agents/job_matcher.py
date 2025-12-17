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
Threshold: ≥75 to apply (Golden Roadmap v2)

FIXED: December 2025 - AI analysis now actually runs!
"""
import logging
import json
import os
from typing import List, Tuple, Dict, Optional
from anthropic import Anthropic

from ..core.models import Profile, JobPosting
from ..core.config import get_settings
from .founding_engineer_scorer import FoundingEngineerScorer

logger = logging.getLogger(__name__)

# Feature flag for deep AI analysis (costs API tokens)
USE_AI_DEEP_ANALYSIS = os.getenv("USE_AI_JOB_ANALYSIS", "true").lower() == "true"


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
        self.ai = None
        try:
            api_key = self.settings.anthropic_api_key
            if api_key:
                self.ai = Anthropic(api_key=api_key)
                logger.info("✅ AI Job Analyzer: Claude API enabled")
            else:
                logger.warning("⚠️ AI Job Analyzer: No API key, using keyword matching only")
        except Exception as e:
            logger.warning(f"⚠️ AI Job Analyzer init failed: {e}")
            self.ai = None
        self.founding_scorer = FoundingEngineerScorer()
    
    def calculate_match_score(self, profile: Profile, job: JobPosting) -> Tuple[float, List[str]]:
        """
        Calculate match score using HYBRID approach:
        1. Fast keyword-based dimensional scoring (always runs)
        2. Deep AI analysis via Claude (for jobs scoring 50+)
        
        Returns: (score 0-100, list of reasons)
        """
        # PHASE 1: Fast dimensional scoring (keyword-based)
        dimensional_score, dimensional_reasons = self._dimensional_score(job)
        
        # Get founding engineer bonus
        founding_score = 0
        strengths = []
        try:
            founding_score, strengths, talking_points = self.founding_scorer.calculate_founding_fit_score(job, profile)
            job.talking_points = talking_points
        except Exception as e:
            logger.debug(f"Founding scorer error: {e}")
        
        # Calculate preliminary score
        BASE_SCORE = 40.0
        dimensional_bonus = max(0, dimensional_score - BASE_SCORE)
        founding_contribution = founding_score * 0.2
        
        preliminary_score = BASE_SCORE + (dimensional_bonus * 0.8) + founding_contribution
        preliminary_score = min(preliminary_score, 100)
        
        # PHASE 2: Deep AI analysis (only for promising jobs)
        # This is the FIX - AI analysis now actually runs!
        ai_score = None
        ai_reasons = []
        
        if USE_AI_DEEP_ANALYSIS and self.ai and preliminary_score >= 50:
            try:
                ai_result = self._ai_deep_analysis(profile, job)
                if ai_result:
                    ai_score = ai_result.get('score', 0)
                    ai_reasons = ai_result.get('reasons', [])
                    
                    # Log AI analysis
                    logger.info(f"🧠 AI Analysis for {job.company}: {ai_score}/100")
            except Exception as e:
                logger.warning(f"AI analysis failed: {e}")
        
        # PHASE 3: Combine scores - CALIBRATED FOR REAL RESULTS
        # Problem: AI was giving 10-25 scores, tanking 70+ keyword matches
        # Fix: Balance weights and add AI floor to prevent over-penalization
        if ai_score is not None:
            # AI floor: Prevent AI from completely tanking a good keyword match
            # If keywords say 70+ and AI says 15, something's wrong with AI prompt
            ai_score_adjusted = max(ai_score, 35)  # Floor at 35
            
            # If keyword score is strong (65+), trust it more
            if preliminary_score >= 65:
                # 60% keyword, 40% AI for strong keyword matches
                combined_score = (preliminary_score * 0.6) + (ai_score_adjusted * 0.4)
            else:
                # 50/50 for weaker keyword matches
                combined_score = (preliminary_score * 0.5) + (ai_score_adjusted * 0.5)
            
            all_reasons = ai_reasons[:3] + dimensional_reasons[:2] + strengths[:2]
        else:
            combined_score = preliminary_score
            all_reasons = dimensional_reasons + strengths[:2]
        
        combined_score = min(combined_score, 100)
        
        # Flag high-priority jobs
        if combined_score >= 75:
            all_reasons.insert(0, "🚨 HIGH PRIORITY - APPLY IMMEDIATELY!")
        elif combined_score >= 65:
            all_reasons.insert(0, "⭐ STRONG MATCH")
        
        return combined_score, all_reasons
    
    def _ai_deep_analysis(self, profile: Profile, job: JobPosting) -> Optional[Dict]:
        """
        Deep AI analysis using Claude - THE FIX!
        
        This actually runs Claude to analyze the job posting deeply.
        Only called for jobs that passed preliminary screening (score >= 50).
        """
        if not self.ai:
            return None
        
        try:
            title = getattr(job, 'title', '') or ''
            company = getattr(job, 'company', '') or ''
            description = getattr(job, 'description', '') or ''
            location = getattr(job, 'location', '') or 'Remote'
            remote = getattr(job, 'remote_allowed', True)
            requirements = getattr(job, 'requirements', []) or []
            
            # Truncate description to save tokens
            desc_truncated = description[:2000] if len(description) > 2000 else description
            req_text = '\n'.join([f"  • {r}" for r in requirements[:8]])
            
            prompt = f"""Analyze this job posting against Elena's profile. Return a JSON score and reasons.

ELENA'S PROFILE:
- 11 AI products built solo in 10 months (5 AIPAs running 24/7)
- Ex-CEO & CLO (7 years strategic leadership)
- Tech: Python, TypeScript, React, Claude, GPT, Groq, LangChain, MCP
- 19 countries reach, PayPal subscriptions LIVE
- 99%+ cost reduction ($900K → <$15K)
- AI Co-Founders: CTO AIPA (code reviews) + CMO AIPA (LinkedIn)
- Target: Founding Engineer, AI Product Manager, Staff/Principal Engineer

JOB:
Title: {title}
Company: {company}
Location: {location}
Remote: {remote}
Description: {desc_truncated}
Requirements:
{req_text}

SCORING CRITERIA (start at 50, adjust up/down):
BASE: 50 (neutral starting point)

POSITIVE (add points):
+25: Founding Engineer / First Engineer / 0-1 role
+20: AI/ML Product Engineer role
+15: YC / Seed / Series A startup
+15: Staff/Principal/Lead engineer role  
+10: Equity mentioned
+10: Small team (under 50 people)
+10: High autonomy / ownership emphasized
+5: Remote-friendly
+5: Web3 + AI combo

NEGATIVE (subtract points):
-30: Big corp (Google, Meta, Microsoft, Amazon, Databricks, Snowflake)
-20: Junior/Entry level
-15: Pure research / PhD required
-10: Maintenance-focused role
-10: Large engineering team (50+ engineers)

Be generous with AI/startup roles. Elena has 11 AI products shipped.

Return ONLY valid JSON (no markdown):
{{"score": <0-100>, "reasons": ["reason1", "reason2", "reason3"], "recommendation": "apply|maybe|skip", "fit_summary": "one sentence"}}"""

            response = self.ai.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Handle potential JSON issues
            result_text = result_text.strip()
            if not result_text.startswith('{'):
                # Try to find JSON object
                start = result_text.find('{')
                end = result_text.rfind('}') + 1
                if start >= 0 and end > start:
                    result_text = result_text[start:end]
            
            result = json.loads(result_text)
            
            # Validate result
            score = float(result.get('score', 0))
            reasons = result.get('reasons', [])
            
            if not reasons:
                reasons = [result.get('fit_summary', 'AI analyzed this role')]
            
            # Add recommendation to reasons
            rec = result.get('recommendation', 'maybe')
            if rec == 'apply':
                reasons.insert(0, "🤖 AI: Strong fit - APPLY")
            elif rec == 'skip':
                reasons.insert(0, "🤖 AI: Poor fit")
            else:
                reasons.insert(0, "🤖 AI: Moderate fit")
            
            return {
                'score': score,
                'reasons': reasons,
                'recommendation': rec,
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"AI analysis JSON parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"AI analysis error: {e}")
            return None
    
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
