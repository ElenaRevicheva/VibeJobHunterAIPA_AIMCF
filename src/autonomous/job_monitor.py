"""
🛡️ JOB MONITOR — CAREER-GATED EDITION

Purpose:
- Discover jobs ONLY from sources that actually work
- Enforce HARD career gate (Phase 0)
- Feed only high-signal roles into the system

This is NOT a scraper playground.
This is a precision career weapon.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set

import aiohttp

from src.core.models import JobPosting, JobSource
from src.utils.logger import setup_logger
from src.utils.cache import ResponseCache

from src.autonomous.job_gate import JobGate

logger = setup_logger(__name__)


class JobMonitor:
    """
    High-signal job discovery with hard career gating
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
                logger.info(f"Loaded {len(self.seen_jobs)} seen jobs")
            except Exception as e:
                logger.warning(f"Failed loading seen jobs: {e}")

    def _save_seen_jobs(self):
        path = Path("autonomous_data/seen_jobs.json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"seen_jobs": list(self.seen_jobs)}))

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

        logger.info("🔍 Job discovery cycle started")

        all_jobs: List[Dict] = []

        # ==============================================================
        # 1️⃣ ATS APIs — PRIMARY SOURCE (WORKS)
        # ==============================================================
        try:
            from src.autonomous.ats_integration import get_ats_jobs_safely

            ats_jobs = await get_ats_jobs_safely(
                target_roles=target_roles,
                max_companies=40,
            )

            logger.info(f"✅ ATS APIs returned {len(ats_jobs)} jobs")
            all_jobs.extend(ats_jobs)

        except Exception as e:
            logger.error(f"❌ ATS integration failed: {e}")

        # ==============================================================
        # 2️⃣ Hacker News Who’s Hiring (API-based, stable)
        # ==============================================================
        hn_jobs = await self._search_hackernews()
        all_jobs.extend(hn_jobs)

        # ==============================================================
        # 3️⃣ RemoteOK JSON API (stable)
        # ==============================================================
        remoteok_jobs = await self._search_remoteok()
        all_jobs.extend(remoteok_jobs)

        # ==============================================================
        # 4️⃣ HARD CAREER GATE (PHASE 0)
        # ==============================================================
        before_gate = len(all_jobs)

        gated_jobs = [
            job for job in all_jobs
            if JobGate.passes(job)
        ]

        logger.info(
            f"🛡️ Career gate enforced: {len(gated_jobs)} / {before_gate} jobs passed"
        )

        # ==============================================================
        # 5️⃣ Deduplicate + persist
        # ==============================================================
        new_jobs: List[JobPosting] = []

        for job in gated_jobs:
            job_id = self._job_id(job)
            if job_id not in self.seen_jobs:
                self.seen_jobs.add(job_id)
                new_jobs.append(self._to_job_posting(job))

        self._save_seen_jobs()

        logger.info(f"🎯 {len(new_jobs)} NEW high-signal jobs accepted")

        return new_jobs[:max_results]

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    async def _search_hackernews(self) -> List[Dict]:
        """
        Hacker News Who’s Hiring via Algolia API
        """
        logger.info("🔍 Fetching Hacker News Who’s Hiring")

        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://hn.algolia.com/api/v1/search"
                params = {
                    "query": "who is hiring",
                    "tags": "ask_hn",
                    "hitsPerPage": 1,
                }

                async with session.get(url, params=params, timeout=10) as resp:
                    data = await resp.json()
                    thread_id = data["hits"][0]["objectID"]

                async with session.get(
                    f"https://hn.algolia.com/api/v1/items/{thread_id}",
                    timeout=10,
                ) as resp:
                    thread = await resp.json()

                    for comment in thread.get("children", []):
                        text = comment.get("text", "") or ""
                        text_l = text.lower()

                        if any(k in text_l for k in ["ai", "ml", "founding", "engineer"]):
                            jobs.append({
                                "title": "AI / Founding Engineer",
                                "company": "HN Startup",
                                "location": "Remote",
                                "salary_min": 80000,
                                "company_size": 10,
                                "stage": "seed",
                                "source": "hackernews",
                                "url": f"https://news.ycombinator.com/item?id={comment.get('id')}",
                                "raw_text": text[:2000],
                            })

        except Exception as e:
            logger.warning(f"HN fetch failed: {e}")

        logger.info(f"✅ HN returned {len(jobs)} jobs")
        return jobs

    async def _search_remoteok(self) -> List[Dict]:
        """
        RemoteOK JSON API
        """
        logger.info("🔍 Fetching RemoteOK")

        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://remoteok.com/api", timeout=10) as resp:
                    data = await resp.json()

                for item in data[1:]:
                    title = (item.get("position") or "").lower()

                    if not any(k in title for k in ["ai", "ml", "founding", "platform"]):
                        continue

                    jobs.append({
                        "title": item.get("position"),
                        "company": item.get("company"),
                        "location": "Remote",
                        "salary_min": item.get("salary_min") or 0,
                        "company_size": 20,
                        "stage": "seed",
                        "source": "remoteok",
                        "url": item.get("url"),
                        "raw_text": item.get("description", "")[:2000],
                    })

        except Exception as e:
            logger.warning(f"RemoteOK failed: {e}")

        logger.info(f"✅ RemoteOK returned {len(jobs)} jobs")
        return jobs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _job_id(self, job: Dict) -> str:
        return f"{job.get('source')}::{job.get('company')}::{job.get('title')}".lower()

    def _to_job_posting(self, job: Dict) -> JobPosting:
        return JobPosting(
            title=job["title"],
            company=job["company"],
            location=job["location"],
            description=job.get("raw_text", ""),
            source=JobSource.OTHER,
            url=job["url"],
            posted_date=datetime.utcnow(),
            remote_allowed=True,
            requirements=[],
            responsibilities=[],
        )
