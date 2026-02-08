"""
📬 FOLLOW-UP ENGINE — Auto follow-ups at +3 and +8 days
Integrated into the autonomous cycle.

How it works:
1. When an application or outreach email is sent, record it via record_sent()
2. On each autonomous cycle, check_and_send_follow_ups() runs
3. At day 3: sends a soft check-in follow-up
4. At day 8: sends a value-add follow-up
5. Max 2 follow-ups per application — no spamming

Storage: autonomous_data/follow_ups.json
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# ─────────────────────────────────────────────────────
# FOLLOW-UP SCHEDULE
# ─────────────────────────────────────────────────────
FOLLOW_UP_DAY_1 = 3   # First follow-up: 3 days after sending
FOLLOW_UP_DAY_2 = 8   # Second follow-up: 8 days after sending
MAX_FOLLOW_UPS = 2     # Hard cap per application


class FollowUpEngine:
    """
    Lightweight, file-based follow-up tracker.
    
    Record format (in follow_ups.json):
    {
        "company::title": {
            "company": "Anthropic",
            "title": "AI Product Engineer",
            "email": "founder@anthropic.com",
            "channel": "email",         # email | outreach | ats
            "sent_at": "2026-02-05T12:00:00",
            "follow_ups_sent": 0,
            "last_follow_up_at": null,
            "got_response": false,
            "subject": "Re: AI Product Engineer at Anthropic"
        }
    }
    """

    def __init__(self):
        self.data_file = Path("autonomous_data/follow_ups.json")
        self.data_file.parent.mkdir(exist_ok=True)
        self.records = self._load()
        logger.info(f"📬 Follow-Up Engine loaded ({len(self.records)} tracked applications)")

    # ─────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────

    def record_sent(
        self,
        company: str,
        title: str,
        email: str,
        channel: str = "email",
        subject: Optional[str] = None,
    ):
        """
        Record that an application or outreach was sent.
        Call this from orchestrator after a successful apply or outreach.
        """
        key = f"{company}::{title}".lower()

        if key in self.records:
            logger.debug(f"📬 Already tracking follow-up for {company} - {title}")
            return

        self.records[key] = {
            "company": company,
            "title": title,
            "email": email,
            "channel": channel,
            "sent_at": datetime.utcnow().isoformat(),
            "follow_ups_sent": 0,
            "last_follow_up_at": None,
            "got_response": False,
            "subject": subject or f"Re: {title} at {company}",
        }

        self._save()
        logger.info(f"📬 Tracking follow-up for {company} — {title[:40]} (email: {email})")

    def mark_response_received(self, company: str, title: str):
        """Mark that we got a response — no more follow-ups needed."""
        key = f"{company}::{title}".lower()
        if key in self.records:
            self.records[key]["got_response"] = True
            self._save()
            logger.info(f"✅ Response received from {company} — stopping follow-ups")

    async def check_and_send_follow_ups(self, email_service) -> Dict[str, int]:
        """
        Check all tracked applications and send follow-ups if due.
        
        Returns: {"checked": N, "sent": M, "skipped": K}
        """
        now = datetime.utcnow()
        stats = {"checked": 0, "sent": 0, "skipped": 0, "errors": 0}

        if not self.records:
            return stats

        for key, record in list(self.records.items()):
            stats["checked"] += 1

            # Skip if got a response
            if record.get("got_response"):
                stats["skipped"] += 1
                continue

            # Skip if max follow-ups reached
            if record.get("follow_ups_sent", 0) >= MAX_FOLLOW_UPS:
                stats["skipped"] += 1
                continue

            # Skip if no email address
            if not record.get("email"):
                stats["skipped"] += 1
                continue

            # Calculate days since sent
            sent_at = datetime.fromisoformat(record["sent_at"])
            days_since = (now - sent_at).days

            # Determine if a follow-up is due
            follow_ups_sent = record.get("follow_ups_sent", 0)

            due = False
            if follow_ups_sent == 0 and days_since >= FOLLOW_UP_DAY_1:
                due = True
            elif follow_ups_sent == 1 and days_since >= FOLLOW_UP_DAY_2:
                due = True

            if not due:
                continue

            # Generate and send the follow-up
            company = record["company"]
            title = record["title"]
            email = record["email"]
            follow_up_num = follow_ups_sent + 1

            subject, body = self._generate_follow_up(
                company, title, days_since, follow_up_num
            )

            try:
                result = await email_service.send_email(
                    to=email,
                    subject=subject,
                    body=body,
                    html=True,
                )

                if result.get("success"):
                    record["follow_ups_sent"] = follow_up_num
                    record["last_follow_up_at"] = now.isoformat()
                    stats["sent"] += 1
                    logger.info(
                        f"📬 Follow-up #{follow_up_num} sent to {company} "
                        f"({email}) — {days_since}d after application"
                    )
                elif result.get("rate_limited"):
                    logger.warning(f"🛡️ Follow-up rate limited for {company} — will retry next cycle")
                    stats["skipped"] += 1
                elif result.get("blocked"):
                    logger.info(f"🚫 Follow-up blocked for {company} ({email}) — ATS email")
                    stats["skipped"] += 1
                else:
                    logger.warning(f"⚠️ Follow-up failed for {company}: {result.get('error', 'unknown')}")
                    stats["errors"] += 1

            except Exception as e:
                logger.error(f"❌ Follow-up send error for {company}: {e}")
                stats["errors"] += 1

        self._save()
        return stats

    def get_summary(self) -> Dict:
        """Get follow-up engine status for daily digest."""
        now = datetime.utcnow()
        total = len(self.records)
        awaiting = 0
        followed_up_once = 0
        followed_up_twice = 0
        got_response = 0

        for record in self.records.values():
            if record.get("got_response"):
                got_response += 1
            elif record.get("follow_ups_sent", 0) == 0:
                awaiting += 1
            elif record.get("follow_ups_sent", 0) == 1:
                followed_up_once += 1
            else:
                followed_up_twice += 1

        return {
            "total_tracked": total,
            "awaiting_first_followup": awaiting,
            "followed_up_once": followed_up_once,
            "followed_up_twice": followed_up_twice,
            "got_response": got_response,
        }

    # ─────────────────────────────────────────────────────
    # EMAIL TEMPLATES
    # ─────────────────────────────────────────────────────

    def _generate_follow_up(
        self, company: str, title: str, days_since: int, follow_up_num: int
    ) -> Tuple[str, str]:
        """Generate follow-up subject and HTML body."""

        if follow_up_num == 1:
            # Day 3: Soft check-in
            subject = f"Following up — {title} at {company}"
            body = f"""<p>Hi there,</p>

<p>I applied for the <b>{title}</b> role at <b>{company}</b> a few days ago 
and wanted to follow up to express my continued interest.</p>

<p>I've built 8+ live AI products in the past year — from a bilingual WhatsApp 
language tutor to an autonomous job hunting engine (the one that found your 
listing!). I bring a rare mix of AI product building and strategic leadership 
(former Deputy CEO).</p>

<p>If you'd like to see what I build, you can try my AI assistant live: 
<a href="https://wa.me/50766623757">wa.me/50766623757</a></p>

<p>Would love to discuss how I can contribute to {company}. 
Happy to jump on a quick call anytime.</p>

<p>Best regards,<br>
Elena Revicheva<br>
<a href="mailto:aipa@aideazz.xyz">aipa@aideazz.xyz</a> · 
<a href="https://aideazz.xyz">aideazz.xyz</a></p>"""

        else:
            # Day 8: Value-add follow-up (final)
            subject = f"Quick thought on the {title} role — {company}"
            body = f"""<p>Hi,</p>

<p>I wanted to reach out one more time about the <b>{title}</b> position 
at <b>{company}</b>.</p>

<p>Since applying, I've been thinking about how my experience building 
AI-powered products could add value to your team. I ship fast — my 
latest project went from idea to production users in 19 countries in 
under 3 months.</p>

<p>I understand you're busy, and if the timing isn't right, no worries 
at all. But if you're still evaluating candidates, I'd love 15 minutes 
to chat about what I could bring to {company}.</p>

<p>Either way, I wish you and the team continued success!</p>

<p>Best,<br>
Elena Revicheva<br>
<a href="mailto:aipa@aideazz.xyz">aipa@aideazz.xyz</a> · 
<a href="https://aideazz.xyz">aideazz.xyz</a></p>"""

        return subject, body

    # ─────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────

    def _load(self) -> Dict:
        if self.data_file.exists():
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                logger.error(f"Failed to load follow_ups.json: {e}")
        return {}

    def _save(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save follow_ups.json: {e}")
