"""
🛡️ JOB GATE - Career-Aligned Filtering
Works with REAL ATS data (not hypothetical metadata)

STRATEGY:
- Filter based on title + description keywords (data we HAVE)
- Exclude junior/intern/sales roles
- Prioritize remote-friendly positions
- Let high-quality scoring happen in job_matcher.py
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────
# KEYWORDS (Based on Elena's target roles)
# ─────────────────────────────

ROLE_INCLUDE_KEYWORDS = {
    # Primary targets
    "founding", "founder", "co-founder",
    "ai engineer", "ml engineer", "machine learning",
    "product engineer", "platform engineer",
    "full stack", "fullstack", "full-stack",
    "senior engineer", "staff engineer", "principal",
    "technical lead", "tech lead", "engineering lead",
    "solutions architect", "ai architect",
    # Secondary
    "software engineer", "backend engineer",
    "automation", "infrastructure", "infra",
    "llm", "nlp", "data engineer",
    "product manager", "growth engineer",
}

ROLE_EXCLUDE_KEYWORDS = {
    # Never apply to these
    "junior", "intern", "internship", "entry level", "entry-level",
    "sales", "recruiter", "recruiting", "hr ",
    "customer success", "account manager", "account executive",
    "phd required", "doctorate required",
    "director of sales", "vp sales",
    "legal counsel", "general counsel",
    "executive assistant", "administrative",
}

LOCATION_INCLUDE_KEYWORDS = {
    "remote", "anywhere", "global", "worldwide",
    "latam", "latin america", "americas",
    "panama", "usa", "united states", "us-",
}


class JobGate:
    """
    🛡️ HARD career gate for Elena's job search.
    
    Uses PRACTICAL filtering based on data ATS APIs actually provide:
    - Job title keywords
    - Job description keywords
    - Location compatibility
    
    Does NOT require: company_size, funding_stage, salary (ATS APIs don't have these)
    """

    @staticmethod
    def passes(job: Dict) -> bool:
        """
        Returns True if job should proceed to scoring.
        Returns False if job should be immediately discarded.
        """
        title = (job.get("title") or "").lower()
        description = (job.get("description") or job.get("raw_text") or "").lower()
        location = (job.get("location") or "").lower()
        
        combined_text = f"{title} {description}"
        
        # ─────────────────────────────
        # 1️⃣ EXCLUDE bad roles (instant reject)
        # ─────────────────────────────
        for exclude_kw in ROLE_EXCLUDE_KEYWORDS:
            if exclude_kw in title:
                logger.debug(f"❌ GATE REJECT (excluded keyword '{exclude_kw}'): {title[:50]}")
                return False
        
        # ─────────────────────────────
        # 2️⃣ REQUIRE at least one relevant keyword
        # ─────────────────────────────
        has_relevant_keyword = any(kw in combined_text for kw in ROLE_INCLUDE_KEYWORDS)
        
        if not has_relevant_keyword:
            logger.debug(f"❌ GATE REJECT (no relevant keywords): {title[:50]}")
            return False
        
        # ─────────────────────────────
        # 3️⃣ CHECK location compatibility
        # ─────────────────────────────
        # If location is specified, check if it's compatible
        if location:
            is_remote_friendly = any(loc in location for loc in LOCATION_INCLUDE_KEYWORDS)
            
            # Reject if explicitly on-site in incompatible locations
            if not is_remote_friendly:
                incompatible_locations = ["london", "new york", "san francisco", "berlin", "paris", "tokyo"]
                for bad_loc in incompatible_locations:
                    if bad_loc in location and "remote" not in location:
                        logger.debug(f"❌ GATE REJECT (incompatible location '{location}'): {title[:50]}")
                        return False
        
        # ─────────────────────────────
        # ✅ PASSED - Proceed to scoring
        # ─────────────────────────────
        logger.debug(f"✅ GATE PASSED: {title[:50]}")
        return True
    
    @staticmethod
    def get_gate_stats(jobs: list) -> Dict:
        """Get statistics about gate filtering"""
        passed = sum(1 for j in jobs if JobGate.passes(j))
        return {
            "total": len(jobs),
            "passed": passed,
            "rejected": len(jobs) - passed,
            "pass_rate": f"{(passed/len(jobs)*100):.1f}%" if jobs else "0%"
        }
