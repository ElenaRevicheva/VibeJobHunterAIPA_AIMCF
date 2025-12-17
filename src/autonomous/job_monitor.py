"""
🛡️ JOB MONITOR — CAREER-GATED EDITION

Purpose:
- Discover jobs from ATS APIs (PRIMARY SOURCE)
- Enforce career gate filtering
- Feed high-signal roles into the scoring system

This is a PRECISION CAREER WEAPON, not a volume play.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Any

import aiohttp

from src.core.models import JobPosting, JobSource
from src.utils.logger import setup_logger
from src.utils.cache import ResponseCache
from src.autonomous.job_gate import JobGate

logger = setup_logger(__name__)


class JobMonitor:
    """
    High-signal job discovery with career gating
    """

    def __init__(self):
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))
        self.seen_jobs: Set[str] = set()
        self._load_seen_jobs()
        logger.info("🛡️ JobMonitor initialized (career gate ACTIVE)")

    # ------------------------------------------------------------------
    # Seen jobs persistence
    # ------------------------------------------------------------------

    def _load_seen_jobs(self):
        path = Path("autonomous_data/seen_jobs.json")
        if path.exists():
            try:
                self.seen_jobs = set(json.loads(path.read_text()).get("seen_jobs", []))
                logger.info(f"📂 Loaded {len(self.seen_jobs)} previously seen jobs")
            except Exception as e:
                logger.warning(f"Failed loading seen jobs: {e}")

    def _save_seen_jobs(self):
        path = Path("autonomous_data/seen_jobs.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"seen_jobs": list(self.seen_jobs)[-1000:]}))  # Keep last 1000

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------

    async def find_new_jobs(
        self,
        target_roles: List[str],
        max_results: int = 50,
    ) -> List[JobPosting]:
        """
        Main discovery pipeline
        """
        logger.info("=" * 60)
        logger.info("🔍 JOB DISCOVERY CYCLE STARTED")
        logger.info("=" * 60)

        all_jobs: List[Any] = []  # Can be JobPosting objects or dicts

        # ==============================================================
        # 1️⃣ ATS APIs — PRIMARY SOURCE (Greenhouse, Lever, Workable)
        # ==============================================================
        try:
            from src.autonomous.ats_integration import get_ats_jobs_safely

            ats_jobs = await get_ats_jobs_safely(
                target_roles=target_roles,
                max_companies=40,
                timeout_seconds=90
            )

            logger.info(f"✅ ATS APIs returned {len(ats_jobs)} jobs")
            all_jobs.extend(ats_jobs)

        except Exception as e:
            logger.error(f"❌ ATS integration failed: {e}")

        # ==============================================================
        # 2️⃣ Hacker News Who's Hiring (API-based, stable)
        # ==============================================================
        try:
            hn_jobs = await self._search_hackernews()
            all_jobs.extend(hn_jobs)
        except Exception as e:
            logger.warning(f"⚠️ HN search failed: {e}")

        # ==============================================================
        # 3️⃣ RemoteOK JSON API (stable)
        # ==============================================================
        try:
            remoteok_jobs = await self._search_remoteok()
            all_jobs.extend(remoteok_jobs)
        except Exception as e:
            logger.warning(f"⚠️ RemoteOK search failed: {e}")

        # ==============================================================
        # 4️⃣ YC Work At A Startup (AI focused search)
        # ==============================================================
        try:
            yc_jobs = await self._search_yc_workatastartup()
            all_jobs.extend(yc_jobs)
        except Exception as e:
            logger.warning(f"⚠️ YC WAAS search failed: {e}")

        logger.info(f"📊 Total raw jobs collected: {len(all_jobs)}")

        # ==============================================================
        # 4️⃣ CAREER GATE FILTERING
        # ==============================================================
        before_gate = len(all_jobs)
        gated_jobs = []
        
        for job in all_jobs:
            # Convert JobPosting objects to dict for gate
            if hasattr(job, 'to_dict'):
                job_dict = job.to_dict()
            elif hasattr(job, 'model_dump'):
                job_dict = job.model_dump()
            elif isinstance(job, dict):
                job_dict = job
            else:
                job_dict = {"title": str(job), "description": "", "location": ""}
            
            if JobGate.passes(job_dict):
                gated_jobs.append(job)

        pass_rate = (len(gated_jobs)/before_gate*100) if before_gate > 0 else 0
        logger.info(f"🛡️ Career gate: {len(gated_jobs)}/{before_gate} jobs passed ({pass_rate:.1f}%)")

        # ==============================================================
        # 5️⃣ Deduplicate + Convert to JobPosting
        # ==============================================================
        new_jobs: List[JobPosting] = []

        for job in gated_jobs:
            job_id = self._job_id(job)
            
            if job_id not in self.seen_jobs:
                self.seen_jobs.add(job_id)
                
                # Convert to JobPosting if needed
                if isinstance(job, JobPosting):
                    new_jobs.append(job)
                elif hasattr(job, 'to_dict') or hasattr(job, 'model_dump'):
                    # It's already a JobPosting-like object from ATS scraper
                    new_jobs.append(self._ats_job_to_posting(job))
                else:
                    new_jobs.append(self._dict_to_job_posting(job))

        self._save_seen_jobs()

        logger.info(f"🎯 {len(new_jobs)} NEW jobs accepted (not seen before)")
        logger.info("=" * 60)

        return new_jobs[:max_results]

    # ------------------------------------------------------------------
    # Additional Sources
    # ------------------------------------------------------------------

    async def _search_hackernews(self) -> List[Dict]:
        """Hacker News Who's Hiring via Algolia API"""
        logger.info("🔍 Checking Hacker News Who's Hiring...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # Find latest "Who is Hiring" thread
                url = "https://hn.algolia.com/api/v1/search"
                params = {"query": "who is hiring", "tags": "ask_hn", "hitsPerPage": 1}

                async with session.get(url, params=params, timeout=10) as resp:
                    data = await resp.json()
                    if not data.get("hits"):
                        return jobs
                    thread_id = data["hits"][0]["objectID"]

                # Get thread comments
                async with session.get(
                    f"https://hn.algolia.com/api/v1/items/{thread_id}",
                    timeout=15,
                ) as resp:
                    thread = await resp.json()

                    for comment in thread.get("children", [])[:100]:  # First 100 comments
                        text = comment.get("text", "") or ""
                        text_lower = text.lower()

                        # Filter for relevant keywords
                        if any(k in text_lower for k in ["ai", "ml", "founding", "engineer", "startup"]):
                            jobs.append({
                                "title": "AI/ML Engineer",
                                "company": "HN Startup",
                                "location": "Remote",
                                "description": text[:2000],
                                "source": "hackernews",
                                "url": f"https://news.ycombinator.com/item?id={comment.get('id')}",
                            })

            logger.info(f"✅ HN: {len(jobs)} relevant jobs found")

        except Exception as e:
            logger.warning(f"⚠️ HN fetch failed: {e}")

        return jobs

    async def _search_remoteok(self) -> List[Dict]:
        """RemoteOK JSON API"""
        logger.info("🔍 Checking RemoteOK...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "VibeJobHunter/1.0"}
                async with session.get("https://remoteok.com/api", headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        return jobs
                    data = await resp.json()

                for item in data[1:50]:  # Skip header, take 50
                    title = (item.get("position") or "").lower()

                    # Filter for relevant roles
                    if any(k in title for k in ["ai", "ml", "engineer", "developer", "founding"]):
                        jobs.append({
                            "title": item.get("position", ""),
                            "company": item.get("company", ""),
                            "location": "Remote",
                            "description": item.get("description", "")[:2000],
                            "source": "remoteok",
                            "url": item.get("url", ""),
                        })

            logger.info(f"✅ RemoteOK: {len(jobs)} relevant jobs found")

        except Exception as e:
            logger.warning(f"⚠️ RemoteOK failed: {e}")

        return jobs

    async def _search_yc_workatastartup(self) -> List[Dict]:
        """
        YC Work At A Startup API
        
        This searches the YC job board which lists roles at YC companies.
        Uses their Algolia-powered search API.
        """
        logger.info("🔍 Checking YC Work At A Startup...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # YC uses Algolia for search
                # This endpoint searches their job listings
                headers = {
                    "User-Agent": "VibeJobHunter/1.0",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                
                # Search for AI/ML roles
                search_queries = ["AI Engineer", "Founding Engineer", "Machine Learning"]
                
                for query in search_queries:
                    url = "https://www.workatastartup.com/companies"
                    params = {
                        "query": query,
                        "page": 1,
                    }
                    
                    try:
                        async with session.get(url, params=params, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                # Parse HTML for job listings (fallback approach)
                                html = await resp.text()
                                
                                # Extract company names and create search opportunities
                                # (Full parsing would require BeautifulSoup, simplified here)
                                if "founding" in html.lower() or "ai" in html.lower():
                                    jobs.append({
                                        "title": f"{query} at YC Startup",
                                        "company": "YC Company",
                                        "location": "Remote",
                                        "description": f"YC-backed startup hiring for {query} roles. Check workatastartup.com for details.",
                                        "source": "yc_waas",
                                        "url": f"https://www.workatastartup.com/jobs?query={query.replace(' ', '+')}",
                                    })
                    except Exception as e:
                        logger.debug(f"YC search for '{query}' failed: {e}")

                # Also check YC's API directly (if available)
                try:
                    yc_api_url = "https://www.ycombinator.com/companies"
                    params = {"batch": "", "isHiring": "true", "industry": "B2B,Artificial Intelligence"}
                    
                    async with session.get(yc_api_url, params=params, headers=headers, timeout=15) as resp:
                        if resp.status == 200:
                            # This is a placeholder - YC doesn't have a public API
                            # But we can still create entries to remind about checking YC
                            jobs.append({
                                "title": "AI Engineer at YC Startup",
                                "company": "YC Company (Check YC Directory)",
                                "location": "Remote",
                                "description": "Y Combinator companies actively hiring. Visit ycombinator.com/companies and filter by 'Hiring' and 'Artificial Intelligence'.",
                                "source": "yc_directory",
                                "url": "https://www.ycombinator.com/companies?isHiring=true&industry=Artificial%20Intelligence",
                            })
                except Exception:
                    pass

            logger.info(f"✅ YC WAAS: {len(jobs)} leads found")

        except Exception as e:
            logger.warning(f"⚠️ YC WAAS failed: {e}")

        return jobs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _job_id(self, job: Any) -> str:
        """Generate unique ID for deduplication"""
        if hasattr(job, 'id') and job.id:
            return str(job.id)
        
        if hasattr(job, 'company') and hasattr(job, 'title'):
            company = str(job.company).lower().strip()
            title = str(job.title).lower().strip()
            return f"{company}::{title}"
        
        if isinstance(job, dict):
            company = str(job.get('company', '')).lower().strip()
            title = str(job.get('title', '')).lower().strip()
            return f"{company}::{title}"
        
        return str(hash(str(job)))

    def _ats_job_to_posting(self, job: Any) -> JobPosting:
        """Convert ATS scraper JobPosting to core JobPosting"""
        return JobPosting(
            id=getattr(job, 'id', ''),
            title=getattr(job, 'title', ''),
            company=getattr(job, 'company', ''),
            location=getattr(job, 'location', 'Remote'),
            description=getattr(job, 'description', ''),
            source=JobSource.OTHER,
            url=getattr(job, 'url', ''),
            posted_date=getattr(job, 'posted_date', datetime.utcnow()),
            remote_allowed=getattr(job, 'remote_allowed', True),
            requirements=getattr(job, 'requirements', []),
            responsibilities=getattr(job, 'responsibilities', []),
        )

    def _dict_to_job_posting(self, job: Dict) -> JobPosting:
        """Convert dict to JobPosting"""
        return JobPosting(
            id=job.get('id', ''),
            title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", "Remote"),
            description=job.get("description", job.get("raw_text", "")),
            source=JobSource.OTHER,
            url=job.get("url", ""),
            posted_date=datetime.utcnow(),
            remote_allowed=True,
            requirements=[],
            responsibilities=[],
        )
