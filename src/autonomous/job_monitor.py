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

        # ==============================================================
        # 5️⃣ Wellfound (AngelList) — Startup jobs
        # ==============================================================
        try:
            wellfound_jobs = await self._search_wellfound()
            all_jobs.extend(wellfound_jobs)
        except Exception as e:
            logger.warning(f"⚠️ Wellfound search failed: {e}")

        # ==============================================================
        # 6️⃣ WeWorkRemotely — Remote jobs
        # ==============================================================
        try:
            wwr_jobs = await self._search_weworkremotely()
            all_jobs.extend(wwr_jobs)
        except Exception as e:
            logger.warning(f"⚠️ WeWorkRemotely search failed: {e}")

        # ==============================================================
        # 7️⃣ AI-Jobs.net — AI-specific job board
        # ==============================================================
        try:
            ai_jobs = await self._search_aijobs()
            all_jobs.extend(ai_jobs)
        except Exception as e:
            logger.warning(f"⚠️ AI-Jobs search failed: {e}")

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
        YC Work At A Startup - REAL API
        
        Uses the actual workatastartup.com Algolia API to fetch real jobs.
        """
        logger.info("🔍 Checking YC Work At A Startup...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # Work at a Startup uses Algolia - public search endpoint
                # The actual API endpoint that returns job data
                algolia_url = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
                
                headers = {
                    "x-algolia-api-key": "NDYzYmNmMTRjYzU3YTkzNGE2ZTQxNzUxY2RhYTBkMTlhMWMxOTlkYmM5Yzg0YmU2ZGQ4ZWZjYzlhMWNmNTBkMXJlc3RyaWN0SW5kaWNlcz0lNUIlMjJXYWFTX3Byb2R1Y3Rpb25fY29tcGFuaWVzJTIyJTJDJTIyV2FhU19wcm9kdWN0aW9uX2pvYl9wb3N0aW5ncyUyMiU1RCZmaWx0ZXJzPWhpcmluZyUzRHRydWUmbnVtZXJpY0ZpbHRlcnM9am9ic19jb3VudCUzRTAmaGl0c1BlclBhZ2U9MTAw",
                    "x-algolia-application-id": "45BWZJ1SGC",
                    "Content-Type": "application/json",
                }
                
                # Search for AI/ML/Founding roles
                search_payload = {
                    "requests": [
                        {
                            "indexName": "WaaS_production_job_postings",
                            "params": "query=AI engineer&hitsPerPage=50&filters=remote%3Atrue"
                        },
                        {
                            "indexName": "WaaS_production_job_postings",
                            "params": "query=founding engineer&hitsPerPage=50"
                        },
                        {
                            "indexName": "WaaS_production_job_postings",
                            "params": "query=machine learning&hitsPerPage=50&filters=remote%3Atrue"
                        },
                        {
                            "indexName": "WaaS_production_job_postings",
                            "params": "query=staff engineer&hitsPerPage=30"
                        }
                    ]
                }
                
                try:
                    async with session.post(
                        algolia_url, 
                        json=search_payload, 
                        headers=headers, 
                        timeout=20
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            seen_ids = set()
                            for result in data.get("results", []):
                                for hit in result.get("hits", []):
                                    job_id = hit.get("id") or hit.get("objectID")
                                    if job_id in seen_ids:
                                        continue
                                    seen_ids.add(job_id)
                                    
                                    title = hit.get("title") or hit.get("job_title") or ""
                                    company = hit.get("company_name") or hit.get("company", {}).get("name") or "YC Startup"
                                    
                                    # Build job URL
                                    slug = hit.get("slug") or hit.get("company_slug") or ""
                                    job_url = f"https://www.workatastartup.com/jobs/{job_id}" if job_id else "https://www.workatastartup.com/jobs"
                                    
                                    # Get location
                                    location = hit.get("location") or hit.get("locations") or "Remote"
                                    if isinstance(location, list):
                                        location = ", ".join(location[:3])
                                    
                                    # Get description
                                    description = hit.get("description") or hit.get("job_description") or ""
                                    if len(description) > 2000:
                                        description = description[:2000]
                                    
                                    jobs.append({
                                        "id": f"yc_{job_id}",
                                        "title": title,
                                        "company": company,
                                        "location": str(location),
                                        "description": description,
                                        "source": "yc_workatastartup",
                                        "url": job_url,
                                        "salary_min": hit.get("salary_min"),
                                        "salary_max": hit.get("salary_max"),
                                        "remote": hit.get("remote", True),
                                        "yc_batch": hit.get("batch") or hit.get("company", {}).get("batch"),
                                    })
                        else:
                            logger.debug(f"YC WAAS API returned {resp.status}")
                            
                except Exception as e:
                    logger.debug(f"YC Algolia API failed: {e}")
                    
                    # Fallback: Try the jobs JSON endpoint
                    try:
                        fallback_url = "https://www.workatastartup.com/companies.json"
                        params = {"query": "ai", "hasJobs": "true"}
                        
                        async with session.get(fallback_url, params=params, headers={"User-Agent": "VibeJobHunter/1.0"}, timeout=15) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                for company in data.get("companies", [])[:30]:
                                    for job in company.get("jobs", []):
                                        jobs.append({
                                            "id": f"yc_{job.get('id')}",
                                            "title": job.get("title", ""),
                                            "company": company.get("name", "YC Startup"),
                                            "location": job.get("location", "Remote"),
                                            "description": job.get("description", "")[:2000],
                                            "source": "yc_workatastartup",
                                            "url": job.get("url") or f"https://www.workatastartup.com/companies/{company.get('slug')}",
                                        })
                    except Exception as e2:
                        logger.debug(f"YC fallback also failed: {e2}")

            logger.info(f"✅ YC WAAS: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ YC WAAS failed: {e}")

        return jobs
    
    async def _search_wellfound(self) -> List[Dict]:
        """
        Wellfound (formerly AngelList Talent) - GraphQL API
        
        Searches for AI/ML/Founding roles at startups.
        """
        logger.info("🔍 Checking Wellfound (AngelList)...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                # Wellfound GraphQL endpoint
                graphql_url = "https://wellfound.com/graphql"
                
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Origin": "https://wellfound.com",
                    "Referer": "https://wellfound.com/jobs",
                }
                
                # GraphQL query for job listings
                queries = [
                    {"role": "AI Engineer", "remote": True},
                    {"role": "Founding Engineer", "remote": False},
                    {"role": "Machine Learning Engineer", "remote": True},
                    {"role": "Staff Engineer", "remote": True},
                ]
                
                for query_params in queries:
                    graphql_query = {
                        "operationName": "JobSearchResults",
                        "variables": {
                            "query": query_params["role"],
                            "page": 1,
                            "perPage": 30,
                            "remote": query_params["remote"],
                            "sortBy": "posted_at",
                        },
                        "query": """
                            query JobSearchResults($query: String, $page: Int, $perPage: Int, $remote: Boolean) {
                                jobListings(query: $query, page: $page, perPage: $perPage, remote: $remote) {
                                    edges {
                                        node {
                                            id
                                            title
                                            slug
                                            remote
                                            locationNames
                                            compensation
                                            description
                                            startup {
                                                name
                                                slug
                                                companySize
                                                highConcept
                                            }
                                        }
                                    }
                                }
                            }
                        """
                    }
                    
                    try:
                        async with session.post(
                            graphql_url,
                            json=graphql_query,
                            headers=headers,
                            timeout=15
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                
                                edges = data.get("data", {}).get("jobListings", {}).get("edges", [])
                                
                                for edge in edges:
                                    node = edge.get("node", {})
                                    startup = node.get("startup", {})
                                    
                                    job_id = node.get("id", "")
                                    slug = node.get("slug", "")
                                    startup_slug = startup.get("slug", "")
                                    
                                    jobs.append({
                                        "id": f"wellfound_{job_id}",
                                        "title": node.get("title", ""),
                                        "company": startup.get("name", ""),
                                        "location": ", ".join(node.get("locationNames", ["Remote"])[:3]),
                                        "description": (node.get("description") or startup.get("highConcept") or "")[:2000],
                                        "source": "wellfound",
                                        "url": f"https://wellfound.com/jobs/{slug}" if slug else "https://wellfound.com/jobs",
                                        "compensation": node.get("compensation"),
                                        "company_size": startup.get("companySize"),
                                        "remote": node.get("remote", False),
                                    })
                            else:
                                logger.debug(f"Wellfound returned {resp.status}")
                                
                    except Exception as e:
                        logger.debug(f"Wellfound query for '{query_params['role']}' failed: {e}")
                
                # Fallback: Try the public job listings page
                if len(jobs) == 0:
                    try:
                        # Simple HTML scrape fallback
                        search_url = "https://wellfound.com/role/r/ai-engineer"
                        async with session.get(search_url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                # Basic parsing - look for job data in script tags
                                if "__NEXT_DATA__" in html:
                                    import re
                                    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', html)
                                    if match:
                                        try:
                                            next_data = json.loads(match.group(1))
                                            # Extract job listings from Next.js data
                                            page_props = next_data.get("props", {}).get("pageProps", {})
                                            listings = page_props.get("jobListings", []) or page_props.get("results", [])
                                            
                                            for listing in listings[:20]:
                                                jobs.append({
                                                    "id": f"wellfound_{listing.get('id', '')}",
                                                    "title": listing.get("title", "AI Engineer"),
                                                    "company": listing.get("company", {}).get("name", "Startup"),
                                                    "location": listing.get("location", "Remote"),
                                                    "description": listing.get("description", "")[:2000],
                                                    "source": "wellfound",
                                                    "url": listing.get("url", "https://wellfound.com/jobs"),
                                                })
                                        except json.JSONDecodeError:
                                            pass
                    except Exception as e:
                        logger.debug(f"Wellfound fallback failed: {e}")

            logger.info(f"✅ Wellfound: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ Wellfound failed: {e}")

        return jobs

    async def _search_weworkremotely(self) -> List[Dict]:
        """
        WeWorkRemotely - RSS/JSON API
        
        Programming and DevOps categories for engineering roles.
        """
        logger.info("🔍 Checking WeWorkRemotely...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "VibeJobHunter/1.0"}
                
                # WWR has category-based RSS feeds we can parse
                categories = [
                    "programming",
                    "devops-sysadmin",
                ]
                
                for category in categories:
                    url = f"https://weworkremotely.com/categories/{category}.rss"
                    
                    try:
                        async with session.get(url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                xml_text = await resp.text()
                                
                                # Parse RSS XML manually (no external dependency)
                                import re
                                items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
                                
                                for item in items[:20]:
                                    title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
                                    link_match = re.search(r'<link>(.*?)</link>', item)
                                    desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL)
                                    
                                    title = title_match.group(1) if title_match else ""
                                    link = link_match.group(1) if link_match else ""
                                    desc = desc_match.group(1) if desc_match else ""
                                    
                                    # Filter for relevant roles
                                    title_lower = title.lower()
                                    if any(kw in title_lower for kw in ["ai", "ml", "engineer", "founding", "senior", "staff", "full stack", "fullstack"]):
                                        # Extract company from title (format: "Company: Job Title")
                                        parts = title.split(":", 1)
                                        company = parts[0].strip() if len(parts) > 1 else "Remote Company"
                                        job_title = parts[1].strip() if len(parts) > 1 else title
                                        
                                        jobs.append({
                                            "id": f"wwr_{hash(link) % 10000000}",
                                            "title": job_title,
                                            "company": company,
                                            "location": "Remote",
                                            "description": desc[:2000],
                                            "source": "weworkremotely",
                                            "url": link,
                                            "remote": True,
                                        })
                    except Exception as e:
                        logger.debug(f"WWR category {category} failed: {e}")

            logger.info(f"✅ WeWorkRemotely: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ WeWorkRemotely failed: {e}")

        return jobs

    async def _search_aijobs(self) -> List[Dict]:
        """
        AI-Jobs.net - AI/ML focused job board
        
        Scrapes the main listings page.
        """
        logger.info("🔍 Checking AI-Jobs.net...")
        jobs = []

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                }
                
                # Try to get the jobs listing
                url = "https://ai-jobs.net/api/jobs/"
                
                try:
                    async with session.get(url, headers=headers, timeout=15) as resp:
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                                
                                for job in data[:50]:
                                    title = job.get("title", "")
                                    
                                    jobs.append({
                                        "id": f"aijobs_{job.get('id', '')}",
                                        "title": title,
                                        "company": job.get("company", "AI Company"),
                                        "location": job.get("location", "Remote"),
                                        "description": job.get("description", "")[:2000],
                                        "source": "ai_jobs_net",
                                        "url": job.get("url", "https://ai-jobs.net"),
                                        "salary_min": job.get("salary_min"),
                                        "salary_max": job.get("salary_max"),
                                    })
                            except json.JSONDecodeError:
                                # Not JSON, try HTML parsing
                                pass
                except Exception as e:
                    logger.debug(f"AI-Jobs API failed: {e}")
                
                # Fallback: scrape HTML if API doesn't work
                if len(jobs) == 0:
                    try:
                        html_url = "https://ai-jobs.net/"
                        async with session.get(html_url, headers=headers, timeout=15) as resp:
                            if resp.status == 200:
                                html = await resp.text()
                                
                                # Look for job cards in HTML
                                import re
                                
                                # Extract job data from structured data or job cards
                                job_pattern = r'<a[^>]*href="(/job/[^"]+)"[^>]*>([^<]+)</a>'
                                matches = re.findall(job_pattern, html)
                                
                                for link, title in matches[:30]:
                                    if any(kw in title.lower() for kw in ["ai", "ml", "engineer", "machine learning", "data"]):
                                        jobs.append({
                                            "id": f"aijobs_{hash(link) % 10000000}",
                                            "title": title.strip(),
                                            "company": "AI Company",
                                            "location": "Remote",
                                            "description": f"AI/ML role from ai-jobs.net. Full details at https://ai-jobs.net{link}",
                                            "source": "ai_jobs_net",
                                            "url": f"https://ai-jobs.net{link}",
                                        })
                    except Exception as e:
                        logger.debug(f"AI-Jobs HTML scrape failed: {e}")

            logger.info(f"✅ AI-Jobs.net: {len(jobs)} jobs found")

        except Exception as e:
            logger.warning(f"⚠️ AI-Jobs.net failed: {e}")

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
