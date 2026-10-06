"""
serpapi_jobs_ingest.py — Google job-board search feed for VJH + client prospect pipeline.

⚠️ THE NAME IS HISTORICAL. SerpAPI is NOT used: its quota died 31 May 2026 and the
account was cancelled 11 Aug 2026. The engine is BRIGHT DATA (fetch_google_jobs below).
The file and PM2 name `serpapi-jobs` are kept only so the running process, its logs and
the PM2 config keep matching; renaming them is a deploy change, not a cleanup.

Queries Google (via Bright Data) every 12h for roles Elena targets.
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

# 2026-09-28 — evidence memory: keep the posting each decision is made on (job_listings), so the
# judge replay re-judges HER decision on the same text. Missing module = no memory, never a crash.
try:
    from src.database.database_models import record_judged_posting  # type: ignore
except Exception:
    def record_judged_posting(*_a, **_k):  # type: ignore
        return False

# dotenv_values reads directly from file, unaffected by PM2 env inheritance
_env = dotenv_values(Path(__file__).parents[2] / '.env')

logging.basicConfig(level=logging.INFO, format='[SerpJobs] %(message)s')
log = logging.getLogger(__name__)

# SERPAPI_KEY removed 2026-09-17: read here, used nowhere, and its presence kept
# suggesting SerpAPI was still live.
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

# ─── BORDERLINE ALERT (added 2026-08-14) — PURELY ADDITIVE ───────────────────
# A gate-vs-judge DISAGREEMENT must never die silently.
#
# Earned from Scale Army: VJH found them on Aug 5, `iron_clad_fit` vetoed on the
# board's country roster (Egypt, Argentina, Ethiopia, South Africa, Nigeria — no
# Panama) and the job was parked in the "ignore" stage. Nine days later their
# recruiter emailed Elena directly inviting her to apply to the senior version of
# the same role. Re-run today, the gate vetoes BOTH Scale Army roles while the LLM
# judge approves both — so without that email the opportunity would simply have
# vanished.
#
# The gate is NOT loosened here. It is very likely right (Panama really is absent
# from that roster) and widening it would re-open the 2026-07-30 flood of jobs
# Elena cannot legally hold. What changes is only that a disagreement now gets
# announced instead of buried.
#
# Measured before building, on a 40-deal sample of the parked pile re-fetched live
# from Ashby/Greenhouse: 0/26 passed BOTH gates (so parking is broadly correct and
# a mass rescue would be waste), and 1/26 was gate-NO/judge-YES ≈ 4% — about two a
# week. Small enough to alert on, which is why this is an alert and not a stage change.
#
# ADDITIVE CONTRACT — this block must never alter existing behaviour:
#   * `fit` and `hiring_stage` are read, NEVER reassigned.
#   * every failure is swallowed and logged; ingest continues regardless.
#   * with TELEGRAM_* unset it silently does nothing.
TELEGRAM_BOT_TOKEN = _env.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = _env.get('TELEGRAM_CHAT_ID')   or os.environ.get('TELEGRAM_CHAT_ID', '')


def _borderline_check(title: str, company: str, location: str, desc: str):
    """(is_borderline, judge_reason) for a job the iron-clad gate rejected.

    Returns (False, '') on ANY problem — a broken alert path must never change
    which jobs get ingested.
    """
    try:
        from src.core.llm_judge import judge_fit
        ok, why = judge_fit(title, company, location, desc)
        if ok and not str(why).startswith('JUDGE UNAVAILABLE'):
            return True, str(why)
    except Exception as e:
        log.debug(f'  borderline check unavailable ({e})')
    return False, ''


def _borderline_alert(title: str, company: str, location: str, job_url: str, why: str) -> None:
    """Tell Elena a parked job split the gate and the judge. Best-effort only."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    import html as _html
    e = _html.escape
    text = (
        f"🟡 <b>BORDERLINE — worth your eyes</b>\n\n"
        f"<b>{e(title)}</b>\n{e(company)}\n\n"
        f"📍 <code>{e(location or 'not stated')}</code>\n\n"
        f"❌ iron-clad gate: NOT a fit (location roster / eligibility)\n"
        f"✅ AI judge: a fit — {e(why[:220])}\n\n"
        f"Parked in HubSpot so it can't clutter “I Act TODAY”. "
        f"Your call:\n{e(job_url or '(no URL)')}"
    )
    try:
        requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            json={'chat_id': TELEGRAM_CHAT_ID, 'text': text,
                  'parse_mode': 'HTML', 'disable_web_page_preview': False},
            timeout=15)
    except Exception as e:
        log.debug(f'  borderline alert not sent ({e})')

JOBS_QUERIES = [
    # 2026-09-29 EDITED IN PLACE, not appended — same 18 queries, same bill. 14 said only "remote",
    # which on Google means US-remote: of 98 jobs this door parked 27-29 Sep, read in full, 77 were
    # off-lane and 17 failed the gate (mostly US-only); 1 would have passed. Each now carries
    # "latin america", like the three that already did. 'remote worldwide' left as it is.
    # Aligned with CAREER_FOCUS: only founding/fractional/AI-builder shapes.
    # NO 'principal', 'VP', 'staff', 'head of X' — those map to Elena's hard-discard filter.
    # 2026-09-16: EXCEPT AI leadership ('head of AI', 'chief AI officer'), which is a lane.
    'fractional CTO remote latin america',
    # 2026-09-20 SWAPPED, not appended — these are PAID searches twice a day, so the two
    # generic engineer queries that used to sit here ('AI engineer founding team remote',
    # 'founding engineer AI remote') were paying to generate her rejections: engineer-titled
    # roles were 62% of the ACT-TODAY queue but 58% of her negatives and 17% of her positives,
    # every reason being "5-8 years", "4+ years ... MLOps", "8+ years", "Senior-level backend".
    # Replaced 1:1 with the two shapes her positives actually came from, so the query count
    # and the bill are unchanged. fit_gate now also vetoes those titles by name.
    'AI automation specialist remote latin america',   # AI Automation Specialist @ LanceMart
    # 2026-10-06 SWAPPED IN PLACE (all four swaps below) — same 18 queries, same bill. Measured from
    # Oracle's serpapi-jobs log over the 15 complete runs on this list (29 Sep – 6 Oct), counting
    # DISTINCT jobs: these four had 0 jobs past the fit gate. Their results / past the first gate /
    # gate-NO-judge-YES were: exec assistant 88/0/0, technical account manager 109/5/0, AI agent
    # developer 100/8/0, AI integration engineer 100/5/3. 'AI solutions consultant' also had 0 but
    # 11 past the first gate, so it stays. For scale, the best were n8n automation engineer (4 past
    # the fit gate) and AI automation lead / AI automation engineer (3 each). The replacements are
    # titles from her Professional Outlook (Oct 2026, "Where I fit"). The protected queries (AI chief
    # of staff, both creative ones, AI product manager, chief AI officer, head of AI) are unchanged.
    'AI implementation lead remote latin america',      # was 'technical account manager AI automation remote latin america'
    'AI automation lead remote latin america startup',
    'solutions architect AI startup remote latin america',
    # 2026-07-30 APPENDED — the AI-automation category (Elena's shipped skill set,
    # $3-6K/mo remote band). Original 5 queries above untouched.
    'AI automation engineer remote latin america',
    'AI workflow architect remote latin america',       # was 'AI agent developer remote worldwide'
    'n8n automation engineer remote latin america',
    'AI transformation lead remote latin america',      # was 'AI integration engineer remote latin america contract'
    # 2026-08-18 APPENDED — AI chief-of-staff / AI-proficient EA-PA lane
    # (wealthy-principal / family-office roles included). Same supply-gap fix
    # as Torre: job_gate.py/fit_gate.py already carve these titles through,
    # they were never being searched for on this source either.
    'AI chief of staff remote latin america',
    # 2026-10-06: the exec-assistant query found 0 jobs past even the first gate in 15 runs. The
    # chief-of-staff lane is still searched (line above) and covered by the free sources.
    'generative AI product lead remote latin america',  # was 'AI executive assistant remote latin america'
    'AI operations lead remote latin america startup',
    # 2026-09-16 APPENDED — AI product / consulting / leadership lanes
    # (src/core/target_lanes.py). Every query here is a paid search twice a day, so
    # only the four highest-yield shapes are added; the free sources carry the rest.
    'AI product manager remote latin america',
    'chief AI officer remote latin america startup',
    'AI solutions consultant remote latin america',
    'head of AI remote latin america startup',
    # 2026-09-28 APPENDED — creative AI lane (src/core/target_lanes.py): 8 published AI films
    # and a production pipeline were invisible to her own job search. Two paid shapes only;
    # Remotive and Torre carry the rest for free.
    'creative technologist generative AI remote latin america',
    'AI video producer remote latin america',
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
    # 2026-07-30 APPENDED (AI-automation category).
    'AI automation engineer',
    'workflow automation',
    'AI integration engineer',
    # 2026-10-06 APPENDED — the Professional Outlook titles (Oct 2026, p.7 "Where I fit") that the
    # queries above do not already match ('AI automation' already covers AI Automation Lead). Free
    # searches. NOTE: ingest_once does not call fetch_remotive today (the bot's JobMonitor owns
    # Remotive, see ingest_once), so this list only takes effect once a caller uses it.
    'AI operations lead',
    'AI implementation lead',
    'AI workflow architect',
    'AI systems operator',
    'agentic workflow designer',
    'AI product automation lead',
    'AI transformation lead',
    'AI innovation lead',
    'AI adoption lead',
    'generative AI product lead',
    'AI prototyping lead',
    'creative technologist',
    'generative AI producer',
    'creative AI pipeline',
    'GenAI production lead',
    'AI innovation producer',
]

# Jobs where company is also a fractional-CTO prospect
CLIENT_INTENT_TITLES = [
    'fractional', 'interim', 'head of ai', 'vp ai', 'vp engineering',
    'chief ai', 'chief technology', 'cto', 'technical co-founder',
]
# 2026-10-06 — WHOLE words/phrases only. Substring matching let 'cto' fire inside "Director" and
# "October", which (with blank company names) made the junk "Hiring manager @ — outreach" deals:
# 13 since 29 Sep, 99 in total.
_CLIENT_INTENT_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(t) for t in CLIENT_INTENT_TITLES) + r')\b', re.I)


def _client_intent(title: str) -> bool:
    return bool(_CLIENT_INTENT_RE.search(title or ''))


# 2026-10-06 — the seen-list keeps ARRIVAL order and drops the OLDEST. It was a set saved as
# list(set)[-2000:], which trims in hash order, not by age: the same recent jobs fell out at every
# save and came back 12h later as "new" (6 Oct: "new jobs: 30" was about 15 truly new). A dict is an
# ordered set. The existing file (a plain JSON list) loads as-is; its old order is arbitrary, so the
# first save after this change trims among those OLD entries only — everything added since is in
# true order. Cap unchanged.
SEEN_CAP = 2000


def load_seen() -> dict:
    try:
        if STATE_FILE.exists():
            return dict.fromkeys(json.loads(STATE_FILE.read_text()))
    except Exception:
        pass
    return {}


def mark_seen(seen: dict, jid: str) -> None:
    """Record a sighting at the NEWEST end. A job Google still shows is moved back to the end, so a
    posting that stays live is never the one evicted and then re-processed as 'new'."""
    seen.pop(jid, None)
    seen[jid] = True


def save_seen(seen: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(list(seen)[-SEEN_CAP:]))
    except Exception:
        pass


def job_id(result: dict) -> str:
    key = (result.get('title', '') + result.get('company_name', '') + result.get('location', '')).lower()
    return hashlib.md5(key.encode()).hexdigest()


# 2026-10-06 — a company name must name a company. cto-aipa refuses a hiring job with a blank company
# (HTTP 400), and a word like "jobs" or "remote" would only make a junk deal name instead. Words, not
# substrings: "US Bank" or "Scale Army Careers" are companies, "Remote Work" and "Latin America" are not.
_GENERIC_COMPANY_WORDS = frozenset({
    'jobs', 'job', 'careers', 'career', 'remote', 'apply', 'application', 'hiring', 'embed', 'www',
    'boards', 'board', 'company', 'companies', 'search', 'home', 'eu', 'en', 'api', 'work', 'now',
    'online', 'anywhere', 'worldwide', 'global', 'latam', 'latin', 'america', 'us', 'usa',
    'lever', 'greenhouse', 'ashby', 'ashbyhq', 'wellfound', 'linkedin', 'indeed', 'n/a', 'unknown',
    'a', 'an', 'the', 'and', 'or', 'of', 'in', 'for', 'from', 'with', 'to',
})
# Words that make one side of "<Company> - <Title>" the TITLE side.
# 2026-10-06 review: 'lead' → 'lead(?:er)?' — "Impact Leader - Solution Architect /…" named "Impact Leader"
# as the company because "Leader" did not read as a role.
_ROLE_WORD = re.compile(
    r'\b(?:engineer|developer|manager|lead(?:er)?|head|director|officer|chief|cto|ceo|vp|architect|designer|'
    r'specialist|consultant|analyst|scientist|producer|operator|technologist|assistant|coordinator|'
    r'strategist|founder|intern|associate|administrator|writer|editor|researcher|recruiter|'
    r'representative|advisor|expert|creator|filmmaker|builder|freelancer|contractor|executive)s?\b',
    re.I)
# A right-hand side like "Remote", "Remote, Medellín" or "Full-time" is a location/terms, not a company.
_NOT_A_COMPANY = re.compile(r'\b(?:remote|hybrid|on-?site|anywhere|worldwide|full[- ]time|part[- ]time)\b', re.I)


def _is_generic_company(name: str) -> bool:
    words = re.findall(r'[a-z0-9/]+', (name or '').lower())
    if not words or all(w in _GENERIC_COMPANY_WORDS or w.isdigit() for w in words):
        return True
    return words[-1] == 'jobs'     # "Remote Jobs", "Automation Jobs": a board's listing page, not an employer


def _company_from_url(link: str) -> str:
    """Company slug from an ATS URL; '' when the URL names none.

    2026-10-06: Lever's usual shape is jobs.lever.co/<company>/<id> — the code read the subdomain
    "jobs", rejected it and never looked at the path, so DEUNA (jobs.lever.co/deuna/...) and Airtm
    went to cto-aipa with a blank company and were refused (DEUNA 7 times, Airtm once). Path segments are now
    URL-decoded too ("Scale%20Army%20Careers" was being used as a company name).
    """
    try:
        u = up.urlparse(link or '')
        host = u.netloc.lower().split(':')[0]
        path = [up.unquote(p) for p in u.path.split('/') if p]
        slug = ''
        if host == 'lever.co' or host.endswith('.lever.co'):
            # <company>.lever.co, or jobs.lever.co/<company>/... (and jobs.eu.lever.co/<company>/...)
            sub = host[:-len('.lever.co')].split('.')[-1] if host.endswith('.lever.co') else ''
            slug = sub if sub and not _is_generic_company(sub) else (path[0] if path else '')
        elif 'greenhouse.io' in host and path:
            slug = path[0]
            if slug.lower() == 'embed':   # boards.greenhouse.io/embed/job_app?for=<company>&token=...
                slug = (up.parse_qs(u.query).get('for') or [''])[0]
        elif 'ashbyhq.com' in host and path:
            slug = path[0]
        elif 'wellfound.com' in host and len(path) >= 2 and path[0] == 'company':
            slug = path[1]                # wellfound.com/company/<company>/jobs/...
        name = slug.replace('-', ' ').title() if slug else ''
        return '' if _is_generic_company(name) else name
    except Exception:
        return ''


# 2026-10-06 review: the only thing that makes the RIGHT side of "<Title> - <X>" a company is a legal
# form ("Marketing Operations Manager - AI Collaborator, Inc."). Without one, the right side of the
# blank-company titles in Oracle's serpapi-jobs log was often a place, a term or a category
# ("United States", "Contract", "AI & Automation"), and each would have become a HubSpot company
# and the addressee of a cover letter. A real employer on the right ("… Engineer - Minted") is lost.
_LEGAL_SUFFIX = re.compile(r',?\s(?:Inc\.?|LLC|Ltd\.?|GmbH|S\.A\.?|Corp\.?)$')
_MAX_COMPANY_CHARS = 40


def _plausible_company(c: str) -> bool:
    """A title-derived candidate may be used as a company name. 2026-10-06 review: Google cuts long
    titles with '...' ("Hardware ...", "Web3 ..."), and a long run of words is a phrase, not a name."""
    return bool(c) and len(c) <= _MAX_COMPANY_CHARS and not c.endswith(('...', '…')) \
        and not _is_generic_company(c) and not _NOT_A_COMPANY.search(c)


def _company_from_title(t: str) -> str:
    """Fallback when the URL names no company. 2026-10-06.

    "<Title> @ <Company>" (Ashby-style, lowercase names too: "… @ n8n"), then Google's
    "<Company> - <Title>" (Lever's page title, e.g. "DEUNA - Product Head of AI"): the LEFT side,
    only when the side after the first dash reads as a job title and the left side does not. The
    right side is taken only when it ends in a legal form ("…, Inc."). Anything after " | " is
    dropped first — in the blank-company titles of Oracle's serpapi-jobs log it was mostly a place,
    a reference or noise ("United States", "REF#302477", "Week 3"); the odd employer named there
    ("Wiz Careers") is lost, which costs less than a junk company. Returns '' rather than guess.
    """
    m = re.search(r'(?:^|\s)@\s*([A-Za-z0-9][\w&.,\-’\' ]{1,40})', t)
    if m:
        c = re.split(r'[•|—]|\s-\s', m.group(1))[0].strip(" -—|·,")
        cut = c == m.group(1).strip(" -—|·,") and t[m.end(1):m.end(1) + 1] == '…'
        # A lowercase name is one token ("n8n"); "@ fast-growing, mission-driven startup" is a phrase.
        phrase = c[:1].islower() and ' ' in c
        if not cut and not phrase and _plausible_company(c):
            return c
    parts = [p.strip() for p in re.split(r'\s+[-–—]\s+', t.split(' | ')[0]) if p.strip()]
    while parts and _is_generic_company(parts[-1]):   # trailing " - Lever" / " - Jobs"
        parts.pop()
    if len(parts) >= 2:
        left, right = parts[0], parts[-1]
        cand = ''
        if _ROLE_WORD.search(parts[1]) and not _ROLE_WORD.search(left):
            cand = left
        elif _LEGAL_SUFFIX.search(right) and not _ROLE_WORD.search(right):
            cand = right
        cand = cand.strip(" -—|·,")
        if _plausible_company(cand):
            return cand
    return ''


def _extract_company(title: str, link: str, hint: str = '') -> str:
    """Best-effort company name from a job-post title, ATS URL slug, or the result's own field.

    Returns '' when nothing names a real company — the caller then skips the job ("skipped: no
    company") instead of pushing a deal cto-aipa will refuse.

    2026-10-06 ORDER: the "Role at Company" title match still runs first and is unchanged for every
    title it already resolved. The company is part of the seen-hash and of the HubSpot deal name, so
    re-deriving a name that works today would re-surface those jobs as "new" deals under a second
    name. Only a generic or Google-truncated ("Modern ...") match now falls through to the URL.
    """
    t = title or ''
    truncated = ''
    # "Role at Company • Location" / "Role at Company"
    m = re.search(r'\b(?:at|@)\s+([A-Z0-9][\w&.\-’\' ]{1,40})', t)
    if m:
        c = re.split(r'[•|\-—]', m.group(1))[0].strip(" -—|·")
        if c.endswith('...'):
            truncated = c.rstrip('. ')
        elif not _is_generic_company(c):
            return c
    # ATS URL slug: job-boards.greenhouse.io/<company>/..., jobs.lever.co/<company>/...,
    # <company>.lever.co, jobs.ashbyhq.com/<company>, wellfound.com/company/<company>
    c = _company_from_url(link)
    if c:
        return c
    # A company field on the Bright Data result itself, when the parser supplies one.
    if isinstance(hint, str) and hint.strip() and not _is_generic_company(hint):
        return hint.strip()
    if truncated and not _is_generic_company(truncated):
        return truncated
    return _company_from_title(t)


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
        data = _bd_search(query, url)
        if data is None:
            return []
        organic = data.get('organic') or data.get('organic_results') or []
        jobs = []
        for it in organic:
            title = (it.get('title') or '').strip()
            link  = (it.get('link') or it.get('url') or '').strip()
            snippet = (it.get('description') or it.get('snippet') or '').strip()
            if not title or not link:
                continue
            # 2026-10-06: a company field on the result, if Bright Data's parser ever supplies one.
            hint = it.get('company') or it.get('company_name') or ''
            jobs.append({
                'title':         title,
                'company_name':  _extract_company(title, link, hint if isinstance(hint, str) else ''),
                'location':      '',
                'description':   snippet,
                'related_links': [{'link': link}],
            })
        return jobs
    except Exception as e:
        log.warning(f'BrightData error ({query}): {e}')
        return []


# 2026-10-06 — ONE retry for Bright Data's transient failures, the way cto-aipa already does it
# (src/brightdata-enrich.ts, "intermittently answers 200 with an EMPTY body under load"). 94 of the
# 270 paid searches in the 15 runs since 29 Sep failed and became "→ 0 results": 74 were a 2xx with
# an empty/non-JSON body ("Expecting value: line 1 column 1"), 20 a read timeout. Those two are
# retried once after a short pause. An HTTP error status is NOT retried (unchanged behaviour).
BD_RETRY_SLEEP_S = 2
BD_COOLDOWN_S = 16   # Bright Data's own "recently failed … minimum of 15 seconds" answer


def _bd_post(url: str):
    return requests.post(
        BD_API,
        json={'zone': BRIGHTDATA_ZONE, 'url': url, 'format': 'raw'},
        headers={'Authorization': 'Bearer ' + BRIGHTDATA_API_TOKEN},
        timeout=45,
    )


def _bd_search(query: str, url: str):
    """Parsed Bright Data JSON (dict), or None after logging why. Retries once (see above)."""
    for attempt in (1, 2):
        wait = BD_RETRY_SLEEP_S
        try:
            resp = _bd_post(url)
        except requests.exceptions.Timeout as e:
            why = f'read timeout ({e})'
        else:
            if not resp.ok:
                log.warning(f'BrightData error ({query}): {resp.status_code} {resp.text[:120]}')
                return None
            text = resp.text or ''
            try:
                data = json.loads(text) if text.strip() else None
            except ValueError:
                data = None
            if isinstance(data, dict):
                if attempt == 2:
                    log.info(f'BrightData retry OK ({query}): {len(text)} bytes')
                return data
            why = 'empty body' if not text.strip() else f'non-JSON body ({len(text)} bytes: {text[:80]!r})'
            if re.search(r'recently failed|minimum of 15 seconds', text, re.I):
                wait = BD_COOLDOWN_S
        if attempt == 1:
            log.warning(f'BrightData {why} ({query}) — retrying once in {wait}s')
            time.sleep(wait)
        else:
            log.warning(f'BrightData error ({query}): {why} — retry failed too')
    return None


def push_crm_event(payload: dict) -> tuple:
    """(HTTP status, parsed JSON answer). Status 0 = no answer (not configured / network / timeout).

    2026-10-06: it returned a bare bool and the caller threw even that away, so "I Act TODAY" was
    logged before cto-aipa answered — 26 such lines since 29 Sep produced 2 real deals (12 were
    refused for a blank company, 12 only added a note to an existing deal). The answer is now read.
    Timeout 15s → 45s: cto-aipa drafts a paid cover letter BEFORE it answers, and a client that hangs
    up first cannot know what happened.
    """
    if not OUTREACH_SECRET:
        log.warning('OUTREACH_SECRET not set — skipping CRM push')
        return 0, {'error': 'OUTREACH_SECRET not set'}
    try:
        r = requests.post(
            OUTREACH_URL + '/api/crm-event',
            json=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': 'Bearer ' + OUTREACH_SECRET,
            },
            timeout=45,
        )
    except Exception as e:
        log.warning(f'CRM push error: {e}')
        return 0, {'error': str(e)[:200]}
    try:
        data = r.json()
    except ValueError:
        data = None
    if not isinstance(data, dict):
        data = {'_raw': (r.text or '')[:200]}
    return r.status_code, data


def _crm_outcome(status: int, data: dict) -> dict:
    """What cto-aipa's /api/crm-event answer means for this job. Added 2026-10-06.

    kind: 'new'       — ok:true, a deal id, and not reported as a duplicate (the only "I Act TODAY")
          'duplicate' — a deal with this name already exists; `stage`, `decided` say where it sits
          'rejected'  — HTTP status not 2xx; `msg` is "HTTP <code>: <message>"
          'unknown'   — no answer, or a 2xx that names no deal (hubspot:null, no ok:true, no deal id)
    The duplicate / decided / stage fields come with the parallel cto-aipa change; an older server
    omits them, and then a 2xx carrying ok:true and hubspot.dealId counts as 'new', as before.

    2026-10-06 review: a bare 2xx is NOT proof of a deal. cto-aipa's createDeal returns null when
    HubSpot refuses the create, pushHiringDealToHubSpot then reports {dealId: null, duplicate: false},
    and /api/crm-event still answers 200 ok:true — so "new" now requires the deal id. A proxy's HTML
    page or an empty body on a 2xx is 'unknown' for the same reason.
    """
    data = data if isinstance(data, dict) else {}
    if not status:
        return {'kind': 'unknown', 'msg': str(data.get('error') or 'no answer')}
    if not 200 <= status < 300:
        msg = data.get('error') or data.get('message') or data.get('_raw') or ''
        return {'kind': 'rejected', 'msg': f'HTTP {status}: {str(msg)[:200]}'}
    hs = data.get('hubspot') if isinstance(data.get('hubspot'), dict) else {}
    if data.get('duplicate', hs.get('duplicate')) is True:
        return {'kind': 'duplicate',
                'stage': data.get('stage') or hs.get('stage') or 'unknown',
                'decided': data.get('decided', hs.get('decided')) is True,
                'dealId': data.get('dealId') or hs.get('dealId') or ''}
    if 'hubspot' in data and data.get('hubspot') is None:
        return {'kind': 'unknown', 'msg': 'cto-aipa answered but HubSpot wrote no deal'}
    deal = data.get('dealId') or hs.get('dealId')
    if data.get('ok') is not True or not deal:
        return {'kind': 'unknown', 'msg': f"HTTP {status} but no deal id ({str(data.get('_raw') or data)[:120]})"}
    return {'kind': 'new', 'dealId': deal}


# iron_clad_fit now lives in the shared src/core/fit_gate.py (single source of truth,
# also used by the LangGraph submit path in nodes.py). Re-exported for callers/tests.
# NOTE: serpapi-jobs runs under SYSTEM python (no pydantic / src.core deps), so a plain
# `from src.core.fit_gate import ...` crashes via src/core/__init__.py → config → pydantic.
# fit_gate.py is stdlib-free, so on that path we load it directly by file (bypassing the
# src.core package __init__). In the venv (bot, submit path) the normal import just works.
try:
    from src.core.fit_gate import iron_clad_fit, title_on_lane  # noqa: E402,F401
except Exception:
    import importlib.util as _ilu
    from pathlib import Path as _P
    _spec = _ilu.spec_from_file_location("fit_gate", _P(__file__).parents[1] / "core" / "fit_gate.py")
    _fg = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_fg)  # type: ignore[union-attr]
    iron_clad_fit = _fg.iron_clad_fit  # noqa: F401
    title_on_lane = _fg.title_on_lane  # noqa: F401

# The same posting reader the LangGraph path uses (nodes.py → enrich_with_state). Optional:
# without it this door gates on the search snippet, exactly as before.
try:
    from src.scrapers.job_enricher import enrich_with_state as _enrich  # noqa: E402
except Exception:
    _enrich = None


def _read_full_posting(title: str, job_url: str, desc_full: str):
    """(text, closed) — the real posting instead of Google's ~180-char snippet.

    Added 2026-09-29. Every in-lane job this door parked 27-29 Sep was judged on a snippet with no
    location, so it failed "remote" and "LATAM" for lack of words, not for lack of fit. Reuses
    enrich_with_state, so its guards come along unchanged: single-posting URLs only, never trades
    down, board/search pages refused, and a page that says it is closed is reported as closed.
    Only for on-lane titles — the off-lane firehose (77 of 98 that week) costs no fetch. Any
    failure returns the snippet unchanged: the gate then decides exactly as it did before.
    """
    if _enrich is None or not job_url or len(desc_full) >= 1500 or not title_on_lane(title):
        return desc_full, False
    try:
        return _enrich(job_url, desc_full)
    except Exception as e:
        log.debug(f'  posting not read ({e}); gating on the snippet')
        return desc_full, False

# Salary floor (added 2026-07-30). salary_gate.py is deliberately stdlib-only for the
# same reason fit_gate.py is: this process runs under SYSTEM python3 with no pydantic.
try:
    from src.core.salary_gate import salary_verdict as _salary_verdict  # noqa: E402,F401
except Exception:
    try:
        import importlib.util as _ilu2
        from pathlib import Path as _P2
        _spec2 = _ilu2.spec_from_file_location(
            "salary_gate", _P2(__file__).parents[1] / "core" / "salary_gate.py")
        _sg = _ilu2.module_from_spec(_spec2)
        _spec2.loader.exec_module(_sg)  # type: ignore[union-attr]
        _salary_verdict = _sg.salary_verdict  # noqa: F401
    except Exception:
        def _salary_verdict(*_a, **_k):          # pay simply not checked
            return "unknown", None, "salary_gate unavailable"


def ingest_once() -> None:
    seen = load_seen()
    new_jobs = 0
    client_prospects = 0

    # Retargeted: Remotive (region-tagged remote board) FIRST, then the legacy
    # Google-Jobs feed. Both flow through the same gate + iron_clad_fit, so the
    # well changed without touching the routing.
    # Remotive is now owned by the BOT's JobMonitor (_search_remotive) so it also
    # surfaces to Telegram (Mode A). Path C keeps only the Google-Jobs feed here, to
    # avoid creating duplicate HubSpot cards for the same Remotive job.
    sources = [('Google Jobs', q, fetch_google_jobs) for q in JOBS_QUERIES]
    for label, query, fetch_fn in sources:
        log.info(f'Querying {label}: {query!r}')
        results = fetch_fn(query)
        log.info(f'  → {len(results)} results')

        for job in results:
            jid = job_id(job)
            if jid in seen:
                mark_seen(seen, jid)   # 2026-10-06: still live in Google → keep it at the newest end
                continue
            mark_seen(seen, jid)
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
            # 2026-09-29: "desc_full" was Google's snippet for most results — read the posting first.
            _before = len(desc_full)
            desc_full, _closed = _read_full_posting(title, job_url, desc_full)
            if _closed:
                log.info(f'  skipped (posting closed): {title} @ {company}')
                continue
            if len(desc_full) > _before:
                desc = desc_full[:800]   # HubSpot keeps the real text, not the snippet
                log.info(f'  read full posting ({_before} → {len(desc_full)} chars): {title} @ {company}')
            fit = iron_clad_fit(title, location, desc_full)   # gate on FULL desc (keywords can sit past 800 chars)

            # ── SALARY FLOOR (added 2026-07-30) — REJECT-ONLY ──
            # Park anything that STATES pay below Elena's $3,000/mo floor. A posting
            # with no stated salary is untouched (verdict "unknown" never parks), so
            # this cannot shrink the actionable view on its own.
            if fit:
                try:
                    _v, _m, _ev = _salary_verdict(title, desc_full)
                    if _v == 'below_floor':
                        fit = False
                        log.info(f'  parked (pay ~${_m:,.0f}/mo below floor, {_ev}): {title} @ {company}')
                except Exception as _se:
                    log.debug(f'  salary gate unavailable ({_se}); pay not checked')

            # ── HER LESSONS + THE JUDGE ON THIS DOOR TOO (added 2026-09-27) ──
            # Until today a gate-PASS went straight to "I Act TODAY": the judge — the only
            # component that reads Elena's rejections — was consulted here only to RESCUE a
            # gate-NO (borderline, below), never to veto a gate-YES. This path created most
            # of what she then rejected (Addi, Byldd, Avenga…). Now a gate-pass must also
            # clear the rules she taught (src/core/learned_rules.py) and the judge.
            # Both fail OPEN: no rules file / judge unavailable = today's behaviour exactly.
            veto_note = ''
            if fit:
                try:
                    from src.core.learned_rules import learned_veto
                    _lv, _lwhy = learned_veto(title, company, f'{location}\n{desc_full}')
                    if _lv:
                        fit, veto_note = False, _lwhy
                        log.info(f'  parked by {_lwhy}: {title} @ {company}')
                except Exception as _le:
                    log.debug(f'  learned rules unavailable ({_le})')
            if fit:
                try:
                    from src.core.llm_judge import judge_fit
                    _jok, _jwhy = judge_fit(title, company, location, desc_full)
                    if not _jok and not str(_jwhy).startswith('JUDGE UNAVAILABLE'):
                        fit, veto_note = False, f'JUDGE VETO: {_jwhy}'
                        log.info(f'  parked by judge VETO ({_jwhy}): {title} @ {company}')
                except Exception as _je:
                    log.debug(f'  judge unavailable ({_je}); gate decision stands')

            hiring_stage = 'applied' if fit else 'lead_parked'
            # 2026-10-06: the "I Act TODAY" line moved below the push — it is printed only when
            # cto-aipa accepted the job as a NEW deal (see _crm_outcome).
            if not fit and not veto_note:
                log.info(f'  parked (not iron-clad fit or below pay floor): {title} @ {company}')

            # ── Additive: a parked job the JUDGE would take is announced, not buried.
            # Reads `fit`; never reassigns it. See _borderline_check above for why.
            # Not for a job her lessons or the judge just vetoed — asking again would only
            # produce the contradiction the borderline alert exists to report.
            borderline, borderline_why = (False, '')
            if not fit and not veto_note:
                borderline, borderline_why = _borderline_check(title, company, location, desc_full)
                if borderline:
                    log.info(f'  BORDERLINE (gate NO / judge YES) -> alerting: {title} @ {company}')
                    _borderline_alert(title, company, location, job_url, borderline_why)

            # 2026-10-06 — no company, no CRM push (hiring OR client). cto-aipa answers a blank company
            # with HTTP 400: 12 of the 26 "I Act TODAY" lines logged 29 Sep – 6 Oct were such jobs
            # (DEUNA, Airtm…), and the log claimed a deal that never existed. The verdict and the URL
            # are logged so a parser gap stays visible.
            # Placed AFTER the BORDERLINE alert on purpose (review, 6 Oct): that Telegram alert needs no
            # company and was the only way such a job ever reached Elena — 17 of the 32 BORDERLINE lines
            # logged 29 Sep – 6 Oct had a blank company. So the alert path is exactly as before, and so
            # is the spend (posting read + judge); only the pushes cto-aipa would refuse are skipped
            # (record_judged_posting below already returns early on a blank company).
            if not (company or '').strip():
                log.info(f"  {'IRON-CLAD FIT + judge OK' if fit else 'parked'}, skipped: no company: "
                         f"{title} ({job_url})")
                continue

            # Evidence memory: the text this decision was made on, keyed by the URL the deal carries.
            record_judged_posting(title, company, job_url, location, desc_full, 'serpapi_jobs')

            # 1. Hiring pipeline (VJH track)
            _status, _answer = push_crm_event({
                'source':   'serpapi_jobs',
                'type':     'application',
                'pipeline': 'hiring',
                'sourcePrefix': 'HIRING-VJH-SERP-LEAD',
                'jobTitle': title,
                'company':  company,
                # Borderline jobs carry their split verdict into the note so the
                # decision is reconstructable in HubSpot months later, and so the
                # deal is findable by searching "BORDERLINE". Non-borderline jobs
                # get the exact same string as before.
                'notes': (
                    # A vetoed job says WHICH lesson or judge reason parked it, so Elena can
                    # see — and correct, by moving the deal — every decision made for her.
                    (f'\U0001f6ab [{veto_note[:280]}]\nParked, not shown in I Act TODAY. '
                     f'If this is wrong, move the deal: VJH learns from that too.\n\n' if veto_note else '')
                    + (f'\U0001f7e1 [BORDERLINE] iron-clad gate said NOT a fit '
                     f'(location roster / eligibility) but the AI judge said FIT: '
                     f'{borderline_why[:300]}\nParked deliberately \u2014 Elena decides. '
                     f'Telegram alert sent.\n\n' if borderline else '')
                    + '\u26a0\ufe0f MANUAL APPLY REQUIRED \u2014 VJH SerpAPI found this job. Click the job URL + apply manually. No cover letter pre-generated for SerpAPI path.'
                ),
                'jobUrl':   job_url,
                'context':  f'[Google Jobs] {title} @ {company} — {location}\n{desc}',
                'stage':    hiring_stage,
            })
            # 2026-10-06 — acknowledgement is not completion: log what cto-aipa actually did.
            # "IRON-CLAD FIT + judge OK" still opens every gate-pass line (the yield count greps it);
            # "-> I Act TODAY" appears only for a NEW deal.
            crm = _crm_outcome(_status, _answer)
            tag = 'IRON-CLAD FIT + judge OK' if fit else 'parked'
            if crm['kind'] == 'new':
                if fit:
                    log.info(f'  IRON-CLAD FIT + judge OK -> I Act TODAY: {title} @ {company}')
            elif crm['kind'] == 'duplicate':
                log.info(f"  {tag}, already in CRM (stage {crm['stage']}) — not new"
                         f"{' (already decided)' if crm['decided'] else ''}: {title} @ {company}")
            elif crm['kind'] == 'rejected':
                log.warning(f"  {tag}, CRM REJECTED ({crm['msg']}): {title} @ {company}")
            else:
                log.warning(f"  {tag}, CRM outcome UNKNOWN ({crm['msg']}) — check HubSpot: {title} @ {company}")

            # 2. Client prospect — company hiring a CTO/AI lead = needs fractional help now
            # 2026-10-06: only for a job that passed every gate AND became a NEW hiring deal, with a
            # company. It used to fire for parked jobs, blank companies and re-seen duplicates too
            # (the "Hiring manager @ — outreach" junk). A real fractional/CTO-intent job that passes
            # still fires exactly as before, with the same urgency rule (now whole-word).
            title_lower = title.lower()
            is_client_signal = _client_intent(title)
            if is_client_signal and fit and company and crm['kind'] == 'new':
                client_prospects += 1
                _c_status, _c_answer = push_crm_event({
                    'source':   'serpapi_jobs',
                    'type':     'prospect',
                    'pipeline': 'client',
                    'name':     f'Hiring manager @ {company}',
                    'company':  company,
                    'context':  f'[SerpAPI/GoogleJobs] Company posted "{title}" — actively scaling AI/tech leadership. Prime fractional CTO prospect.\nJob: {job_url}\n{desc[:400]}',
                    'urgency':  5 if re.search(r'\bcto\b', title_lower) or 'fractional' in title_lower else 4,
                })
                _c = _crm_outcome(_c_status, _c_answer)
                if _c['kind'] in ('rejected', 'unknown'):
                    log.warning(f"  client prospect not confirmed ({_c['msg']}): {company}")

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
