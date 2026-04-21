#!/usr/bin/env python3
"""
Fire 4 marketing-engine LinkedIn posts via Make.com, one after another, each with a fixed
GitHub raw image (architecture / workflow PNGs). Does not change the orchestrator schedule.

Usage (from repo root, with env like production):
  python3 scripts/run_marketing_engine_four_image_test.py --sleep-seconds 45

Env: ANTHROPIC_API_KEY, MAKE_WEBHOOK_URL_LINKEDIN (same as vibejobhunter).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception as e:
    print(f"warning: could not load .env via python-dotenv: {e}", file=sys.stderr)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("marketing_image_test")

GITHUB_BASE = (
    "https://raw.githubusercontent.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF/main/assets"
)

# Four posts: three lane types + one repeat with the fourth diagram (all EN for predictability).
STEPS = [
    (
        "marketing_engine_geo_seo",
        "en",
        f"{GITHUB_BASE}/marketing_engine_architecture.png",
    ),
    (
        "marketing_engine_content_attribution",
        "en",
        f"{GITHUB_BASE}/marketing_engine_architecture_1.png",
    ),
    (
        "marketing_engine_outreach_triage",
        "en",
        f"{GITHUB_BASE}/marketing_engine_workflow.png",
    ),
    (
        "marketing_engine_geo_seo",
        "en",
        f"{GITHUB_BASE}/marketing_engine_workflow_1.png",
    ),
]


async def main(sleep_seconds: float, dry_run: bool) -> int:
    if not os.getenv("MAKE_WEBHOOK_URL_LINKEDIN"):
        log.error("MAKE_WEBHOOK_URL_LINKEDIN is not set")
        return 1
    if dry_run:
        log.info("DRY RUN — probing images only")
        from src.notifications.linkedin_cmo_v4 import _probe_image_url_downloads_like_buffer

        for i, (ptype, lang, url) in enumerate(STEPS, start=1):
            ok = _probe_image_url_downloads_like_buffer(url)
            log.info("  %s/%s %s probe=%s", i, len(STEPS), url.split("/")[-1], ok)
        return 0

    from src.notifications.linkedin_cmo_v4 import LinkedInCMO

    cmo = LinkedInCMO()
    if not cmo.enabled:
        log.error("LinkedIn CMO disabled (no Make webhook)")
        return 1

    for i, (ptype, lang, img_url) in enumerate(STEPS, start=1):
        log.info("=== Post %s/%s type=%s lang=%s image=%s ===", i, len(STEPS), ptype, lang, img_url.split("/")[-1])
        ok = await cmo.post_to_linkedin(ptype, lang, forced_image_url=img_url)
        if not ok:
            log.error("Post %s failed — stopping sequence", i)
            return 1
        if i < len(STEPS) and sleep_seconds > 0:
            log.info("Sleeping %.0f s before next post…", sleep_seconds)
            await asyncio.sleep(sleep_seconds)

    log.info("All %s marketing-engine posts sent.", len(STEPS))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=60.0,
        help="Pause between webhook calls (default 60)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only HTTP-probe the 4 image URLs; do not post",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(main(args.sleep_seconds, args.dry_run)))
