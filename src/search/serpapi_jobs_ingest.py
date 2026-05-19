"""
serpapi_jobs_ingest.py — Google Jobs API feed for VJH + client prospect pipeline.

Queries Google Jobs every 12h for roles Elena targets.
Each result:
  1. Pushed through /api/crm-event pipeline:'hiring'  (VJH track)
  2. If company matches high-intent signals → also pushed as pipeline:'client'
     (the company hiring a CTO/AI lead is also a fractional CTO prospect)

Run: python3 -m src.search.serpapi_jobs_ingest
PM2: managed under cto-aipa ecosystem or standalone cron.
"""

import os
import sys
import time
import json
import logging
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

# ─── Gate import: this script is standalone, so add repo root to sys.path ───
_REPO_ROOT = Path(__file__).parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
try:
    from src.autonomous.job_gate import JobGate  # type: ignore
    _GATE_AVAILABLE = True
except Exception:
    JobGate = None  # type: ignore
    _GATE_AVAILABLE = False

# dotenv_values reads directly from file, unaffected by PM2 env inheritance
_env = dotenv_values(Path(__file__).parents[2] / '.env')

logging.basicConfig(level=logging.INFO, format='[SerpJobs] %(message)s')
log = logging.getLogger(__name__)

SERPAPI_KEY  = _env.get('SERPAPI_KEY') or os.environ.get('SERPAPI_KEY', '')
OUTREACH_URL = (_env.get('CTO_AIPA_WEBHOOK_URL') or os.environ.get('CTO_AIPA_WEBHOOK_URL') or 'https://webhook.aideazz.xyz/cto').rstrip('/')
OUTREACH_SECRET = _env.get('OUTREACH_SECRET') or os.environ.get('OUTREACH_SECRET', '')
STATE_FILE   = Path(__file__).parent / 'serpapi_jobs_seen.json'

JOBS_QUERIES = [
    # Aligned with CAREER_FOCUS: only founding/fractional/AI-builder shapes.
    # NO 'principal', 'VP', 'staff', 'head of X' — those map to Elena's hard-discard filter.
    'fractional CTO remote',
    'AI engineer founding team remote',
    'founding engineer AI remote',
    'AI automation lead remote startup',
    'solutions architect AI startup remote',
]

# Jobs where company is also a fractional-CTO prospect
CLIENT_INTENT_TITLES = [
    'fractional', 'interim', 'head of ai', 'vp ai', 'vp engineering',
    'chief ai', 'chief technology', 'cto', 'technical co-founder',
]


def load_seen() -> set:
    try:
        if STATE_FILE.exists():
            return set(json.loads(STATE_FILE.read_text()))
    except Exception:
        pass
    return set()


def save_seen(seen: set) -> None:
    try:
        STATE_FILE.write_text(json.dumps(list(seen)[-2000:]))
    except Exception:
        pass


def job_id(result: dict) -> str:
    key = (result.get('title', '') + result.get('company_name', '') + result.get('location', '')).lower()
    return hashlib.md5(key.encode()).hexdigest()


def fetch_google_jobs(query: str) -> list:
    if not SERPAPI_KEY:
        log.warning('SERPAPI_KEY not set — skipping')
        return []
    try:
        resp = requests.get('https://serpapi.com/search', params={
            'engine':   'google_jobs',
            'q':        query,
            'hl':       'en',
            'chips':    'date_posted:week',
            'api_key':  SERPAPI_KEY,
        }, timeout=20)
        resp.raise_for_status()
        return resp.json().get('jobs_results', [])
    except Exception as e:
        log.warning(f'SerpAPI error ({query}): {e}')
        return []


def push_crm_event(payload: dict) -> bool:
    if not OUTREACH_SECRET:
        log.warning('OUTREACH_SECRET not set — skipping CRM push')
        return False
    try:
        r = requests.post(
            OUTREACH_URL + '/api/crm-event',
            json=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': 'Bearer ' + OUTREACH_SECRET,
            },
            timeout=15,
        )
        return r.ok
    except Exception as e:
        log.warning(f'CRM push error: {e}')
        return False


def ingest_once() -> None:
    seen = load_seen()
    new_jobs = 0
    client_prospects = 0

    for query in JOBS_QUERIES:
        log.info(f'Querying Google Jobs: {query!r}')
        results = fetch_google_jobs(query)
        log.info(f'  → {len(results)} results')

        for job in results:
            jid = job_id(job)
            if jid in seen:
                continue
            seen.add(jid)
            new_jobs += 1

            title    = job.get('title', '')
            company  = job.get('company_name', '')
            location = job.get('location', '')
            desc     = job.get('description', '')[:800]
            job_url  = ''
            # SerpAPI nests apply links under extensions
            extensions = job.get('extensions', [])
            related    = job.get('related_links', [])
            if related:
                job_url = related[0].get('link', '')

            # ─── HARD GATE: apply Elena's CAREER_FOCUS filter BEFORE HubSpot push ───
            # Was missing — this script bypassed JobGate and polluted HubSpot
            # with Principal/Director/DevOps/big-co deals every run.
            if _GATE_AVAILABLE:
                gate_dict = {
                    'title':       title,
                    'company':     company,
                    'location':    location,
                    'description': desc,
                    'url':         job_url,
                }
                try:
                    if not JobGate.passes(gate_dict):
                        log.info(f'  ✗ GATE REJECT: {title} @ {company}')
                        continue
                except Exception as e:
                    log.warning(f'  ⚠ gate error (allow-through): {e}')

            log.info(f'  + {title} @ {company} ({location})')

            # 1. Hiring pipeline (VJH track)
            push_crm_event({
                'source':   'serpapi_jobs',
                'type':     'application',
                'pipeline': 'hiring',
                'jobTitle': title,
                'company':  company,
                'jobUrl':   job_url,
                'context':  f'[Google Jobs] {title} @ {company} — {location}\n{desc}',
                'stage':    'applied',
            })

            # 2. Client prospect — company hiring a CTO/AI lead = needs fractional help now
            title_lower = title.lower()
            is_client_signal = any(t in title_lower for t in CLIENT_INTENT_TITLES)
            if is_client_signal:
                client_prospects += 1
                push_crm_event({
                    'source':   'serpapi_jobs',
                    'type':     'prospect',
                    'pipeline': 'client',
                    'name':     f'Hiring manager @ {company}',
                    'company':  company,
                    'context':  f'[SerpAPI/GoogleJobs] Company posted "{title}" — actively scaling AI/tech leadership. Prime fractional CTO prospect.\nJob: {job_url}\n{desc[:400]}',
                    'urgency':  5 if 'cto' in title_lower or 'fractional' in title_lower else 4,
                })

            time.sleep(0.5)  # stay under rate limits

        time.sleep(2)  # 1 API call per query, be polite

    save_seen(seen)
    log.info(f'Done — new jobs: {new_jobs}, client prospects: {client_prospects}')


def main() -> None:
    log.info(f'SerpAPI Jobs Ingestor started — {len(JOBS_QUERIES)} queries, running now then every 12h')
    while True:
        try:
            ingest_once()
        except Exception as e:
            log.error(f'Cycle error: {e}')
        log.info('Sleeping 12h...')
        time.sleep(12 * 60 * 60)


if __name__ == '__main__':
    main()
