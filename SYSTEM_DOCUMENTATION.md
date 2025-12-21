# 🤖 VIBEJOBHUNTER - COMPLETE SYSTEM DOCUMENTATION

**Last Updated:** December 21, 2025  
**Status:** ✅ FULLY OPERATIONAL  
**Deployment:** Railway (24/7)

---

## 📋 TABLE OF CONTENTS

1. [What This System Does](#1-what-this-system-does)
2. [The Autonomous Job Application Flow](#2-the-autonomous-job-application-flow)
3. [Target Roles & Platforms](#3-target-roles--platforms)
4. [Key Files & Data](#4-key-files--data)
5. [Configuration](#5-configuration)
6. [Codebase Architecture](#6-codebase-architecture)
7. [How to Modify/Extend](#7-how-to-modifyextend)

---

## 1. WHAT THIS SYSTEM DOES

VibeJobHunter is a **fully autonomous job hunting engine** that:

### ✅ Implemented & Working (December 2025)

| Feature | Status | Description |
|---------|--------|-------------|
| **ATS Job Scraping** | ✅ LIVE | Scrapes 3000+ jobs/hour from Greenhouse, Lever, Ashby, Workable |
| **Smart Job Scoring** | ✅ LIVE | AI-powered scoring (Claude) + keyword matching |
| **Auto-Application** | ✅ LIVE | Fills and submits Greenhouse forms automatically |
| **Email Verification** | ✅ LIVE | Reads verification codes from Zoho Mail IMAP |
| **Resume Selection** | ✅ LIVE | 3 resume variants, auto-selects based on role |
| **Founder Outreach** | ✅ LIVE | Finds founder contacts, generates personalized messages |
| **LinkedIn CMO** | ✅ LIVE | Daily AI-generated posts via Make.com |
| **Telegram Bot** | ✅ LIVE | Real-time notifications + interactive commands |
| **Email Service** | ✅ LIVE | Sends applications via Resend API |
| **Database Tracking** | ✅ LIVE | SQLite tracks all applications |

---

## 2. THE AUTONOMOUS JOB APPLICATION FLOW

### Every Hour, The System:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    🔄 AUTONOMOUS CYCLE (Hourly)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: JOB DISCOVERY                                                │
│ ─────────────────────                                                │
│ • Greenhouse API → 73 companies → ~2000 jobs                         │
│ • Lever API → 19 companies → ~150 jobs                               │
│ • Ashby API → 37 companies → ~900 jobs                               │
│ • Workable API → 9 companies                                         │
│ • Hacker News Who's Hiring → ~90 jobs                                │
│ • RemoteOK API → ~18 jobs                                            │
│                                                                      │
│ TOTAL: ~3000 jobs scraped per cycle                                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: CAREER GATE FILTER                                           │
│ ──────────────────────────                                           │
│ Filters out ~78% of jobs that don't match:                           │
│ • Keywords: founding, senior, staff, principal, AI, ML, platform     │
│ • Excludes: junior, intern, manager-only, non-technical              │
│ • Blocks large companies (>500 employees)                            │
│                                                                      │
│ RESULT: ~700 jobs pass the gate                                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: AI SCORING (Claude)                                          │
│ ───────────────────────────                                          │
│ Each job scored 0-100 based on:                                      │
│ • AI/ML relevance (25%)                                              │
│ • Autonomy/0→1 signals (25%)                                         │
│ • Technical depth (20%)                                              │
│ • Company stage (15%)                                                │
│ • Remote-friendliness (15%)                                          │
│                                                                      │
│ Bonuses: +4 for senior/staff roles, +3 for founding titles           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: ROUTING BY SCORE                                             │
│ ────────────────────────                                             │
│                                                                      │
│ Score ≥ 60 → AUTO-APPLY (ATS form submission)                        │
│ Score ≥ 58 → FOUNDER OUTREACH (email/LinkedIn message)               │
│ Score ≥ 55 → REVIEW QUEUE (saved for manual review)                  │
│ Score < 55 → DISCARDED                                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                              ▼
┌─────────────────────────────┐  ┌─────────────────────────────────────┐
│ AUTO-APPLY FLOW             │  │ FOUNDER OUTREACH FLOW               │
│ ─────────────────           │  │ ─────────────────────               │
│ 1. Research company (Claude)│  │ 1. Research company (Claude)        │
│ 2. Select resume variant    │  │ 2. Find founder email/LinkedIn      │
│ 3. Generate cover letter    │  │ 3. Generate personalized message    │
│ 4. Fill Greenhouse form     │  │ 4. Send via Resend or notify via TG │
│ 5. Handle email verification│  │                                     │
│ 6. Submit application       │  │                                     │
│ 7. Save to database         │  │                                     │
│ 8. Notify via Telegram      │  │                                     │
└─────────────────────────────┘  └─────────────────────────────────────┘
```

### Email Verification Flow (Greenhouse):

```
Form submitted → Greenhouse sends verification email to aipa@aideazz.xyz
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ IMAP CONNECTION TO ZOHO MAIL                                         │
│ • Server: imappro.zoho.com:993 (SSL)                                 │
│ • Checks folders: INBOX, Notification, Spam, Junk                    │
│ • Searches for: security code, verification emails                   │
│ • Extracts 8-character code from email body                          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
Code entered into form → Wait for button to enable → Submit → SUCCESS!
```

---

## 3. TARGET ROLES & PLATFORMS

### 🎯 Target Role Keywords

```python
TARGET_ROLES = [
    "Founding Engineer",
    "Senior AI Engineer", 
    "Staff AI Engineer",
    "Principal Engineer",
    "AI Product Engineer",
    "AI Solutions Architect",
    "Technical Lead - AI",
    "ML Engineer",
    "Platform Engineer",
]
```

### 🏢 Platforms Scraped

| Platform | API Type | # Companies | Jobs/Cycle |
|----------|----------|-------------|------------|
| **Greenhouse** | REST API | 73 | ~2000 |
| **Ashby** | GraphQL | 37 | ~900 |
| **Lever** | REST API | 19 | ~150 |
| **Workable** | REST API | 9 | ~0 (API issues) |
| **Hacker News** | Firebase API | - | ~90 |
| **RemoteOK** | REST API | - | ~18 |

### 🔥 Top Target Companies (from `src/scrapers/ats_scraper.py`)

**Frontier AI Labs:**
- Anthropic, OpenAI, DeepMind, xAI, Meta AI

**AI Infrastructure:**
- Databricks, Scale AI, Modal, Anyscale, Together AI, Fireworks AI

**AI Products:**
- Perplexity, Runway, Jasper, Grammarly, Cohere

**AI Robotics:**
- Figure AI, Nuro, Waymo

**Dev Tools:**
- Cursor, Vercel, Figma, Retool, Supabase, Linear

**Fintech:**
- Stripe, Ramp, Brex, Mercury

---

## 4. KEY FILES & DATA

### 📁 Core Source Files

```
src/
├── autonomous/
│   ├── orchestrator.py          # 🧠 Main brain - runs hourly cycles
│   ├── job_monitor.py           # 🔍 Fetches jobs from all sources
│   ├── auto_applicator.py       # 📝 Generates application materials
│   ├── ats_submitter.py         # 🚀 Submits to ATS (Greenhouse/Lever)
│   ├── greenhouse_email_verifier.py  # 📧 IMAP verification code reader
│   ├── company_researcher.py    # 🔬 Claude-powered company research
│   ├── founder_finder_v2.py     # 👤 Finds founder contacts
│   ├── message_generator.py     # ✍️ Generates outreach messages
│   └── email_service.py         # 📤 Sends emails via Resend
│
├── scrapers/
│   └── ats_scraper.py           # 🕷️ Greenhouse/Lever/Ashby/Workable APIs
│
├── agents/
│   └── job_matcher.py           # 🎯 AI-powered job scoring
│
├── templates/
│   ├── resume_selector.py       # 📄 Selects from 3 resume variants
│   ├── resume_founding_engineer.md
│   ├── resume_senior_ai_engineer.md
│   └── resume_ai_solutions_architect.md
│
└── notifications/
    ├── telegram_notifier.py     # 📱 Telegram notifications
    ├── telegram_bot_enhanced.py # 🤖 Interactive bot commands
    └── linkedin_cmo_v4.py       # 📣 Daily LinkedIn posting
```

### 📊 Data Files

```
autonomous_data/
├── resumes/
│   ├── founding_engineer.pdf    # Resume variant 1
│   ├── senior_ai_engineer.pdf   # Resume variant 2
│   ├── ai_solutions_architect.pdf # Resume variant 3
│   └── elena_resume.pdf         # Default resume
│
├── applications/                # Generated cover letters/materials
│   └── application_*.txt
│
├── ats_cache/                   # Cached job listings
│   └── jobs_*.json
│
└── vibejobhunter.db            # SQLite database (applications, companies)

src/data/
└── target_companies.json        # Company list (if exists)
```

### ⚙️ Configuration Files

```
.env                             # Environment variables (not in git)
.env.example                     # Template with all variables
requirements.txt                 # Python dependencies
Dockerfile                       # Railway deployment
railway.json                     # Railway config
```

---

## 5. CONFIGURATION

### 🔑 Required Environment Variables

```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...          # Claude API

# Email (for applications)
RESEND_API_KEY=re_...                 # Resend email service
FROM_EMAIL=Elena Revicheva <aipa@aideazz.xyz>

# Applicant Info
APPLICANT_FIRST_NAME=Elena
APPLICANT_LAST_NAME=Revicheva
APPLICANT_EMAIL=aipa@aideazz.xyz
APPLICANT_PHONE=+507-6166-6716
APPLICANT_LINKEDIN=https://linkedin.com/in/elenarevicheva
APPLICANT_PORTFOLIO=https://aideazz.xyz

# Zoho Mail (for reading verification codes)
ZOHO_EMAIL=aipa@aideazz.xyz
ZOHO_APP_PASSWORD=xxxxxxxxxxxx        # 12-char app-specific password

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# ATS Settings
ATS_DRY_RUN=false                     # Set to true for testing
ATS_SUBMISSION_ENABLED=true
```

### 📊 Scoring Thresholds (in `orchestrator.py`)

```python
AUTO_APPLY_THRESHOLD = 60    # Score >= 60 → auto-submit application
OUTREACH_THRESHOLD = 58      # Score >= 58 → send founder outreach
REVIEW_THRESHOLD = 55        # Score >= 55 → save for review
MAX_DAILY_APPLICATIONS = 5   # Safety cap per day
```

---

## 6. CODEBASE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTRY POINTS                                 │
├─────────────────────────────────────────────────────────────────────┤
│  web_server.py          → FastAPI server (Railway runs this)         │
│  src/main.py            → CLI for local testing                      │
│  railway-entrypoint.sh  → Docker startup script                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR LAYER                              │
│                   src/autonomous/orchestrator.py                     │
├─────────────────────────────────────────────────────────────────────┤
│  • Runs hourly autonomous cycles                                     │
│  • Coordinates all components                                        │
│  • Manages daily caps and rate limits                                │
│  • Sends Telegram notifications                                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   JOB DISCOVERY   │  │    AI SCORING     │  │   APPLICATION     │
│   job_monitor.py  │  │  job_matcher.py   │  │  auto_applicator  │
│   ats_scraper.py  │  │                   │  │  ats_submitter    │
└───────────────────┘  └───────────────────┘  └───────────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  EXTERNAL APIs    │  │    CLAUDE API     │  │  ATS PLATFORMS    │
│  • Greenhouse     │  │  (Anthropic)      │  │  • Greenhouse     │
│  • Lever          │  │                   │  │  • Lever          │
│  • Ashby          │  │                   │  │  • Ashby          │
│  • HN/RemoteOK    │  │                   │  │                   │
└───────────────────┘  └───────────────────┘  └───────────────────┘
```

### Component Dependencies

```
orchestrator.py
├── job_monitor.py
│   ├── ats_scraper.py (Greenhouse/Lever/Ashby/Workable APIs)
│   └── ats_integration.py (wrapper)
├── job_matcher.py
│   └── Claude API (AI scoring)
├── auto_applicator.py
│   ├── company_researcher.py (Claude research)
│   ├── resume_selector.py (3 variants)
│   ├── ats_submitter.py (Playwright browser automation)
│   │   └── greenhouse_email_verifier.py (IMAP)
│   └── email_service.py (Resend API)
├── founder_finder_v2.py
│   └── message_generator.py
├── telegram_notifier.py
└── linkedin_cmo_v4.py (daily posts via Make.com)
```

---

## 7. HOW TO MODIFY/EXTEND

### Adding New ATS Companies

Edit `src/scrapers/ats_scraper.py`:

```python
GREENHOUSE_COMPANIES = [
    # Add new company slug here
    "new-company-slug",
    ...
]
```

### Changing Target Roles

Edit `src/autonomous/job_monitor.py` and `CAREER_FOCUS.md`:

```python
TARGET_ROLES = [
    "New Role Title",
    ...
]
```

### Adjusting Scoring Thresholds

Edit `src/autonomous/orchestrator.py`:

```python
AUTO_APPLY_THRESHOLD = 65   # Higher = more selective
OUTREACH_THRESHOLD = 60
```

### Adding New Job Sources

1. Create scraper in `src/scrapers/new_source.py`
2. Add to `job_monitor.py`:
   ```python
   async def _fetch_new_source(self):
       # Fetch and return jobs
   ```
3. Call from `find_new_jobs()` method

### Modifying Resume Selection

Edit `src/templates/resume_selector.py`:
- Add new resume variant
- Update selection logic

### Customizing Application Materials

Edit `src/autonomous/auto_applicator.py`:
- Modify Claude prompts
- Change cover letter format

---

## 📈 CURRENT PERFORMANCE (December 2025)

| Metric | Value |
|--------|-------|
| Jobs scraped per cycle | ~3000 |
| Jobs after career gate | ~700 (22%) |
| Jobs scoring 60+ | ~5-10 |
| Applications per day | 3-5 (capped) |
| Email verification success | ✅ Working |
| ATS submission success | ✅ Working |
| Founder outreach | ✅ Working |

---

## 🛠️ TROUBLESHOOTING

### IMAP Authentication Failed
1. Generate new app password in Zoho → Settings → Security
2. Update `ZOHO_APP_PASSWORD` in Railway
3. Ensure IMAP is enabled in Zoho Mail settings

### No Jobs Found
1. Check ATS scraper logs for API errors
2. Verify target companies are still using Greenhouse/Lever
3. Check if career gate is too restrictive

### Application Submission Failed
1. Check Playwright browser logs
2. Verify form selectors haven't changed
3. Check if email verification is working

### Low Match Scores
1. Adjust scoring weights in `job_matcher.py`
2. Update target keywords in career gate
3. Review Claude prompts for AI scoring

---

## 📝 VERSION HISTORY

| Date | Change |
|------|--------|
| 2025-12-21 | Fixed email verification (Notification folder + submit button) |
| 2025-12-20 | Added Ashby API scraping |
| 2025-12-18 | Calibrated scoring thresholds (60/58/55) |
| 2025-12-17 | First production application sent |
| 2025-12-16 | ATS form submission working |
| 2025-12-13 | Initial ATS API integration |

---

## 8. KNOWN LIMITATIONS & WHY

### ⚠️ Platforms That Can't Be Easily Fixed

| Platform | Issue | Why It's Hard |
|----------|-------|---------------|
| **Workable** | API returns 404 | Workable changed their API structure. Now requires Cloudflare bypass and possibly authentication. Companies are moving away from it anyway. |
| **YC Work at Startup** | Needs Algolia API key | Uses Algolia search backend with private API key embedded in their frontend. Would need to scrape their React app or get an API key. |
| **Wellfound (AngelList)** | GraphQL + Auth | Requires authenticated GraphQL queries. Would need to maintain a session and potentially handle CAPTCHAs. |
| **LinkedIn Jobs** | Heavy anti-bot | Aggressive rate limiting, CAPTCHAs, account bans. Not worth the risk. |

**Reality Check:** The current ATS APIs (Greenhouse 73 + Lever 19 + Ashby 37 = **129 companies**) already cover the best AI/ML startups. Adding more sources has diminishing returns.

---

## 9. 🚀 FUTURE ROADMAP

### PHASE 1: Intelligence Upgrades (High Impact, Achievable)

#### 1.1 📊 Success Prediction Model
**Status:** NOT IMPLEMENTED  
**Priority:** HIGH  
**Effort:** 2-3 days

```python
# Track which applications get responses
# Build ML model predicting:
# - Which companies respond to founder outreach?
# - Which job descriptions have highest success rate?
# - What message styles work best?

# Implementation:
# 1. Log all application outcomes to SQLite
# 2. After 50+ applications, train simple classifier
# 3. Add "predicted_response_rate" to scoring
```

**Why genius:** Self-improving system. After 30 days, you know exactly which companies are worth applying to.

**Files to modify:**
- `src/autonomous/orchestrator.py` - add outcome tracking
- `src/agents/job_matcher.py` - add prediction score
- `autonomous_data/vibejobhunter.db` - add outcomes table

---

#### 1.2 🧠 AI-Powered Company Intelligence
**Status:** PARTIALLY IMPLEMENTED (basic research exists)  
**Priority:** HIGH  
**Effort:** 1-2 days

```python
# Before applying, research:
# - Recent company blog posts (via RSS/Atom feeds)
# - GitHub commits (public repos via API)
# - Product launches (ProductHunt API)
# - Founder tweets (X API - if available)
#
# Then generate hyper-personalized messages referencing specific work

# Example output:
"I saw your v2.3 release on ProductHunt last week - the RAG improvements 
look solid. I've built similar retrieval systems at scale..."
```

**Why genius:** Shows you actually researched them, not mass applying. 10x higher response rate.

**Files to modify:**
- `src/autonomous/company_researcher.py` - add RSS/GitHub/ProductHunt
- `src/autonomous/message_generator.py` - use research in messages

---

#### 1.3 📧 Response Detection & Auto-Triage
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Effort:** 2-3 days

```python
# Monitor inbox for responses
# Classify with Claude:
# - POSITIVE: "Let's schedule a call" → Alert immediately
# - REJECTION: "We've decided to move forward with other candidates" → Log
# - QUESTION: "Can you tell me more about..." → Draft response
# - SPAM: Ignore

# Auto-actions:
# - POSITIVE → Send calendar link (Calendly integration)
# - QUESTION → Draft response, notify for review
```

**Why genius:** Never miss a hot lead. Instant response = higher conversion.

**Files to modify:**
- `src/autonomous/greenhouse_email_verifier.py` - extend for response detection
- New: `src/autonomous/response_handler.py`

---

### PHASE 2: Multi-Touch Sequencing (Medium Impact)

#### 2.1 🎭 Coordinated Outreach Sequence
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Effort:** 3-4 days

```python
# Day 0: Submit via ATS
# Day 0 + 30min: Founder email (if score >= 58)
# Day 3: Check for response → if none, queue follow-up
# Day 7: Send follow-up email (gentle nudge)
# Day 14: Final follow-up OR close loop

# All perfectly timed, all coordinated
# Track in database: application_id → sequence_stage → next_action_date
```

**Why genius:** Professional persistence without being annoying. 3x higher response rate with proper sequencing.

**Files to modify:**
- New: `src/autonomous/sequence_manager.py`
- `src/autonomous/orchestrator.py` - add sequence check to cycle

---

### PHASE 3: Network Effects (Advanced)

#### 3.1 🕸️ Founder Network Mapping
**Status:** NOT IMPLEMENTED  
**Priority:** LOW (high effort, high reward)  
**Effort:** 1-2 weeks

```python
# Build graph of:
# - YC batch connections (who was in same batch)
# - Investor portfolios (who shares investors)
# - Twitter/LinkedIn follows (mutual connections)
# - Previous companies (alumni networks)

# Use for:
# - "You were in YC W23 with [other founder I know]..."
# - Prioritize companies where you have warm intro potential
# - Identify bridge contacts
```

**Why genius:** Warm intros have 50%+ response rate vs 5% cold. This is how top candidates actually get jobs.

**Data sources:**
- YC Company Directory (public)
- Crunchbase (API or scrape)
- LinkedIn (manual or limited API)

---

### PHASE 4: Platform Expansion (If Needed)

#### 4.1 More ATS Platforms
**Status:** Deprioritized  
**Priority:** LOW

| Platform | Feasibility | Notes |
|----------|-------------|-------|
| **Rippling** | MEDIUM | Some YC companies use it, has public job boards |
| **BambooHR** | LOW | Mostly HR-focused companies |
| **Jobvite** | LOW | Enterprise-focused |

**Recommendation:** Focus on intelligence (Phase 1-2) before adding more sources. 129 companies is already comprehensive.

---

### PHASE 5: The Dream Features (Long-term Vision)

#### 5.1 🤖 Full Interview Pipeline Automation
```
Application → Response Detection → Auto-Schedule → 
Prep Materials Generated → Calendar Reminder → 
Post-Interview Follow-up → Offer Negotiation Support
```

#### 5.2 📈 Market Intelligence Dashboard
```
- Which companies are hiring most aggressively?
- Salary trend analysis by role/location
- Time-to-hire predictions
- "Hot" company alerts (new funding, team growth)
```

#### 5.3 🎯 Portfolio-to-Job Matching
```
- Analyze your GitHub repos
- Match to job requirements
- Auto-generate "relevant project" bullets for each application
- Link specific commits/PRs that prove skills
```

---

## 10. IMPLEMENTATION PRIORITY MATRIX

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Success Prediction Model | HIGH | 2-3 days | ⭐⭐⭐ DO FIRST |
| Company Intelligence (RSS/GitHub) | HIGH | 1-2 days | ⭐⭐⭐ DO FIRST |
| Response Detection | HIGH | 2-3 days | ⭐⭐ DO SECOND |
| Multi-Touch Sequencing | MEDIUM | 3-4 days | ⭐⭐ DO SECOND |
| Network Mapping | HIGH | 1-2 weeks | ⭐ LONG-TERM |
| More ATS Platforms | LOW | varies | ❌ SKIP FOR NOW |

---

## 11. WHAT MAKES THIS SYSTEM UNIQUE

### Already Implemented (Nobody Else Has This):
1. ✅ **End-to-end Greenhouse automation** - Form fill + email verification + submit
2. ✅ **Claude-powered personalization** - Every application is unique
3. ✅ **Multi-resume selection** - Right resume for right role
4. ✅ **Founder outreach pipeline** - Not just ATS, but direct contact

### With Roadmap Features:
1. 🔮 **Self-improving scoring** - Learns what works for YOU
2. 🔮 **Hyper-personalized outreach** - References their latest blog/GitHub
3. 🔮 **Automated response handling** - Never miss a hot lead
4. 🔮 **Professional persistence** - Timed follow-up sequences

**This isn't just automation. This is an AI job hunting co-founder that gets smarter over time.**

---

**Built by Elena Revicheva with AI Co-Founders** 🤖

*This system runs autonomously 24/7 on Railway, finding and applying to AI/ML jobs.*

*Last Updated: December 21, 2025*
