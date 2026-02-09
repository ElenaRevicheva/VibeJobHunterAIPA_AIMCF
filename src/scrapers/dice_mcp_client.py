"""
🎲 DICE MCP CLIENT — Tech Job Search via Model Context Protocol

Purpose:
- Search Dice's tech-only job database via their public MCP server
- Returns structured job data with direct application links
- ADDITIVE source — does NOT replace any existing job sources

Endpoint: https://mcp.dice.com/mcp
Protocol: JSON-RPC 2.0 over HTTP (SSE transport)
Auth: None required

Safety Level: 🟢 NON-BREAKING (new file, no existing code modified)
"""

import json
import ssl
import logging
import urllib.request
from typing import List, Dict, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# DICE MCP SERVER CONFIG
# ─────────────────────────────────────────────────────────
DICE_MCP_URL = "https://mcp.dice.com/mcp"
DICE_TIMEOUT = 30  # seconds per request

# ─────────────────────────────────────────────────────────
# SEARCH KEYWORDS — Aligned with Elena's LinkedIn goals:
#   AI Product Engineer | Applied LLM Engineer | Founding Engineer
#   Companies building personal AI, agents, or developer tools
# ─────────────────────────────────────────────────────────
DICE_SEARCH_QUERIES = [
    "AI Product Engineer",
    "Applied LLM Engineer",
    "Founding Engineer AI",
    "AI Engineer Python",
    "LLM Engineer",
    "AI Agent Engineer",
    "AI Developer Tools Engineer",
    "Personal AI Engineer",
]

# ─────────────────────────────────────────────────────────
# FEATURE FLAG
# ─────────────────────────────────────────────────────────
import os
DICE_MCP_ENABLED = os.getenv("DICE_MCP_ENABLED", "true").lower() == "true"


class DiceMCPClient:
    """
    Client for Dice's Model Context Protocol job search server.

    Usage:
        client = DiceMCPClient()
        jobs = await client.search_all()
        # Returns List[Dict] ready for job_monitor pipeline
    """

    def __init__(self):
        self._ssl_ctx = ssl.create_default_context()
        self._request_id = 0
        self._initialized = False
        logger.info("🎲 Dice MCP Client initialized (endpoint: %s)", DICE_MCP_URL)

    # ─────────────────────────────
    # LOW-LEVEL MCP TRANSPORT
    # ─────────────────────────────

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _mcp_request(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Send a JSON-RPC 2.0 request to the Dice MCP server.
        Returns parsed result dict, or None on failure.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._next_id(),
        }
        if params:
            payload["params"] = params

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            DICE_MCP_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )

        try:
            resp = urllib.request.urlopen(req, timeout=DICE_TIMEOUT, context=self._ssl_ctx)
            body = resp.read().decode("utf-8")

            # Parse SSE response — Dice returns `event: message\ndata: {...}`
            for line in body.split("\n"):
                if line.startswith("data: "):
                    return json.loads(line[6:])

            # Fallback: try entire body as JSON
            return json.loads(body)

        except Exception as e:
            logger.warning("🎲 Dice MCP request failed (%s): %s", method, e)
            return None

    def _ensure_initialized(self):
        """Initialize MCP session if not done yet."""
        if self._initialized:
            return True

        result = self._mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "VibeJobHunter", "version": "1.0"},
        })

        if result and result.get("result"):
            server_info = result["result"].get("serverInfo", {})
            logger.info(
                "🎲 Dice MCP connected: %s v%s",
                server_info.get("name", "unknown"),
                server_info.get("version", "?"),
            )
            self._initialized = True
            return True

        logger.warning("🎲 Dice MCP initialization failed")
        return False

    # ─────────────────────────────
    # JOB SEARCH
    # ─────────────────────────────

    def search_jobs(
        self,
        keyword: str,
        workplace_types: Optional[List[str]] = None,
        employment_types: Optional[List[str]] = None,
        posted_date: str = "SEVEN",
        jobs_per_page: int = 20,
    ) -> List[Dict]:
        """
        Search Dice for jobs matching the keyword.

        Args:
            keyword: Search query (e.g., "AI Product Engineer")
            workplace_types: ["Remote"], ["On-Site"], ["Hybrid"] or combo
            employment_types: ["FULLTIME"], ["CONTRACTS"], ["PARTTIME"]
            posted_date: "ONE" (1 day), "THREE" (3 days), "SEVEN" (7 days)
            jobs_per_page: Results per page (1-100)

        Returns:
            List of job dicts normalized for the VibeJobHunter pipeline.
        """
        if not self._ensure_initialized():
            return []

        arguments = {
            "keyword": keyword,
            "posted_date": posted_date,
            "jobs_per_page": jobs_per_page,
        }
        if workplace_types:
            arguments["workplace_types"] = workplace_types
        if employment_types:
            arguments["employment_types"] = employment_types

        result = self._mcp_request("tools/call", {
            "name": "search_jobs",
            "arguments": arguments,
        })

        if not result:
            return []

        # Check for errors
        content = result.get("result", {}).get("content", [])
        is_error = result.get("result", {}).get("isError", False)

        if is_error or not content:
            error_text = content[0].get("text", "unknown") if content else "empty response"
            logger.debug("🎲 Dice search '%s' error: %s", keyword, error_text[:200])
            return []

        # Parse the response text (JSON inside text field)
        text = content[0].get("text", "")
        try:
            raw_data = json.loads(text)
        except json.JSONDecodeError:
            logger.debug("🎲 Dice search '%s' returned non-JSON: %s", keyword, text[:200])
            return []

        # Extract jobs from response
        raw_jobs = raw_data.get("data", [])
        if not isinstance(raw_jobs, list):
            raw_jobs = []

        jobs = []
        for raw in raw_jobs:
            job = self._normalize_job(raw, keyword)
            if job:
                jobs.append(job)

        logger.debug("🎲 Dice '%s': %d jobs found", keyword, len(jobs))
        return jobs

    def search_all(
        self,
        queries: Optional[List[str]] = None,
        workplace_types: Optional[List[str]] = None,
        employment_types: Optional[List[str]] = None,
        posted_date: str = "SEVEN",
        jobs_per_page: int = 20,
    ) -> List[Dict]:
        """
        Run all configured search queries and return deduplicated results.

        Args:
            queries: Override search queries (default: DICE_SEARCH_QUERIES)
            workplace_types: Default ["Remote"]
            employment_types: Default ["FULLTIME", "CONTRACTS"]
            posted_date: Default "SEVEN"

        Returns:
            Deduplicated list of job dicts for the pipeline.
        """
        if not DICE_MCP_ENABLED:
            logger.debug("🎲 Dice MCP disabled (DICE_MCP_ENABLED=false)")
            return []

        queries = queries or DICE_SEARCH_QUERIES
        workplace_types = workplace_types or ["Remote"]
        employment_types = employment_types or ["FULLTIME", "CONTRACTS"]

        all_jobs: Dict[str, Dict] = {}  # guid -> job (dedup by guid)

        for query in queries:
            try:
                results = self.search_jobs(
                    keyword=query,
                    workplace_types=workplace_types,
                    employment_types=employment_types,
                    posted_date=posted_date,
                    jobs_per_page=jobs_per_page,
                )
                for job in results:
                    job_id = job.get("id", "")
                    if job_id and job_id not in all_jobs:
                        all_jobs[job_id] = job

            except Exception as e:
                logger.warning("🎲 Dice query '%s' failed: %s", query, e)

        total = len(all_jobs)
        logger.info("🎲 Dice MCP: %d unique jobs from %d queries", total, len(queries))
        return list(all_jobs.values())

    # ─────────────────────────────
    # JOB NORMALIZATION
    # ─────────────────────────────

    def _normalize_job(self, raw: Dict, search_query: str) -> Optional[Dict]:
        """
        Convert a raw Dice API job into the VibeJobHunter pipeline format.

        Matches the dict format used by job_monitor.py secondary sources.
        """
        guid = raw.get("guid", "")
        if not guid:
            return None

        title = raw.get("title", "")
        company_name = raw.get("companyName", "")
        summary = raw.get("summary", "")
        details_url = raw.get("detailsPageUrl", "")
        company_url = raw.get("companyPageUrl", "")
        salary = raw.get("salary", "")
        posted_date = raw.get("postedDate", "")
        employment_type = raw.get("employmentType", "")
        easy_apply = raw.get("easyApply", False)
        is_remote = raw.get("isRemote", False)
        workplace_types = raw.get("workplaceTypes", [])
        willing_to_sponsor = raw.get("willingToSponsor", False)

        # Location
        location_data = raw.get("jobLocation") or {}
        location = location_data.get("displayName", "") if isinstance(location_data, dict) else ""
        if is_remote:
            location = f"Remote | {location}" if location else "Remote"

        # Build description with rich metadata
        desc_parts = [summary]
        if salary:
            desc_parts.append(f"Salary: {salary}")
        if employment_type:
            desc_parts.append(f"Type: {employment_type}")
        if willing_to_sponsor:
            desc_parts.append("Visa sponsorship: Yes")
        if easy_apply:
            desc_parts.append("Easy Apply: Yes")
        description = "\n".join(p for p in desc_parts if p)

        # Parse salary into numeric for gate filtering
        salary_min = self._parse_salary(salary)

        return {
            "id": f"dice_{guid}",
            "title": title,
            "company": company_name,
            "location": location,
            "description": description[:2000],
            "source": "dice_mcp",
            "url": details_url,
            "company_url": company_url,
            "salary": salary,
            "salary_min": salary_min,
            "employment_type": employment_type,
            "easy_apply": easy_apply,
            "is_remote": is_remote,
            "workplace_types": workplace_types,
            "willing_to_sponsor": willing_to_sponsor,
            "posted_date_raw": posted_date,
            "search_query": search_query,
            # Premium flags for scoring
            "is_dice_job": True,
            "has_direct_apply_link": bool(details_url),
        }

    @staticmethod
    def _parse_salary(salary_str: str) -> Optional[int]:
        """Extract minimum annual salary from Dice salary string.
        
        Examples: 
            "USD 150,000.00 - 200,000.00 per year" -> 150000
            "Depends on Experience" -> None
        """
        if not salary_str or not isinstance(salary_str, str):
            return None

        import re
        # Match patterns like "150,000.00" or "150000"
        matches = re.findall(r'[\d,]+\.?\d*', salary_str.replace(",", ""))
        numbers = []
        for m in matches:
            try:
                val = float(m)
                if val > 1000:  # Likely an annual salary
                    numbers.append(int(val))
            except ValueError:
                pass

        return min(numbers) if numbers else None


# ─────────────────────────────────────────────────────────
# ASYNC WRAPPER for job_monitor.py integration
# ─────────────────────────────────────────────────────────

async def get_dice_jobs_safely(
    queries: Optional[List[str]] = None,
    timeout_seconds: int = 120,
) -> List[Dict]:
    """
    SAFE async wrapper for Dice MCP job search.

    Follows the same pattern as ats_integration.py:
    - Returns empty list on ANY error
    - Respects DICE_MCP_ENABLED feature flag
    - Has timeout protection
    - All errors are logged, never raised

    Usage in job_monitor.py:
        from src.scrapers.dice_mcp_client import get_dice_jobs_safely
        dice_jobs = await get_dice_jobs_safely()
        all_jobs.extend(dice_jobs)
    """
    if not DICE_MCP_ENABLED:
        logger.debug("🎲 Dice MCP disabled by feature flag")
        return []

    import asyncio

    try:
        logger.info("🎲 [Dice MCP] Starting job search...")
        client = DiceMCPClient()

        # Run synchronous MCP calls in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        jobs = await asyncio.wait_for(
            loop.run_in_executor(None, client.search_all, queries),
            timeout=timeout_seconds,
        )

        logger.info("🎲 [Dice MCP] Found %d unique jobs", len(jobs))
        return jobs

    except asyncio.TimeoutError:
        logger.warning("🎲 [Dice MCP] Timeout after %ds", timeout_seconds)
        return []
    except Exception as e:
        logger.error("🎲 [Dice MCP] Unexpected error: %s", e)
        return []
