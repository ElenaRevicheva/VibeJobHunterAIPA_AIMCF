import asyncio
import logging
from datetime import datetime

from src.scrapers.ats_scraper import ATSScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ATS_RUNNER")

ATS_INTERVAL_SECONDS = 60 * 60  # 1 hour


async def run_ats_once():
    run_id = datetime.utcnow().isoformat()
    logger.info(f"[ATS][START] run_id={run_id}")

    try:
        scraper = ATSScraper()
        jobs = await scraper.fetch_all_jobs(
            keywords=[
                "ai",
                "machine learning",
                "ml",
                "founder",
                "python",
                "research",
            ]
        )
        logger.info(f"[ATS][DONE] jobs_found={len(jobs)}")
    except Exception as e:
        logger.exception("[ATS][ERROR]")


async def ats_background_loop():
    logger.info("🧠 ATS hourly background runner ACTIVE")

    while True:
        await run_ats_once()
        await asyncio.sleep(ATS_INTERVAL_SECONDS)
