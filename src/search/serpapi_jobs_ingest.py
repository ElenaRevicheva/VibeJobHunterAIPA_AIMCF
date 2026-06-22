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
import re
import urllib.parse as up
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
# BrightData SERP (May 31 2026): SerpAPI google_jobs quota is exhausted (HTTP 429,
# no top-up). BrightData is now the engine — reuses the same token/zone as cto-aipa's
# brightdata-enrich.ts. brd_json does NOT parse the Google Jobs vertical, so we use
# organic Google search restricted to ATS/job-board domains (returns real postings
# with direct apply links).
BRIGHTDATA_API_TOKEN = _env.get('BRIGHTDATA_API_TOKEN') or os.environ.get('BRIGHTDATA_API_TOKEN', '')
BRIGHTDATA_ZONE      = _env.get('BRIGHTDATA_ZONE') or os.environ.get('BRIGHTDATA_ZONE', '')
BD_API = 'https://api.brightdata.com/request'
JOB_BOARD_SITES = ('(site:wellfound.com OR site:lever.co OR site:greenhouse.io '
                   'OR site:job-boards.greenhouse.io OR site:jobs.ashbyhq.com OR site:ashbyhq.com)')
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

# ─── Remotive: remote-first, REGION-TAGGED board (free API, no key). Its
# `candidate_required_location` field ("Worldwide" / "Americas" / "LATAM" /
# "USA" / "Brazil") lets the iron-clad gate read a REAL region instead of
# guessing from snippets. This is the retargeted well: remote + LATAM-friendly
# + AI-builder, not US-centric Google Jobs. Queries match Elena's profile. ───
REMOTIVE_QUERIES = [
    'AI automation',
    'no-code',
    'prompt',
    'AI agent',
    'AI solutions',
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


def _extract_company(title: str, link: str) -> str:
    """Best-effort company name from a job-post title or ATS URL slug."""
    t = title or ''
    # "Role at Company • Location" / "Role at Company" / "Role @ Company"
    m = re.search(r'\b(?:at|@)\s+([A-Z0-9][\w&.\-’\' ]{1,40})', t)
    if m:
        return re.split(r'[•|\-—]', m.group(1))[0].strip(" -—|·")
    # ATS URL slug: job-boards.greenhouse.io/<company>/... , <company>.lever.co , jobs.ashbyhq.com/<company>
    try:
        u = up.urlparse(link)
        host, path = u.netloc.lower(), [p for p in u.path.split('/') if p]
        if 'lever.co' in host:
            sub = host.split('.lever.co')[0].split('.')[-1]
            if sub and sub != 'jobs':
                return sub.replace('-', ' ').title()
        if 'greenhouse.io' in host and path:
            return path[0].replace('-', ' ').title()
        if 'ashbyhq.com' in host and path:
            return path[0].replace('-', ' ').title()
    except Exception:
        pass
    return ''


def fetch_remotive(query: str) -> list:
    """Remote-first job board with explicit region tags (free, no key).
    Maps `candidate_required_location` → our `location` field so iron_clad_fit
    reads a real region. All Remotive jobs are remote, so we prefix 'Remote —'
    to guarantee the remote signal while preserving the region tag."""
    try:
        r = requests.get(
            'https://remotive.com/api/remote-jobs',
            params={'search': query, 'limit': 50},
            headers={'User-Agent': 'Mozilla/5.0 (VJH job ingest)'},
            timeout=20,
        )
        r.raise_for_status()
        jobs = r.json().get('jobs', [])
    except Exception as e:
        log.warning(f'Remotive fetch error ({query!r}): {e}')
        return []
    out = []
    for j in jobs:
        region = (j.get('candidate_required_location') or 'Worldwide').strip()
        desc = re.sub(r'<[^>]+>', ' ', j.get('description', '') or '')
        desc = re.sub(r'\s+', ' ', desc).strip()
        out.append({
            'title':         j.get('title', ''),
            'company_name':  j.get('company_name', ''),
            'location':      f'Remote — {region}',  # guarantees 'remote' + real region tag
            'description':   desc,
            'related_links': [{'link': j.get('url', '')}],
        })
    return out


def fetch_google_jobs(query: str) -> list:
    """BrightData organic Google search restricted to ATS/job boards.

    Replaces the dead SerpAPI google_jobs feed. Normalizes results to the same
    dict shape the rest of this module expects (title, company_name, location,
    description, related_links)."""
    if not (BRIGHTDATA_API_TOKEN and BRIGHTDATA_ZONE):
        log.warning('BrightData not configured (BRIGHTDATA_API_TOKEN/ZONE) — skipping')
        return []
    q = f'{query} {JOB_BOARD_SITES}'
    url = 'https://www.google.com/search?' + up.urlencode({
        'q': q, 'hl': 'en', 'gl': 'us', 'num': '20', 'tbs': 'qdr:m', 'brd_json': '1',
    })
    try:
        resp = requests.post(
            BD_API,
            json={'zone': BRIGHTDATA_ZONE, 'url': url, 'format': 'raw'},
            headers={'Authorization': 'Bearer ' + BRIGHTDATA_API_TOKEN},
            timeout=45,
        )
        if not resp.ok:
            log.warning(f'BrightData error ({query}): {resp.status_code} {resp.text[:120]}')
            return []
        data = resp.json()
        organic = data.get('organic') or data.get('organic_results') or []
        jobs = []
        for it in organic:
            title = (it.get('title') or '').strip()
            link  = (it.get('link') or it.get('url') or '').strip()
            snippet = (it.get('description') or it.get('snippet') or '').strip()
            if not title or not link:
                continue
            jobs.append({
                'title':         title,
                'company_name':  _extract_company(title, link),
                'location':      '',
                'description':   snippet,
                'related_links': [{'link': link}],
            })
        return jobs
    except Exception as e:
        log.warning(f'BrightData error ({query}): {e}')
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


# iron_clad_fit now lives in the shared src/core/fit_gate.py (single source of truth,
# also used by the LangGraph submit path in nodes.py). Re-exported for callers/tests.
# NOTE: serpapi-jobs runs under SYSTEM python (no pydantic / src.core deps), so a plain
# `from src.core.fit_gate import ...` crashes via src/core/__init__.py → config → pydantic.
# fit_gate.py is stdlib-free, so on that path we load it directly by file (bypassing the
# src.core package __init__). In the venv (bot, submit path) the normal import just works.
try:
    from src.core.fit_gate import iron_clad_fit  # noqa: E402,F401
except Exception:
    import importlib.util as _ilu
    from pathlib import Path as _P
    _spec = _ilu.spec_from_file_location("fit_gate", _P(__file__).parents[1] / "core" / "fit_gate.py")
    _fg = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_fg)  # type: ignore[union-attr]
    iron_clad_fit = _fg.iron_clad_fit  # noqa: F401


def ingest_once() -> None:
    seen = load_seen()
    new_jobs = 0
    client_prospects = 0

    # Retargeted: Remotive (region-tagged remote board) FIRST, then the legacy
    # Google-Jobs feed. Both flow through the same gate + iron_clad_fit, so the
    # well changed without touching the routing.
    sources = [('Remotive', q, fetch_remotive) for q in REMOTIVE_QUERIES] \
            + [('Google Jobs', q, fetch_google_jobs) for q in JOBS_QUERIES]
    for label, query, fetch_fn in sources:
        log.info(f'Querying {label}: {query!r}')
        results = fetch_fn(query)
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
            desc_full = job.get('description', '') or ''
            desc     = desc_full[:800]   # truncated copy for HubSpot storage only
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

            # ── IRON-CLAD FIT GATE: only fully-remote + LATAM/global + AI-augmented
            # roles reach Elena's actionable "I Act TODAY"; the rest are parked in
            # "ignore" so the scraped firehose never floods her view again. ──
            fit = iron_clad_fit(title, location, desc_full)   # gate on FULL desc (keywords can sit past 800 chars)
            hiring_stage = 'applied' if fit else 'lead_parked'
            if fit:
                log.info(f'  IRON-CLAD FIT -> I Act TODAY: {title} @ {company}')
            else:
                log.info(f'  parked (not iron-clad fit): {title} @ {company}')

            # 1. Hiring pipeline (VJH track)
            push_crm_event({
                'source':   'serpapi_jobs',
                'type':     'application',
                'pipeline': 'hiring',
                'sourcePrefix': 'HIRING-VJH-SERP-LEAD',
                'jobTitle': title,
                'company':  company,
                'notes': '\u26a0\ufe0f MANUAL APPLY REQUIRED \u2014 VJH SerpAPI found this job. Click the job URL + apply manually. No cover letter pre-generated for SerpAPI path.',
                'jobUrl':   job_url,
                'context':  f'[Google Jobs] {title} @ {company} — {location}\n{desc}',
                'stage':    hiring_stage,
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
