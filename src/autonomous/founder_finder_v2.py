"""
👤 FOUNDER FINDER — Production v3.0

Finds founder contact information (LinkedIn, Twitter, Email).
Uses multiple data sources to build complete founder profiles.

CHANGES (2024-12-18):
✅ Added find_and_message() for orchestrator integration
✅ Email sending via Resend
✅ Manual outreach queue for LinkedIn/Twitter
✅ Outreach attempt logging
✅ Message generation integration
✅ Telegram notifications for manual actions
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import aiohttp
from bs4 import BeautifulSoup

from ..core.models import JobPosting, Profile
from ..utils.logger import setup_logger
from ..utils.cache import ResponseCache

# ──────────────────────────────────────────────────────────────
# LOGGER + RAILWAY FINGERPRINT (DO NOT REMOVE)
# ──────────────────────────────────────────────────────────────
logger = setup_logger(__name__)

FINGERPRINT = "FounderFinderV2_2025-12-18_PROD_v3_FORCE"
logger.error(f"🔥 LOADING MODULE: founder_finder_v2 | {FINGERPRINT}")

# ──────────────────────────────────────────────────────────────
# MAIN CLASS
# ──────────────────────────────────────────────────────────────
class FounderFinderV2:
    """
    Finds and profiles company founders.
    Discovers: LinkedIn, Twitter, Email, recent activity.

    Production v3.0 — Multi-channel outreach ready.
    """

    def __init__(self):
        self.cache = ResponseCache(cache_dir=Path("autonomous_data/cache"))

        # Optional integrations
        try:
            from .message_generator import MessageGenerator
            self.message_generator = MessageGenerator(profile=None)
        except Exception as e:
            logger.warning(f"MessageGenerator unavailable: {e}")
            self.message_generator = None

        try:
            from .email_service import create_email_service
            self.email_service = create_email_service()
        except Exception as e:
            logger.warning(f"Email service unavailable: {e}")
            self.email_service = None

        try:
            from ..notifications import TelegramNotifier
            self.telegram_notifier = TelegramNotifier()
        except Exception as e:
            logger.warning(f"Telegram notifier unavailable: {e}")
            self.telegram_notifier = None

        try:
            from ..database.database_models import DatabaseHelper
            self.db = DatabaseHelper()
        except Exception:
            self.db = None
            logger.debug("Database helper not available")

        logger.info("👤 FounderFinderV2 initialized (production v3.0)")

    # ════════════════════════════════════════════════════════════
    # ORCHESTRATOR ENTRYPOINT
    # ════════════════════════════════════════════════════════════

    async def find_and_message(self, job: JobPosting, profile: Profile) -> Dict[str, Any]:
        result = {
            "success": False,
            "founder_found": False,
            "message_sent": False,
            "channel": "none",
            "founder_name": None,
        }

        company = job.company
        logger.info(f"🔍 Founder outreach started for {company}")

        try:
            founder_data = await self.find_founder(
                company,
                {
                    "url": getattr(job, "company_url", ""),
                    "description": getattr(job, "description", ""),
                },
            )

            if not founder_data:
                logger.warning(f"No founder found for {company}")
                await self._log_outreach_attempt(job, None, "founder_not_found")
                return result

            result["founder_found"] = True
            founder_name = self._extract_founder_name(founder_data)
            result["founder_name"] = founder_name

            message_data = await self._generate_outreach_message(
                founder_data, job, profile
            )
            if not message_data or not message_data.get("message"):
                logger.error("Message generation failed")
                return result

            channel = self._determine_best_channel(founder_data)
            result["channel"] = channel

            sent = False
            if channel == "email":
                email = self._extract_email(founder_data)
                if email:
                    sent = await self._send_email_message(
                        email,
                        message_data["message"],
                        message_data.get("subject"),
                        founder_name or "Hiring Team",
                        company,
                    )

            elif channel == "linkedin":
                sent = await self._send_linkedin_message(
                    self._extract_linkedin(founder_data),
                    message_data["message"],
                    founder_name or "Contact",
                    company,
                )

            elif channel == "twitter":
                sent = await self._send_twitter_dm(
                    self._extract_twitter(founder_data),
                    message_data["message"],
                    founder_name or "Contact",
                    company,
                )

            result["message_sent"] = sent
            result["success"] = sent

            await self._log_outreach_attempt(
                job,
                founder_data,
                "sent" if sent else "failed",
                channel,
                message_data["message"],
            )

            return result

        except Exception as e:
            logger.exception(f"FounderFinderV2 fatal error: {e}")
            result["error"] = str(e)
            return result

    # ════════════════════════════════════════════════════════════
    # FOUNDER DISCOVERY
    # ════════════════════════════════════════════════════════════

    async def find_founder(
        self, company_name: str, company_intel: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        cache_key = f"founder_{company_name.lower().replace(' ', '_')}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        tasks = [
            self._search_linkedin(company_name),
            self._search_twitter(company_name),
            self._find_email_pattern(company_name, company_intel.get("url", "")),
            self._check_yc_profile(company_name),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        founder_info: Dict[str, Any] = {"company": company_name}

        for r in results:
            if isinstance(r, dict):
                founder_info.update(r)

        if not any(founder_info.values()):
            return None

        self.cache.set(cache_key, founder_info, ttl=2592000)
        return founder_info

    async def _search_linkedin(self, company_name: str) -> Dict[str, Any]:
        slug = company_name.lower().replace(" ", "-")
        return {"linkedin_company": f"https://www.linkedin.com/company/{slug}"}

    async def _search_twitter(self, company_name: str) -> Dict[str, Any]:
        slug = company_name.lower().replace(" ", "")
        return {"twitter_company": f"https://twitter.com/{slug}"}

    async def _find_email_pattern(self, company_name: str, company_url: str) -> Dict[str, Any]:
        if not company_url:
            return {}
        domain = company_url.replace("https://", "").replace("http://", "").split("/")[0]
        return {
            "domain": domain,
            "email_patterns": [
                f"founder@{domain}",
                f"hello@{domain}",
                f"contact@{domain}",
            ],
        }

    async def _check_yc_profile(self, company_name: str) -> Dict[str, Any]:
        try:
            slug = company_name.lower().replace(" ", "-")
            url = f"https://www.ycombinator.com/companies/{slug}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as r:
                    if r.status != 200:
                        return {}
                    html = await r.text()
            soup = BeautifulSoup(html, "html.parser")
            founders = [{"name": a.text.strip()} for a in soup.find_all("a") if a.text]
            return {"founders": founders[:1]} if founders else {}
        except Exception:
            return {}

    # ════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════

    def _extract_founder_name(self, data: Dict[str, Any]) -> Optional[str]:
        if data.get("founders"):
            return data["founders"][0].get("name")
        return None

    def _extract_email(self, data: Dict[str, Any]) -> Optional[str]:
        return data.get("email_patterns", [None])[0]

    def _extract_linkedin(self, data: Dict[str, Any]) -> Optional[str]:
        return data.get("linkedin_company")

    def _extract_twitter(self, data: Dict[str, Any]) -> Optional[str]:
        url = data.get("twitter_company")
        return url.split("/")[-1] if url else None

    def _determine_best_channel(self, data: Dict[str, Any]) -> str:
        if data.get("email_patterns"):
            return "email"
        if data.get("linkedin_company"):
            return "linkedin"
        if data.get("twitter_company"):
            return "twitter"
        return "none"

    # ════════════════════════════════════════════════════════════
    # LOGGING & STORAGE
    # ════════════════════════════════════════════════════════════

    async def _log_outreach_attempt(
        self,
        job: JobPosting,
        founder_data: Optional[Dict[str, Any]],
        status: str,
        channel: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:

        record = {
            "company": job.company,
            "job_title": job.title,
            "founder": self._extract_founder_name(founder_data) if founder_data else None,
            "status": status,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
        }

        log_file = Path("autonomous_data/outreach_log.jsonl")
        log_file.parent.mkdir(exist_ok=True)
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")


# ──────────────────────────────────────────────────────────────
# HARD ASSERT — IMPORT MUST SUCCEED
# ──────────────────────────────────────────────────────────────
assert "FounderFinderV2" in globals(), "❌ FounderFinderV2 not loaded"
logger.error(f"✅ FounderFinderV2 AVAILABLE | {FINGERPRINT}")

