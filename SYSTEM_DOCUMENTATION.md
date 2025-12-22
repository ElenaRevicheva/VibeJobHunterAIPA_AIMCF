# 🤖 VIBEJOBHUNTER - COMPLETE SYSTEM DOCUMENTATION

**Last Updated:** December 22, 2025  
**Status:** ✅ FULLY OPERATIONAL + GENIUS FEATURES  
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
8. [LinkedIn CMO (AI Marketing Co-Founder)](#8-linkedin-cmo-ai-marketing-co-founder)
9. [Known Limitations & Why](#9-known-limitations--why)
10. [Future Roadmap](#10-future-roadmap)

---

## 🚀 QUICK RECAP: WHAT HAPPENS EVERY HOUR

```
Every hour, your system:
1. Scrapes ~3000 jobs from 129 AI/ML companies (Greenhouse, Lever, Ashby)
2. Filters to ~700 relevant jobs (career gate)
3. Scores each with Claude AI
4. Auto-applies to jobs scoring 60+ (fills forms, handles email verification)
5. Sends founder outreach for jobs scoring 58+
6. Scans inbox for interview requests (AI-powered response detection)
7. Sends you Telegram notifications for everything

Daily at 21:30 UTC:
- LinkedIn CMO posts AI-generated content (EN/ES alternating)
```

---

## 1. WHAT THIS SYSTEM DOES

VibeJobHunter is a **fully autonomous job hunting engine** that:

### ✅ Implemented & Working (December 2025)

| Feature | Status | Description |
|---------|--------|-------------|
| **ATS Job Scraping** | ✅ LIVE | Scrapes 3000+ jobs/hour from Greenhouse, Lever, Ashby |
| **Smart Job Scoring** | ✅ LIVE | AI-powered scoring (Claude) + keyword matching |
| **Auto-Application** | ✅ LIVE | Fills and submits Greenhouse forms automatically |
| **Email Verification** | ✅ LIVE | Reads verification codes from Zoho Mail IMAP |
| **Resume Selection** | ✅ LIVE | 3 resume variants, auto-selects based on role |
| **Founder Outreach** | ✅ LIVE | Finds founder contacts, generates personalized messages |
| **LinkedIn CMO** | ✅ LIVE | Daily AI-generated posts via Make.com (EN/ES) |
| **Telegram Bot** | ✅ LIVE | Real-time notifications + interactive commands |
| **Email Service** | ✅ LIVE | Sends applications via Resend API |
| **Database Tracking** | ✅ LIVE | SQLite tracks all applications |
| **🧠 Response Detection** | ✅ LIVE | AI-powered inbox scanning for interview requests |

---

## 2. THE AUTONOMOUS JOB APPLICATION FLOW

### Every Hour, The System Runs This 5-Step Cycle:

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
│                                                                      │
│ RESULT: ~700 jobs pass the gate (22%)                                │
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
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: 🧠 RESPONSE DETECTION (GENIUS FEATURE)                       │
│ ─────────────────────────────────────────────                        │
│ After each cycle, scans inbox for responses:                         │
│ • Connects to Zoho Mail via IMAP                                     │
│ • Analyzes each email with Claude AI                                 │
│ • Classifies: POSITIVE | REJECTION | QUESTION | SPAM                 │
│ • If POSITIVE → 🔥🔥🔥 Instant Telegram alert!                        │
│ • Saves all responses to database (for success prediction)           │
└─────────────────────────────────────────────────────────────────────┘
```

### Email Verification Flow (Greenhouse):

```
Form submitted → Greenhouse sends verification email to aipa@aideazz.xyz
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ IMAP CONNECTION TO ZOHO MAIL                                         │
│ • Server: imappro.zoho.com:993 (SSL)                                 │
│ • Auto-discovers all folders (INBOX, Notification, etc.)             │
│ • Searches for: security code, verification emails                   │
│ • Extracts 8-character code from email body                          │
│ • Timeout: 180 seconds (3 minutes)                                   │
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
| **Hacker News** | Firebase API | - | ~90 |
| **RemoteOK** | REST API | - | ~18 |

### 🔥 Top Target Companies (from `src/scrapers/ats_scraper.py`)

**Frontier AI Labs:**
- Anthropic, OpenAI, DeepMind, xAI, Meta AI

**AI Infrastructure:**
- Databricks, Scale AI, Modal, Anyscale, Together AI, Fireworks AI, Cohere

**AI Products:**
- Perplexity, Runway, Jasper, Grammarly, Cursor

**AI Robotics:**
- Figure AI, Nuro, Waymo

**Dev Tools:**
- Vercel, Figma, Retool, Supabase, Linear, Railway

**Fintech:**
- Stripe, Ramp, Brex, Mercury

---

## 4. KEY FILES & DATA

### 📁 Core Source Files

```
src/
├── autonomous/
│   ├── orchestrator.py              # 🧠 Main brain - runs hourly cycles
│   ├── job_monitor.py               # 🔍 Fetches jobs from all sources
│   ├── auto_applicator.py           # 📝 Generates application materials
│   ├── ats_submitter.py             # 🚀 Submits to ATS (Greenhouse/Lever)
│   ├── greenhouse_email_verifier.py # 📧 IMAP verification code reader
│   ├── response_detector.py         # 🧠 AI-powered response detection (NEW!)
│   ├── company_researcher.py        # 🔬 Claude-powered company research
│   ├── founder_finder_v2.py         # 👤 Finds founder contacts
│   ├── message_generator.py         # ✍️ Generates outreach messages
│   └── email_service.py             # 📤 Sends emails via Resend
│
├── scrapers/
│   └── ats_scraper.py               # 🕷️ Greenhouse/Lever/Ashby APIs
│
├── agents/
│   └── job_matcher.py               # 🎯 AI-powered job scoring
│
├── templates/
│   └── resume_selector.py           # 📄 Selects from 3 resume variants
│
└── notifications/
    ├── telegram_notifier.py         # 📱 Telegram notifications
    ├── telegram_bot_enhanced.py     # 🤖 Interactive bot commands
    └── linkedin_cmo_v4.py           # 📣 LinkedIn CMO v5.1 (daily posts)
```

### 📊 Data Files

```
autonomous_data/
├── resumes/
│   ├── founding_engineer.pdf        # Resume variant 1
│   ├── senior_ai_engineer.pdf       # Resume variant 2
│   ├── ai_solutions_architect.pdf   # Resume variant 3
│   └── elena_resume.pdf             # Default resume
│
├── applications/                    # Generated cover letters/materials
│   └── application_*.txt
│
├── ats_cache/                       # Cached job listings
│   └── jobs_*.json
│
├── last_used_image.txt              # Tracks image rotation (CMO)
├── last_used_language.txt           # Tracks EN/ES alternation (CMO)
│
└── vibejobhunter.db                 # SQLite database
```

### 🗄️ Database Tables (SQLite)

```sql
-- Applications tracking
applications (id, company, role, score, status, applied_at, ...)

-- Detected responses (for success prediction)
detected_responses (id, email_id, from_email, company_name, 
                   response_type, confidence, ai_analysis, ...)
```

---

## 5. CONFIGURATION

### 🔑 Required Environment Variables (Railway)

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

# Zoho Mail (for reading verification codes + responses)
ZOHO_EMAIL=aipa@aideazz.xyz
ZOHO_APP_PASSWORD=xxxxxxxxxxxx        # 12-char app-specific password

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# LinkedIn CMO
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/...

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
│  • Runs hourly autonomous cycles (Steps 1-5)                         │
│  • Coordinates all components                                        │
│  • Manages daily caps and rate limits                                │
│  • Sends Telegram notifications                                      │
│  • Calls response_detector after each cycle                          │
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
│   ├── ats_scraper.py (Greenhouse/Lever/Ashby APIs)
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
├── response_detector.py (NEW - AI inbox scanning)
│   └── Claude API (response classification)
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
- Add new resume variant (PDF in `autonomous_data/resumes/`)
- Update selection logic

### Customizing Application Materials

Edit `src/autonomous/auto_applicator.py`:
- Modify Claude prompts
- Change cover letter format

---

## 8. LINKEDIN CMO (AI Marketing Co-Founder)

### What It Does

The LinkedIn CMO is a **TRUE AI Co-Founder** that posts daily content:

| Feature | Implementation |
|---------|----------------|
| **Timing** | Daily at 21:30 UTC (4:30 PM Panama) |
| **Content** | Fresh AI-generated via Claude API |
| **Languages** | EN↔ES alternation (not random!) |
| **Images** | 14 rotating images (no repeats) |
| **Posting** | Make.com webhook → LinkedIn |

### Content Types

```python
# English (5 types)
"open_to_work"           # Founder-minded job seeking
"technical_showcase"     # Technical depth - 5 AIPAs
"transformation_story"   # CEO → Founder journey
"seeking_funding"        # Pre-seed pitch
"vibe_coding_philosophy" # Life transformation through AI (NEW!)

# Spanish (3 types)
"busco_trabajo"           # Spanish job seeking
"historia_transformacion" # Spanish journey
"filosofia_vibe_coding"   # Spanish vibe coding philosophy (NEW!)
```

### How It Works

```
Daily at 21:30 UTC:
1. Alternate language (EN → ES → EN → ES...)
2. Select random post type from that language
3. Generate fresh content with Claude
4. Select rotating image (1 of 14, no repeats)
5. Post via Make.com webhook
6. Track performance (UTM links)
```

### Files

- `src/notifications/linkedin_cmo_v4.py` - Main CMO logic
- `autonomous_data/last_used_language.txt` - Tracks EN/ES
- `autonomous_data/last_used_image.txt` - Tracks image rotation

---

## 9. KNOWN LIMITATIONS & WHY

### ⚠️ Platforms That Can't Be Easily Fixed

| Platform | Issue | Why It's Hard |
|----------|-------|---------------|
| **Workable** | API returns 404 | API structure changed, needs Cloudflare bypass |
| **YC Work at Startup** | Needs Algolia key | Uses private API key in frontend |
| **Wellfound (AngelList)** | GraphQL + Auth | Requires authenticated sessions |
| **LinkedIn Jobs** | Heavy anti-bot | CAPTCHAs, account bans - not worth risk |

**Reality Check:** The current ATS APIs (Greenhouse 73 + Lever 19 + Ashby 37 = **129 companies**) already cover the best AI/ML startups.

---

## 10. FUTURE ROADMAP

### ✅ COMPLETED

| Feature | Status | Date |
|---------|--------|------|
| Response Detection | ✅ DONE | Dec 22, 2025 |
| Email Verification Folder Discovery | ✅ DONE | Dec 22, 2025 |
| Vibe Coding Philosophy Content | ✅ DONE | Dec 21, 2025 |
| True EN↔ES Alternation | ✅ DONE | Dec 21, 2025 |

### ⭐⭐⭐ DO NEXT

| Feature | Impact | Effort |
|---------|--------|--------|
| Success Prediction Model | HIGH | 2-3 days |
| Company Intelligence (RSS/GitHub) | HIGH | 1-2 days |

### ⭐⭐ AFTER THAT

| Feature | Impact | Effort |
|---------|--------|--------|
| Multi-Touch Sequencing | MEDIUM | 3-4 days |
| Follow-up Email Automation | MEDIUM | 2 days |

### ⭐ LONG-TERM

| Feature | Impact | Effort |
|---------|--------|--------|
| Founder Network Mapping | HIGH | 1-2 weeks |
| Interview Pipeline Automation | HIGH | 1-2 weeks |

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
| Response detection | ✅ Working |

---

## 🛠️ TROUBLESHOOTING

### IMAP Authentication Failed
1. Generate new app password in Zoho → Settings → Security
2. Update `ZOHO_APP_PASSWORD` in Railway (no quotes!)
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

### Response Detection Not Working
1. Check Zoho IMAP connection in logs
2. Verify ANTHROPIC_API_KEY is set
3. Look for `[FINGERPRINT: 2025-12-22_GENIUS_RESPONSE_DETECTION_DEPLOYED]`

---

## 📝 VERSION HISTORY

| Date | Change |
|------|--------|
| 2025-12-22 | ✨ Added GENIUS Response Detection (AI-powered inbox scanning) |
| 2025-12-22 | Fixed email verification folder discovery (auto-discovers Notification folder) |
| 2025-12-21 | Added Vibe Coding Philosophy content to LinkedIn CMO |
| 2025-12-21 | Implemented true EN↔ES language alternation |
| 2025-12-21 | Fixed email verification (submit button detection) |
| 2025-12-20 | Added Ashby API scraping (37 companies) |
| 2025-12-18 | Calibrated scoring thresholds (60/58/55) |
| 2025-12-17 | First production application sent |
| 2025-12-16 | ATS form submission working |
| 2025-12-13 | Initial ATS API integration |

---

## 11. WHAT MAKES THIS SYSTEM UNIQUE

### Already Implemented:
1. ✅ **End-to-end Greenhouse automation** - Form fill + email verification + submit
2. ✅ **Claude-powered personalization** - Every application is unique
3. ✅ **Multi-resume selection** - Right resume for right role
4. ✅ **Founder outreach pipeline** - Not just ATS, but direct contact
5. ✅ **AI Response Detection** - Never miss an interview request
6. ✅ **AI Marketing Co-Founder** - Daily LinkedIn posts, zero manual work

### The Philosophy (Vibe Coding):

> "I apply for jobs using my own AI agent. I built the AI. The AI is the vehicle—I am the architect."

This isn't just automation. **This is an AI job hunting co-founder that gets smarter over time.**

---

**Built by Elena Revicheva with AI Co-Founders** 🤖

*This system runs autonomously 24/7 on Railway, finding and applying to AI/ML jobs while you sleep.*

*Last Updated: December 22, 2025*
