"""
Shared iron-clad fit gate — the single source of truth for "is this role a fit
for Elena?" used by BOTH the SerpAPI/Remotive ingest (serpapi_jobs_ingest.py) and
the LangGraph submit path (nodes.py).

A role only reaches Elena's actionable "I Act TODAY" if it is:
  fully remote  AND  LATAM/Panama-open  AND  AI-augmented-builder shaped
  AND NOT US-only  AND NOT heavy hand-coding (CS-degree / years-of-SWE / leetcode).

Bias is intentionally strict: better to park/drop a good one than promote a bad one.
"""

LATAM_OK = ('worldwide', 'anywhere', 'global', 'americas', 'latam',
            'latin america', 'central america')
COUNTRY_LOCK = ('brazil', 'usa', 'united states', 'canada', 'germany',
                'united kingdom', 'india', 'australia', 'israel', 'philippines',
                'mexico', 'argentina', 'europe', 'emea', 'apac')


def iron_clad_fit(title: str, location: str, desc: str) -> bool:
    title_l, loc, desc_l = (title or '').lower(), (location or '').lower(), (desc or '').lower()
    blob = f"{title_l} {loc} {desc_l}"

    remote = any(k in blob for k in (
        'remote', 'work from anywhere', 'work from home', 'distributed team', 'fully remote'))

    # LATAM/Panama eligibility: TRUST the structured region tag when present. A
    # specific non-Panama country tag (Brazil-only, USA-only) is authoritative and
    # parks the job even if the description name-drops "Americas". Only fall back to
    # description keywords when there is no clean region tag (e.g. Google Jobs).
    if any(t in loc for t in LATAM_OK):
        latam = True
    elif any(t in loc for t in COUNTRY_LOCK):
        latam = False
    else:
        latam = any(t in desc_l for t in LATAM_OK + ('any time zone', 'any timezone', 'international'))

    us_only = any(k in blob for k in (
        'us only', 'u.s. only', 'united states only', 'us-based only', 'usa only',
        'must be based in the us', 'must be located in the united states',
        'authorized to work in the us', 'eligible to work in the us',
        'us-remote', 'us remote', 'remote - united states', 'remote, united states',
        'remote (us', 'remote, us'))

    ai_aug = any(k in blob for k in (
        'no-code', 'no code', 'low-code', 'low code', 'prompt', 'ai-augment', 'ai augment',
        'ai tools', 'ai agent', 'automation', 'claude', 'cursor', 'copilot', 'gpt', 'llm',
        'non-technical',
        # AI-role titles ARE AI-augmented work — bare "AI Engineer" matched NONE of the above
        # and failed iron-clad despite being Elena's #1 target. (Same class of bug as the gate.)
        'ai engineer', 'ai developer', 'ai architect', 'ai/ml', 'ai solution', 'ai system',
        'ai lead', 'ai specialist', 'ai product', 'ai ops', 'machine learning', 'ml engineer',
        'artificial intelligence', 'generative ai', 'genai', 'agentic', 'rag', 'nlp', 'deep learning'))

    # Strip NEGATED mentions first, so "no CS degree required" / "no leetcode"
    # don't falsely trip the heavy-coding exclusion — those are a GOOD sign.
    heavy_blob = blob
    for neg in ('no cs degree', 'no computer science degree', 'without a cs degree',
                'without cs degree', 'no degree required', 'degree not required',
                'no leetcode', 'without leetcode', 'no coding required',
                'no prior coding', 'no engineering degree'):
        heavy_blob = heavy_blob.replace(neg, ' ')
    heavy = any(k in heavy_blob for k in (
        'computer science degree', 'cs degree', 'leetcode', 'system design interview',
        'strong coding', 'strong programming', 'algorithms and data structures',
        'years of software engineering', 'years of professional software',
        'years writing production code',
        # title-level heavy-coding roles — not AI-augmented-builder shaped
        'staff engineer', 'staff product engineer', 'staff software', 'principal engineer',
        'senior software engineer', 'backend engineer', 'frontend engineer',
        'full stack', 'full-stack', 'fullstack'))

    return remote and latam and ai_aug and not us_only and not heavy
