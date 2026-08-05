"""
Shared iron-clad fit gate — the single source of truth for "is this role a fit
for Elena?" used by BOTH the SerpAPI/Remotive ingest (serpapi_jobs_ingest.py) and
the LangGraph submit path (nodes.py).

A role only reaches Elena's actionable "I Act TODAY" if it is:
  fully remote  AND  LATAM/Panama-open  AND  AI-augmented-builder shaped
  AND NOT US-only  AND NOT heavy hand-coding (CS-degree / years-of-SWE / leetcode).

Bias is intentionally strict: better to park/drop a good one than promote a bad one.
"""

import os
import re

# ── RESIDENCY ROSTER BEATS THE REGION LABEL (added 2026-07-31) ────────────────
# Elena applied to "AI-Native Agentic Operations Specialist @ Singular Agency"
# and Torre's pre-screening rejected her at step 2 of 3:
#   "This position requires you to be a resident of any of these countries:
#    Guatemala, México, República Dominicana, Salvador, Nicaragua, Puerto Rico,
#    Costa Rica, Honduras, Venezuela, Bolivia, Argentina, Chile, Colombia,
#    Ecuador, Paraguay, Uruguay, Perú, Aruba"
# PANAMA IS NOT ON IT. VJH had that roster all along — it was sitting inside the
# location string it stored — but the string reads
#   "Remote — Worldwide / LATAM (Colombia, Ecuador, Puerto Rico, ...)"
# and the gate matched the "Worldwide / LATAM" LABEL while ignoring the
# parenthesised list. The label is marketing; the roster is the rule. When a
# posting enumerates the countries it hires from, Elena's must be among them.
HOME_COUNTRY = os.getenv("VJH_HOME_COUNTRY", "panama").strip().lower()
_COUNTRY_ROSTER = re.compile(r"\(([^)]{6,})\)")
# If the roster itself says "anywhere", it is a region label, not a restriction.
_OPEN_REGION_TOKENS = ('worldwide', 'anywhere', 'global', 'any country',
                       'latam', 'latin america', 'americas')


# ── TITLE-ONLY LANE CHECK (added 2026-08-04) ─────────────────────────────────
# Used ONLY to decide whether an unjudgeable posting is worth Elena's own 30
# seconds. In 48h the thin-data guard discarded 107 postings and 37 were in her
# lanes — including "Forward Deployed Engineer - AI Solutions Engineering", the
# exact title she applied to elsewhere that week. Silence was the wrong answer;
# the right one is to surface it clearly marked as unverified.
# This is NOT a fit gate. It never promotes anything on its own.
_ON_LANE_TITLE = re.compile(
    r"\bai\b.*\b(engineer|developer|architect|specialist|builder|lead|consultant)|"
    r"\b(engineer|developer|architect|specialist|builder|lead)\b.*\bai\b|"
    r"agentic|ai agent|llm|generative ai|genai|"
    r"automation (engineer|specialist|architect|consultant)|"
    r"forward.deployed|solutions (engineer|architect|consultant)|"
    r"\bn8n\b|make\.com|zapier|workflow automation|prompt engineer|"
    r"\b(geo|aeo)\b|technical seo",
    re.IGNORECASE,
)
_OFF_LANE_TITLE = re.compile(
    r"machine learning (engineer|scientist|researcher)|\bml (engineer|scientist)\b|"
    r"research (engineer|scientist)|researcher|data (scientist|analyst)|"
    r"qa automation|test automation|sdet|quality assurance|"
    r"it automation|infrastructure automation|industrial automation|rpa|"
    r"marketing automation|sales automation|"
    r"full[- ]?stack|backend engineer|front[- ]?end engineer|"
    r"senior software engineer|staff (engineer|software)|principal engineer|"
    r"embedded|firmware|business analyst|account executive|recruiter",
    re.IGNORECASE,
)


def title_on_lane(title: str) -> bool:
    """True if the TITLE alone puts this role in one of Elena's three lanes."""
    t = title or ""
    if _OFF_LANE_TITLE.search(t):
        return False
    return bool(_ON_LANE_TITLE.search(t))


# ── RESIDENCY STATED IN PROSE, NOT IN THE LOCATION FIELD (added 2026-08-04) ──
# "Product Execution Partner @ Force of Nature" reached "I Act TODAY" with the
# location field reading "Remote — Worldwide / LATAM" — which is what its source
# actually publishes. The real rule was a sentence in the body:
#     "Location: Remote — Uruguay, Colombia, Peru, or Paraguay preferred."
# Panama is not on it. roster_excludes_home() could not fire because there was no
# roster in the location field to read. Same lesson as Singular Agency, one layer
# deeper: the SPECIFIC statement beats the general label, wherever it is written.
#
# Deliberately anchored to residency language. A description that merely mentions
# countries as MARKETS — "retail partners across the US, GCC and UK" — is not a
# hiring restriction and must never be read as one.
_RESIDENCY_ANCHOR = re.compile(
    r"(must be a resident|residents? of|must reside|candidates? must reside|"
    r"eligible to work in|open to candidates?|hiring (?:only )?in|"
    r"location:\s*remote|based in|located in|preferred in|"
    r"candidates? (?:in|from)|physically (?:perform|located|reside))",
    re.IGNORECASE,
)
# Countries seen in these postings. Not exhaustive by design — it only has to be
# good enough to recognise "this sentence enumerates places".
_COUNTRY_WORDS = (
    "panama", "uruguay", "colombia", "peru", "paraguay", "chile", "bolivia",
    "ecuador", "venezuela", "guatemala", "honduras", "nicaragua", "salvador",
    "costa rica", "dominican", "aruba", "mexico", "brazil", "argentina",
    "united states", "usa", "canada", "ukraine", "poland", "portugal", "spain",
    "germany", "france", "india", "philippines", "pakistan", "nigeria", "kenya",
    "south africa", "australia", "israel", "united kingdom", "ireland",
)
# If any of these appear in the same sentence, the enumeration is a REGION that
# includes Panama, not a restriction that excludes her.
_REGION_COVERS_HOME = (
    "worldwide", "anywhere", "global", "any country", "latam", "latin america",
    "central america", "americas", "anywhere in the world",
)


def residency_excludes_home(text: str) -> bool:
    """
    True when the BODY states a residency requirement that names countries and
    Elena's is not among them.
    """
    blob = _deaccent((text or "").lower())
    for m in _RESIDENCY_ANCHOR.finditer(blob):
        window = blob[m.start():m.start() + 220]
        if any(r in window for r in _REGION_COVERS_HOME):
            continue                      # region includes Panama → not a bar
        if _deaccent(HOME_COUNTRY) in window:
            continue                      # explicitly eligible
        named = sum(1 for c in _COUNTRY_WORDS if c in window)
        if named >= 2:                    # an actual roster, not a passing mention
            return True
    return False


def _deaccent(s: str) -> str:
    """Fold diacritics so 'Panamá' == 'panama' and 'México' == 'mexico'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def roster_excludes_home(location: str) -> bool:
    """
    True when the location enumerates eligible countries and HOME_COUNTRY is
    absent — i.e. Elena is not allowed to hold this job however "LATAM" it looks.

    Conservative: only a comma-separated list of two or more entries counts as a
    roster, so "Berlin (Remote)" and "Remote (anywhere)" are never treated as one.
    """
    m = _COUNTRY_ROSTER.search(location or "")
    if not m:
        return False
    # Torre writes rosters in Spanish — "México", "Perú", "Panamá". Comparing
    # raw would miss Elena's OWN country on any accented listing and reject a job
    # she is in fact eligible for, so fold diacritics on both sides.
    inner = _deaccent(m.group(1).lower())
    if len([x for x in inner.split(",") if x.strip()]) < 2:
        return False
    if any(tok in inner for tok in _OPEN_REGION_TOKENS):
        return False
    return _deaccent(HOME_COUNTRY) not in inner


LATAM_OK = ('worldwide', 'anywhere', 'global', 'americas', 'latam',
            'latin america', 'central america')
COUNTRY_LOCK = ('brazil', 'usa', 'united states', 'canada', 'germany',
                'united kingdom', 'india', 'australia', 'israel', 'philippines',
                'mexico', 'argentina', 'europe', 'emea', 'apac',
                # 2026-07-30: three jobs reached Elena's "I Act TODAY" with
                # locations she cannot hold — "Remote — Ukraine" (ELVTR),
                # "Remote-UK&I" (Remote.com) and "Berlin (Remote)" (Moss).
                # "united kingdom" never matched "UK&I", and city names were not
                # checked at all, so the LATAM fallback read the description and
                # let them through. Countries + the major hiring cities that
                # imply a country lock:
                # (substring matching — no regex here, so no bare "uk" token:
                #  it would match "Ukraine" and unrelated words alike)
                'ukraine', 'uk&i', 'uk & i', 'uk and ireland', 'ireland',
                'poland', 'portugal', 'spain', 'france', 'netherlands', 'romania',
                'serbia', 'turkey', 'egypt', 'nigeria', 'kenya', 'south africa',
                'pakistan', 'bangladesh', 'indonesia', 'vietnam', 'singapore',
                'japan', 'china', 'korea', 'new zealand',
                'berlin', 'london', 'dublin', 'amsterdam', 'paris', 'madrid',
                'barcelona', 'lisbon', 'warsaw', 'kyiv', 'kiev', 'tel aviv',
                'bengaluru', 'bangalore', 'gurugram', 'mumbai', 'manila',
                'toronto', 'vancouver', 'sydney', 'melbourne', 'tokyo')

# Panama is UTC-5 year-round, overlapping US Eastern (UTC-5 EST/UTC-4 EDT) and
# Central (UTC-6 CST/UTC-5 CDT) time. A job stating these hours without ever
# saying "LATAM"/"worldwide" was invisible to the LATAM_OK fallback below.
# Word-boundary regex only — bare substrings like "et"/"ct" match too many
# unrelated words ("market", "internet", "select") if checked without \b.
_TZ_COMPATIBLE_PATTERNS = tuple(re.compile(p) for p in (
    r'eastern time', r'eastern standard time', r'eastern daylight time',
    r'central time', r'central standard time', r'central daylight time',
    r'utc-5', r'utc-4', r'gmt-5', r'gmt-4',
    r'\bet\b', r'\bct\b', r'\best\b', r'\bedt\b', r'\bcst\b', r'\bcdt\b',
))

# GEO/AEO/Tech-SEO is one of Elena's explicit target lanes (July 9 2026) — it IS
# AI-augmented work (AI-crawler visibility, generative/answer-engine optimization)
# but shares no keyword with the ai_aug tuple below. \b-bounded so "seoul" /
# "archaeology" can't substring-match.
_SEO_AEO_PATTERNS = tuple(re.compile(p) for p in (
    r'\bseo\b', r'\baeo\b', r'\bgeo\b',
    r'search engine optimization', r'answer engine optimization',
    r'generative engine optimization', r'search everywhere optimization',
))


def iron_clad_fit(title: str, location: str, desc: str) -> bool:
    title_l, loc, desc_l = (title or '').lower(), (location or '').lower(), (desc or '').lower()
    blob = f"{title_l} {loc} {desc_l}"

    remote = any(k in blob for k in (
        'remote', 'work from anywhere', 'work from home', 'distributed team', 'fully remote'))

    # LATAM/Panama eligibility: TRUST the structured region tag when present. A
    # specific non-Panama country tag (Brazil-only, USA-only) is authoritative and
    # parks the job even if the description name-drops "Americas". Only fall back to
    # description keywords when there is no clean region tag (e.g. Google Jobs).
    # An explicit residency roster OUTRANKS the region label in front of it —
    # "Worldwide / LATAM (Colombia, Ecuador, ...)" means those countries, not LATAM.
    # A residency roster — in the location field OR in the body — outranks any
    # region label. "Remote — Worldwide / LATAM" is what the board publishes;
    # "Uruguay, Colombia, Peru, or Paraguay" is what the employer means.
    if roster_excludes_home(loc) or residency_excludes_home(desc_l):
        latam = False
    elif any(t in loc for t in LATAM_OK):
        latam = True
    elif any(t in loc for t in COUNTRY_LOCK):
        latam = False
    else:
        # The DESCRIPTION fallback must be stricter than the LOCATION test.
        # "Global" in a location field means the hiring region. In prose it almost
        # always describes the EMPLOYER: StatusNeo's blurb — "a global digital
        # transformation and product engineering company" — matched bare 'global'
        # and its India-centric AI Engineer role was read as LATAM-open (2026-07-31).
        # Same failure class as bare "agents": a word about the company scoring as
        # a fact about the job. Here the phrase must be about WHERE YOU MAY LIVE.
        latam = (
            any(t in desc_l for t in (
                'latam', 'latin america', 'central america', 'south america',
                'work from anywhere', 'from anywhere in the world', 'anywhere in the world',
                'globally distributed', 'hire globally', 'hiring globally',
                'remote worldwide', 'worldwide remote', 'fully remote worldwide',
                'any country', 'any time zone', 'any timezone', 'location independent',
                'open to candidates anywhere', 'candidates from any',
            ))
            or any(p.search(blob) for p in _TZ_COMPATIBLE_PATTERNS)
        )

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
        'artificial intelligence', 'generative ai', 'genai', 'agentic', 'rag', 'nlp', 'deep learning',
        'product builder')) or any(p.search(blob) for p in _SEO_AEO_PATTERNS)

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
        # 2026-07-31: the StatusNeo posting demanded "Bachelor's or Master's degree
        # in Computer Science" and "5+ years of software engineering experience" —
        # neither phrasing matched. The list only knew the words in the OTHER order.
        'degree in computer science', 'degree in engineering', 'bachelor’s or master',
        "bachelor's or master", 'bachelor degree', "bachelor's degree", 'bachelors degree',
        "master's degree", 'masters degree', 'b.tech', 'b.e./b.tech',
        'years of software engineering experience', 'years of professional experience in software',
        'years of hands-on software', 'years of backend', 'years of full-stack',
        'strong coding', 'strong programming', 'algorithms and data structures',
        'years of software engineering', 'years of professional software',
        'years writing production code',
        # title-level heavy-coding roles — not AI-augmented-builder shaped
        'staff engineer', 'staff product engineer', 'staff software', 'principal engineer',
        'senior software engineer', 'backend engineer', 'frontend engineer',
        'full stack', 'full-stack', 'fullstack'))

    # ── WRONG KIND OF "AUTOMATION" (added 2026-07-30) ────────────────────────
    # Broadening the search terms to Elena's AI-automation lane also pulled in
    # QA/test automation, IT/infrastructure automation and industrial automation —
    # all of which contain "automation engineer" and none of which she wants. Real
    # leak, seen the same day: "Senior QA Automation Engineer @ Coderoad" and
    # "(1515) QA Automation Engineer" landed in HubSpot "🔥 I Act TODAY" via the
    # SerpAPI path, which has no LLM judge behind it. Title-level check only, so a
    # genuine AI-automation role that merely mentions testing is unaffected.
    title_l = (title or '').lower()
    wrong_automation = any(k in title_l for k in (
        'qa automation', 'automation qa', 'test automation', 'automation test',
        'sdet', 'quality assurance', 'quality engineer',
        'it automation', 'infrastructure automation', 'network automation',
        'industrial automation', 'plc', 'robotics automation', 'rpa developer',
        'marketing automation', 'sales automation'))

    return remote and latam and ai_aug and not us_only and not heavy and not wrong_automation
