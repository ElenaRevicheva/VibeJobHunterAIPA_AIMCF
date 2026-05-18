"""
crm_hub.py — Fire-and-forget POST to CTO AIPA /api/crm-event.

Called from notify_node after each meaningful VJH outcome (applied, outreach_sent).
Never raises — CRM write failure must not crash the pipeline.
"""
import logging
import os
from urllib.request import urlopen, Request as URLRequest
import json

logger = logging.getLogger(__name__)

_CRM_URL = None


def _crm_url() -> str:
    global _CRM_URL
    if _CRM_URL is None:
        base = (os.environ.get("CTO_AIPA_WEBHOOK_URL") or "https://webhook.aideazz.xyz/cto").rstrip("/")
        _CRM_URL = f"{base}/api/crm-event"
    return _CRM_URL


def push_application_to_crm(
    *,
    job_title: str,
    company: str,
    job_url: str = "",
    domain: str = "",
    recruiter_email: str = "",
    recruiter_name: str = "",
    stage: str = "applied",
    source: str = "vjh",
    notes: str = "",
    score: float = 0.0,
) -> bool:
    """POST the job application to CTO AIPA CRM hub. Returns True on success."""
    secret = (os.environ.get("OUTREACH_SECRET") or "").strip()
    if not secret:
        logger.debug("[crm_hub] OUTREACH_SECRET not set — skipping CRM push")
        return False

    # Build rich notes so every HubSpot card is actionable
    if not notes:
        notes_parts = []
        if score:
            notes_parts.append(f"Score: {score:.0f}/100")
        if job_url:
            notes_parts.append(f"Apply: {job_url}")
        if stage == "applied":
            notes_parts.append("VJH auto-applied — verify confirmation")
        notes = "\n".join(notes_parts)

    payload = {
        "source": source,
        "type": "application",
        "pipeline": "hiring",
        "jobTitle": job_title,
        "company": company,
        "domain": domain or _domain_from_url(job_url),
        "jobUrl": job_url,
        "stage": stage,
    }
    if notes:
        payload["notes"] = notes
    if recruiter_email:
        payload["recruiterEmail"] = recruiter_email
    if recruiter_name:
        payload["recruiterName"] = recruiter_name

    try:
        body = json.dumps(payload).encode("utf-8")
        req = URLRequest(
            _crm_url(),
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secret}",
            },
            method="POST",
        )
        with urlopen(req, timeout=8) as resp:
            ok = 200 <= resp.status < 300
            if ok:
                logger.info(f"[crm_hub] HubSpot hiring deal posted: {job_title} @ {company}")
            else:
                logger.warning(f"[crm_hub] CRM push returned {resp.status}")
            return ok
    except Exception as e:
        logger.warning(f"[crm_hub] CRM push failed (non-fatal): {e}")
        return False


def _domain_from_url(url: str) -> str:
    """Extract bare domain from a job URL."""
    try:
        from urllib.parse import urlparse
        h = urlparse(url).netloc
        return h.removeprefix("www.") if h else ""
    except Exception:
        return ""
