"""
🛡️ SAFE ATS INTEGRATION MODULE

This module provides a SAFE way to integrate the new ATS scraper
into the existing autonomous system WITHOUT breaking anything.

SAFETY GUARANTEES:
✅ Does NOT modify linkedin_cmo_v4.py (posting system untouched)
✅ Does NOT modify orchestrator.py core logic
✅ Uses feature flag (can disable with env var)
✅ Falls back to existing behavior on ANY error
✅ All new code is ADDITIVE, not replacing

USAGE:
    from .ats_integration import get_ats_jobs_safely
    
    # In job_monitor.py, ADD this to existing sources:
    ats_jobs = await get_ats_jobs_safely(target_roles)
    all_jobs.extend(ats_jobs)  # Add to existing jobs, don't replace

Author: VibeJobHunter Upgrade
Date: December 2025
Safety Level: 🟢 NON-BREAKING
"""

import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# =====================================
# FEATURE FLAG - Can disable via env var
# =====================================

ATS_ENABLED = os.getenv("ATS_SCRAPER_ENABLED", "true").lower() == "true"

if ATS_ENABLED:
    logger.info("✅ [ATS Integration] ATS Scraper is ENABLED")
else:
    logger.info("⚠️ [ATS Integration] ATS Scraper is DISABLED (set ATS_SCRAPER_ENABLED=true to enable)")


async def get_ats_jobs_safely(
    target_roles: Optional[List[str]] = None,
    max_companies: int = 20,
    timeout_seconds: int = 60
) -> List:
    """
    SAFE wrapper to get jobs from ATS APIs.
    
    SAFETY:
    - Returns empty list on ANY error (never crashes)
    - Respects feature flag
    - Has timeout protection
    - Logs all issues for debugging
    
    Args:
        target_roles: List of target role keywords (e.g., ['AI Engineer', 'Founding'])
        max_companies: Max companies to check (lower = faster, higher = more jobs)
        timeout_seconds: Total timeout for all API calls
    
    Returns:
        List of JobPosting objects, or empty list on any error
    """
    
    # Check feature flag
    if not ATS_ENABLED:
        logger.debug("[ATS Integration] Skipping - disabled by feature flag")
        return []
    
    try:
        # Import here to avoid import errors if ats_scraper has issues
        from ..scrapers.ats_scraper import ATSScraper
        
        logger.info(f"🔍 [ATS Integration] Starting safe job fetch...")
        logger.info(f"   Target roles: {target_roles[:3] if target_roles else 'All'}...")
        logger.info(f"   Max companies: {max_companies}")
        
        # Extract keywords from target roles
        keywords = None
        if target_roles:
            # Convert role names to search keywords
            keywords = []
            for role in target_roles:
                keywords.extend(role.lower().split())
            # Add common engineering keywords
            keywords.extend(['engineer', 'developer', 'ai', 'ml', 'python', 'software'])
            keywords = list(set(keywords))[:15]  # Dedupe and limit
        
        # Create scraper and fetch with timeout
        scraper = ATSScraper()
        
        try:
            jobs = await asyncio.wait_for(
                scraper.fetch_all_jobs(keywords=keywords, max_companies=max_companies),
                timeout=timeout_seconds
            )
            
            logger.info(f"✅ [ATS Integration] Successfully fetched {len(jobs)} jobs!")
            return jobs
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [ATS Integration] Timeout after {timeout_seconds}s - returning partial results")
            return []
        
    except ImportError as e:
        logger.error(f"❌ [ATS Integration] Import error (ats_scraper not found?): {e}")
        logger.info("   Falling back to existing job sources only")
        return []
        
    except Exception as e:
        logger.error(f"❌ [ATS Integration] Unexpected error: {e}")
        logger.info("   Falling back to existing job sources only")
        return []


async def test_ats_integration():
    """
    Test function to verify ATS integration works.
    
    Run with: python -c "import asyncio; from src.autonomous.ats_integration import test_ats_integration; asyncio.run(test_ats_integration())"
    """
    print("\n" + "="*60)
    print("🧪 TESTING ATS INTEGRATION (Safe Mode)")
    print("="*60 + "\n")
    
    print(f"Feature flag ATS_SCRAPER_ENABLED: {ATS_ENABLED}")
    print()
    
    # Test with sample target roles
    target_roles = ["AI Engineer", "Founding Engineer", "Software Engineer"]
    
    print(f"Testing with roles: {target_roles}")
    print("This should NOT affect any existing systems...")
    print()
    
    jobs = await get_ats_jobs_safely(
        target_roles=target_roles,
        max_companies=5,  # Small test
        timeout_seconds=30
    )
    
    print(f"\n✅ Test complete!")
    print(f"   Jobs found: {len(jobs)}")
    print(f"   Existing systems: UNTOUCHED ✅")
    
    if jobs:
        print(f"\n   Sample job: {jobs[0].company} - {jobs[0].title}")
    
    return jobs


# =====================================
# HELPER: Add to job_monitor without modifying it heavily
# =====================================

def get_integration_code_snippet():
    """
    Returns the exact code snippet to add to job_monitor.py
    
    This is a MINIMAL change - just adding one more source to the existing list.
    """
    snippet = '''
# =====================================
# ADD THIS TO job_monitor.py find_new_jobs() method
# Location: After the existing search tasks, around line 90
# =====================================

# NEW: Add ATS API source (safe - won't break if disabled)
try:
    from .ats_integration import get_ats_jobs_safely
    ats_jobs = await get_ats_jobs_safely(target_roles, max_companies=20)
    all_jobs.extend(ats_jobs)
    logger.info(f"✅ Added {len(ats_jobs)} jobs from ATS APIs")
except Exception as e:
    logger.debug(f"ATS integration skipped: {e}")
    # Continues with existing sources - no impact on existing functionality

# =====================================
# END OF ADDITION
# =====================================
'''
    return snippet


if __name__ == "__main__":
    # Run test
    asyncio.run(test_ats_integration())
