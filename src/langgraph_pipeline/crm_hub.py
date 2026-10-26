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


def _resolve_origin_url(job_title: str, company: str, job_url: str):
    """(url, note_line): the posting's origin-board url when `job_url` is an aggregator copy, else unchanged.
    Reuses the Bright Data door's resolver (src/search/serpapi_jobs_ingest.py: remembered boards -> the board's
    public API -> one paid search). Never raises."""
    try:
        if not job_url or not (company or "").strip():
            return job_url, ""
        from src.search import serpapi_jobs_ingest as door
        if door._is_origin_host(job_url) or door._is_company_domain(job_url, company):
            return job_url, ""
        found = door._find_origin(job_title, company)
        if not found:
            logger.info(f"[crm_hub] aggregator {door._host(job_url)}, origin not found — deal keeps the copy's url: {job_title} @ {company}")
            return job_url, f"\u26a0\ufe0f Found on an aggregator ({door._host(job_url)}); the employer's own posting was not found — look for it before applying."
        origin, _otitle = found
        logger.info(f"[crm_hub] aggregator {door._host(job_url)} -> origin {origin}: {job_title} @ {company}")
        return origin, f"\U0001f517 Origin posting: {origin} (first seen on {door._host(job_url)})"
    except Exception as e:
        logger.debug(f"[crm_hub] origin resolution unavailable ({e}); url unchanged")
        return job_url, ""


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
    source_prefix: str = "HIRING-VJH-LEAD",
    answer: dict = None,
) -> bool:
    """POST the job application to CTO AIPA CRM hub. Returns True on success.

    answer (added 18 Oct 2026, optional): a dict the caller passes in to receive cto-aipa's parsed JSON
    answer on a 2xx ({"ok", "hubspot": {"dealId"}, "duplicate", "decided", "stage", "dealId"}). notify_node
    needs the deal id to put the ⏳ / ❌ buttons on the alert. Left as None, nothing is read: every
    existing caller behaves exactly as before.
    """
    secret = (os.environ.get("OUTREACH_SECRET") or "").strip()
    if not secret:
        logger.debug("[crm_hub] OUTREACH_SECRET not set — skipping CRM push")
        return False

    # 2026-10-26 (Elena): "if VJH finds a job presented by a paid aggregator it will automatically head to its
    # original job board, wire the original link inside the deal note, with the kit prepared from the original
    # source". The Bright Data door does this since 24 Oct; this door (Tailscale via weworkremotely, Clara via
    # remotefront) did not. Same resolver, same rule: the deal carries the ORIGIN url, so the apply kit (which
    # reads the posting url from the deal's note) builds the CV, letter and defenses from the employer's own
    # posting. Fails open: any failure leaves the url exactly as it came.
    job_url, origin_line = _resolve_origin_url(job_title, company, job_url)
    if origin_line:
        notes = (notes + "\n" if notes else "") + origin_line

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
        # Drives the HubSpot deal name: "[{sourcePrefix}] {jobTitle} @ {company}".
        # UNVERIFIED jobs pass a different prefix (2026-08-18) so a card the bot could
        # not read is never visually identical to one that cleared every filter —
        # which is exactly how the Optum lead reached Elena looking fully vetted.
        "sourcePrefix": source_prefix,
        "jobTitle": job_title,
        "company": company,
        "notes": f"\u26a0\ufe0f MANUAL APPLY REQUIRED \u2014 VJH found this job and generated a cover letter, but did NOT submit. Click the job URL above + paste the cover letter. Cover letter path: see local materials/ folder.",
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
                if answer is not None:
                    try:
                        parsed = json.loads(resp.read().decode("utf-8", "replace") or "{}")
                        if isinstance(parsed, dict):
                            answer.update(parsed)
                    except Exception:
                        pass        # an unreadable answer only means: no deal id, so no buttons
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
