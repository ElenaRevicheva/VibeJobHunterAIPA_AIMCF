# VIBEJOBHUNTER - COMPLETE SYSTEM DOCUMENTATION

**Last Updated:** February 9, 2026  
**Status:** FULLY OPERATIONAL on Oracle Cloud  
**Deployment:** Oracle Cloud (systemd service `vibejobhunter-web.service`)  
**Source of truth:** Oracle server → GitHub → Local

---

## TABLE OF CONTENTS

1. [What This System Does](#1-what-this-system-does)
2. [The Autonomous Job Application Flow (Step by Step)](#2-the-autonomous-job-application-flow)
3. [What Is Automatic vs What Needs Manual Action](#3-what-is-automatic-vs-manual)
4. [Target Roles & Platforms](#4-target-roles--platforms)
5. [Job Sources (All Active)](#5-job-sources)
6. [Key Files & Data](#6-key-files--data)
7. [Configuration](#7-configuration)
8. [LinkedIn CMO (AI Marketing Co-Founder)](#8-linkedin-cmo)
9. [Known Limitations & Why](#9-known-limitations)
10. [Version History](#10-version-history)

---

## QUICK RECAP: WHAT HAPPENS EVERY HOUR

```
Every hour, your system:
1. Scrapes ~3000+ jobs from 218 AI/ML companies (Greenhouse, Lever, Ashby, Workable)
2. Searches Dice MCP for ~55 additional tech jobs (8 query variations)
3. Checks 6 secondary sources (HN, RemoteOK, YC, Wellfound, WeWorkRemotely, AI-Jobs.net)
4. Filters through career gate (~78% pass rate)
5. Penalizes wrong-domain roles (DevOps, QA, DBA get -15 to -30 penalty)
6. Scores each with Claude AI (0-100)
7. Auto-applies to jobs scoring 60+ (fills forms, handles email verification)
8. Sends founder outreach for jobs scoring 58+ (max 2/day cap)
9. Tracks follow-ups (+3/+8 day auto follow-up emails)
10. Scans inbox for interview requests (AI-powered response detection)
11. Sends you Telegram notifications for everything

Every 10 minutes:
- Checks if LinkedIn CMO daily post is due

Daily at 15:10 UTC (10:10 AM Panama):
- LinkedIn CMO posts AI-generated content (EN/ES alternating, persists across reboots)

Daily at 20:00 UTC (3:00 PM Panama):
- Sends Telegram daily digest (applications, outreach, warm intros summary)
```

---

## 1. WHAT THIS SYSTEM DOES

VibeJobHunter is a **fully autonomous job hunting engine** deployed on Oracle Cloud.

### Feature Status (February 2026)

| Feature | Status | Automatic? | Description |
|---------|--------|------------|-------------|
| **ATS Job Scraping** | LIVE | AUTOMATIC | Scrapes 3000+ jobs/hour from Greenhouse, Lever, Ashby, Workable (218 companies) |
| **Dice MCP Tech Jobs** | LIVE (NEW) | AUTOMATIC | 55+ tech jobs/cycle via Model Context Protocol (8 keyword queries) |
| **Secondary Sources** | LIVE | AUTOMATIC | HN, RemoteOK, YC WAAS, Wellfound, WeWorkRemotely, AI-Jobs.net |
| **Career Gate Filter** | LIVE | AUTOMATIC | Filters by keywords, location, salary, company size, blocklist |
| **Domain-Match Filter** | LIVE (NEW) | AUTOMATIC | Penalizes non-AI/non-product roles (DevOps, QA, DBA, etc.) |
| **AI Job Scoring** | LIVE | AUTOMATIC | Claude scores each job 0-100 on AI relevance, autonomy, depth |
| **Auto-Application** | LIVE | AUTOMATIC | Fills and submits Greenhouse forms (max 5/day) |
| **Email Verification** | LIVE | AUTOMATIC | Reads verification codes from Zoho Mail IMAP |
| **Resume Selection** | LIVE | AUTOMATIC | 3 resume variants, auto-selects based on role |
| **Founder Outreach** | LIVE | SEMI-AUTO | Finds contacts, generates messages, sends email if verified address found. LinkedIn messages queued for MANUAL send |
| **Outreach Daily Cap** | LIVE (NEW) | AUTOMATIC | Max 2 outreach messages per day |
| **Follow-Up Engine** | LIVE (NEW) | AUTOMATIC | +3/+8 day auto follow-up emails for tracked applications |
| **LinkedIn CMO** | LIVE | AUTOMATIC | Daily AI-generated posts via Make.com (EN/ES). Reboot-safe. |
| **Telegram Bot** | LIVE | AUTOMATIC | Real-time notifications + interactive commands |
| **Response Detection** | LIVE | AUTOMATIC | AI-powered inbox scanning for interview requests |
| **Seen Jobs TTL** | LIVE (NEW) | AUTOMATIC | Re-evaluates jobs after 21 days, applied jobs never retry |
| **Warm Intro Queue** | ENCODED | MANUAL SETUP NEEDED | Database ready, needs real contacts added |
| **Daily Digest** | LIVE (NEW) | AUTOMATIC | Telegram summary at 3 PM Panama |

---

## 2. THE AUTONOMOUS JOB APPLICATION FLOW

### Every Hour, The System Runs This Pipeline:

```
STEP 1: JOB DISCOVERY (AUTOMATIC)
══════════════════════════════════
  PRIMARY: ATS APIs
  ├── Greenhouse API → 106 companies
  ├── Lever API → 36 companies
  ├── Workable API → 17 companies
  └── Ashby API → 59 companies
  → ~3000 jobs scraped

  NEW: Dice MCP (Tech-Only Database)
  ├── "AI Product Engineer"
  ├── "Applied LLM Engineer"
  ├── "Founding Engineer AI"
  ├── "AI Engineer Python"
  ├── "LLM Engineer"
  ├── "AI Agent Engineer"
  ├── "AI Developer Tools Engineer"
  └── "Personal AI Engineer"
  → ~55 unique jobs (deduplicated across 8 queries)

  SECONDARY: (parallel, 15-20s timeout each)
  ├── Hacker News Who's Hiring
  ├── RemoteOK API
  ├── YC Work At A Startup (Algolia)
  ├── Wellfound (GraphQL)
  ├── WeWorkRemotely (RSS)
  └── AI-Jobs.net
  → Variable (0-100 jobs depending on availability)

  TOTAL: ~3000-3200 jobs per cycle
                    │
                    ▼
STEP 2: CAREER GATE FILTER (AUTOMATIC)
══════════════════════════════════════
  ✅ Pass: founding, AI, ML, senior, staff, principal, product engineer, LLM
  ❌ Reject: junior, intern, sales, recruiter, administrative
  ❌ Reject: Blocklisted companies (Google, Meta, Amazon, OpenAI, etc. - too large)
  ❌ Reject: Incompatible on-site locations (London, Tokyo, etc.)
  ❌ Reject: Salary below floor ($150K US, $120K remote, $100K LATAM)
  ❌ Reject: Company >150 employees or Series D+

  RESULT: ~78% pass rate → ~700-800 jobs
                    │
                    ▼
STEP 3: DOMAIN-MATCH FILTER (AUTOMATIC) — NEW Feb 2026
══════════════════════════════════════════════════════
  Penalizes wrong-domain roles that slip through career gate:
  • DevOps/SRE/Infrastructure → -15 to -25 penalty
  • QA/Testing/SDET → -20 penalty
  • DBA/Data Warehouse → -20 penalty
  • Payroll/HR Tech → -30 penalty
  • Security/Compliance → -15 penalty

  Jobs matching AI/LLM/Product/Founding → NO penalty (or small boost)
                    │
                    ▼
STEP 4: AI SCORING via Claude (AUTOMATIC)
════════════════════════════════════════
  Each job scored 0-100:
  • AI/ML relevance (25%)
  • Autonomy/0→1 signals (25%)
  • Technical depth (20%)
  • Company stage (15%)
  • Remote-friendliness (15%)
  • Bonuses: +4 senior/staff, +3 founding, +15 YC company
  • Domain penalty applied from Step 3
                    │
                    ▼
STEP 5: ROUTING BY SCORE (AUTOMATIC)
═══════════════════════════════════
  Score ≥ 60 → AUTO-APPLY (ATS form submission)      [max 5/day]
  Score ≥ 58 → FOUNDER OUTREACH (email or LinkedIn)   [max 2/day]
  Score ≥ 55 → REVIEW QUEUE (saved, Telegram notified)
  Score < 55 → DISCARDED
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
  AUTO-APPLY FLOW         FOUNDER OUTREACH FLOW
  (AUTOMATIC)             (SEMI-AUTOMATIC)
  ─────────────           ──────────────────
  1. Research company      1. Research company (Claude)
  2. Select resume variant 2. Find founder email/LinkedIn
  3. Generate cover letter 3. Generate personalized message
  4. Fill Greenhouse form  4a. Email found → SEND via Resend (AUTO)
  5. Handle email verify   4b. No email → Queue for MANUAL LinkedIn send
  6. Submit application    5. Log to outreach_log.jsonl
  7. Save to database      6. Notify via Telegram
  8. Notify via Telegram
                    │
                    ▼
STEP 6: FOLLOW-UP ENGINE (AUTOMATIC) — NEW Feb 2026
═══════════════════════════════════════════════════
  Tracks all applications and sends follow-ups:
  • +3 days → First follow-up email (gentle check-in)
  • +8 days → Second follow-up email (with new context)
  • Only for applications where we have a contact email
  • Respects do-not-follow-up flags

  NOTE: Activates automatically as applications accumulate
                    │
                    ▼
STEP 7: RESPONSE DETECTION (AUTOMATIC)
═══════════════════════════════════════
  Scans inbox after each cycle:
  • Connects to Zoho Mail via IMAP
  • Analyzes each email with Claude AI
  • Classifies: POSITIVE | REJECTION | QUESTION | SPAM
  • If POSITIVE → Instant Telegram alert with details
```

---

## 3. WHAT IS AUTOMATIC vs WHAT NEEDS MANUAL ACTION

### FULLY AUTOMATIC (runs 24/7 without you)

| Action | Frequency | Details |
|--------|-----------|---------|
| Job discovery (all sources incl. Dice MCP) | Every hour | 8+ sources, ~3000+ jobs |
| Career gate + domain filtering | Every hour | Instant, rule-based |
| AI scoring | Every hour | Claude evaluates each new job |
| Auto-application (Greenhouse forms) | Every hour | Max 5/day, with email verification |
| Email outreach (when verified email found) | Every hour | Max 2/day, via Resend API |
| Follow-up emails (+3/+8 days) | Daily check | Sends to tracked contacts |
| Response detection (inbox scan) | After each cycle | AI classifies responses |
| LinkedIn CMO post | Daily 10:10 AM Panama | Claude-generated, reboot-safe |
| Daily Telegram digest | Daily 3 PM Panama | Summary of all activity |
| Telegram notifications | Real-time | Every application, outreach, score |

### REQUIRES YOUR MANUAL ACTION

| Action | Why Manual | What You Do |
|--------|-----------|-------------|
| **LinkedIn outreach messages** | LinkedIn has NO public API for sending messages. Browser automation risks account ban. | Open Telegram, see the generated message, copy/paste to LinkedIn. Messages are in `autonomous_data/manual_outreach_queue.json`. |
| **Review queue jobs** (score 55-59) | These are borderline — need your judgment | Check Telegram notifications or review queue, decide to apply or skip. |
| **Warm intro contacts** | Only you know your personal network | Add real contacts to warm_intro_queue via Telegram bot or database. Currently has 3 inactive placeholders. |
| **LinkedIn CMO content review** | Optional — posts automatically, but you may want to review quality | Check LinkedIn after 10:10 AM Panama for new post. |
| **Oracle instance monitoring** | Oracle free tier sometimes stops instances | If Telegram goes silent for >2 hours, check Oracle Cloud console. |

---

## 4. TARGET ROLES & PLATFORMS

### Target Role Keywords (aligned with LinkedIn profile)

```
Primary (from LinkedIn "Seeking" section):
- AI Product Engineer
- Applied LLM Engineer
- Founding Engineer
- AI Engineer
- AI Solutions Architect

Secondary:
- Senior AI Engineer, Staff AI Engineer
- Technical Lead - AI
- ML Engineer, LLM Engineer
- Platform Engineer, Full Stack Engineer
- AI Agent Engineer, Personal AI Engineer
```

### Company Targeting Strategy

| Category | Strategy | Examples |
|----------|----------|---------|
| **APPLY** | Seed to Series B, <150 employees, AI-focused | Small AI startups on Greenhouse/Lever |
| **APPLY** | Dice MCP tech companies | Remote AI/LLM/Python roles |
| **OUTREACH** | Founders of AI companies | Personalized email/LinkedIn |
| **BLOCK** | Big Tech (>1000 employees) | Google, Meta, Amazon, OpenAI, Anthropic |
| **BLOCK** | Consulting/Enterprise | Accenture, Deloitte, Infosys |
| **BLOCK** | Large Fintech | Stripe, PayPal, Coinbase |

---

## 5. JOB SOURCES

| Source | Type | How It Works | Jobs/Cycle | Status |
|--------|------|-------------|------------|--------|
| **Greenhouse** | REST API | Scrapes 106 companies | ~2000 | ACTIVE |
| **Ashby** | GraphQL | Scrapes 59 companies | ~900 | ACTIVE |
| **Lever** | REST API | Scrapes 36 companies | ~150 | ACTIVE |
| **Workable** | REST API | Scrapes 17 companies | Variable | ACTIVE |
| **Dice MCP** | MCP Protocol | 8 keyword queries, remote, tech-only | ~55 | NEW - ACTIVE |
| **Hacker News** | Algolia API | Who's Hiring thread | ~90 | ACTIVE |
| **RemoteOK** | REST API | Filtered for AI/ML | ~18 | ACTIVE |
| **YC WAAS** | Algolia/Scrape | 3 fallback methods | Variable | INTERMITTENT |
| **Wellfound** | GraphQL | AI Engineer queries | Variable | INTERMITTENT |
| **WeWorkRemotely** | RSS | Programming category | Variable | ACTIVE |
| **AI-Jobs.net** | API/Scrape | AI/ML focused board | Variable | INTERMITTENT |

### Dice MCP Search Queries (new source)

These are the 8 queries run every cycle, aligned with your LinkedIn goals:
1. "AI Product Engineer"
2. "Applied LLM Engineer"
3. "Founding Engineer AI"
4. "AI Engineer Python"
5. "LLM Engineer"
6. "AI Agent Engineer"
7. "AI Developer Tools Engineer"
8. "Personal AI Engineer"

Feature flag: `DICE_MCP_ENABLED` (default: true)

---

## 6. KEY FILES & DATA

### Core Source Files

```
src/
├── autonomous/
│   ├── orchestrator.py              # Main brain - runs hourly cycles
│   ├── job_monitor.py               # Fetches jobs from ALL sources (incl. Dice MCP)
│   ├── job_gate.py                  # Career gate filter (keywords, blocklist, salary)
│   ├── auto_applicator.py           # Generates application materials
│   ├── ats_submitter.py             # Submits to ATS (Greenhouse/Lever)
│   ├── ats_integration.py           # Safe ATS wrapper with feature flag
│   ├── greenhouse_email_verifier.py # IMAP verification code reader
│   ├── response_detector.py         # AI-powered response detection
│   ├── company_researcher.py        # Claude-powered company research
│   ├── founder_finder_v2.py         # Finds founder contacts
│   ├── message_generator.py         # Generates outreach messages
│   ├── email_service.py             # Sends emails via Resend
│   ├── follow_up_engine.py          # NEW: +3/+8 day auto follow-ups
│   └── warm_intro_queue.py          # NEW: Personal network contacts (needs setup)
│
├── scrapers/
│   ├── ats_scraper.py               # Greenhouse/Lever/Ashby/Workable APIs
│   └── dice_mcp_client.py           # NEW: Dice tech jobs via MCP protocol
│
├── agents/
│   └── job_matcher.py               # AI scoring + domain-match filter
│
├── templates/
│   └── resume_selector.py           # Selects from 3 resume variants
│
└── notifications/
    ├── telegram_notifier.py         # Telegram notifications
    ├── telegram_bot_enhanced.py     # Interactive bot commands
    └── linkedin_cmo_v4.py           # LinkedIn CMO v5.1 (daily posts)
```

### Data Files

```
autonomous_data/
├── vibejobhunter.db                # SQLite database (applications, companies, etc.)
├── seen_jobs.json                  # TTL-aware seen jobs (v2 format, 21-day expiry)
├── outreach_log.jsonl              # All generated outreach messages
├── manual_outreach_queue.json      # LinkedIn messages awaiting manual send
├── resumes/                        # PDF resume variants
├── applications/                   # Generated cover letters
├── cache/                          # Response cache
└── submissions/                    # ATS submission records

linkedin_cmo_data/
├── last_post_date.txt              # NEW: Persists last post date (survives reboot)
├── last_used_image.txt             # Tracks image rotation
├── last_used_language.txt          # Tracks EN/ES alternation
├── post_performance.json           # UTM tracking data
├── market_intelligence.json        # AI market analysis
└── strategy_decisions.json         # AI content strategy
```

---

## 7. CONFIGURATION

### Required Environment Variables (Oracle)

```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...          # Claude API (scoring, content, research)

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

# Zoho Mail (verification codes + responses)
ZOHO_EMAIL=aipa@aideazz.xyz
ZOHO_APP_PASSWORD=xxxxxxxxxxxx

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# LinkedIn CMO
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/...

# Feature Flags
ATS_SCRAPER_ENABLED=true              # ATS scraping on/off
DICE_MCP_ENABLED=true                 # Dice MCP on/off (NEW)
ATS_DRY_RUN=false                     # Set true for testing
ATS_SUBMISSION_ENABLED=true
SEEN_TTL_DAYS=21                      # Days before re-evaluating seen jobs
```

### Scoring Thresholds (in orchestrator.py)

```python
AUTO_APPLY_THRESHOLD = 60    # Score >= 60 → auto-submit application
OUTREACH_THRESHOLD = 58      # Score >= 58 → send founder outreach
REVIEW_THRESHOLD = 55        # Score >= 55 → save for review
MAX_DAILY_APPLICATIONS = 5   # Safety cap per day
MAX_DAILY_OUTREACH = 2       # NEW: Outreach cap per day
```

---

## 8. LINKEDIN CMO (AI Marketing Co-Founder)

### What It Does

The LinkedIn CMO is a **TRUE AI Co-Founder** (v5.1) that posts daily content:

| Feature | Implementation |
|---------|----------------|
| **Timing** | Daily at 15:10 UTC (10:10 AM Panama) — checked every 10 minutes |
| **Content** | Fresh AI-generated via Claude API with market trend analysis |
| **Languages** | EN on even weekdays, ES on odd weekdays (deterministic) |
| **Images** | 14 rotating images (no repeats) |
| **Posting** | Make.com webhook → LinkedIn |
| **Reboot Safety** | Last post date persisted to `linkedin_cmo_data/last_post_date.txt` |

### Content Generation Flow

```
1. Claude analyzes current market trends (3 trends)
2. AI makes strategic decision: HIRING vs FUNDRAISING vs VISIBILITY
3. Selects post type based on strategy
4. Claude generates fresh content (2000+ chars) with learning insights
5. Selects rotating image (anti-repeat)
6. Adds UTM tracking
7. Sends to Make.com webhook → LinkedIn
8. Saves post date to disk (reboot-safe)
```

---

## 9. KNOWN LIMITATIONS & WHY

| Limitation | Why | Workaround |
|-----------|-----|------------|
| **LinkedIn messages are MANUAL** | LinkedIn has no public message API. Browser automation risks permanent account ban. | Messages are generated and sent to Telegram. Copy/paste to LinkedIn. |
| **YC WAAS intermittent** | Uses private Algolia key that rotates | 3 fallback methods, works sometimes |
| **Wellfound intermittent** | GraphQL requires auth sessions | Falls back gracefully |
| **Greenhouse only ATS auto-apply** | Lever/Ashby have different form structures | Greenhouse is #1 priority (106 companies) |
| **Warm intro queue inactive** | Needs real contacts from your network | Add contacts via Telegram bot or SQL |
| **No catch-up for missed CMO posts** | If service down during 15:10-15:59 UTC | Post missed for that day, resumes next day |

---

## 10. VERSION HISTORY

| Date | Change | Impact |
|------|--------|--------|
| **2026-02-09** | Dice MCP integration (55+ tech jobs/cycle) | IMMEDIATE - new job source active |
| **2026-02-09** | Warm intro queue + outreach cap (2/day) + LinkedIn reboot persistence | Outreach cap & persistence ACTIVE. Warm intros need setup. |
| **2026-02-08** | Follow-up engine (+3/+8 day auto emails) | Activates as applications accumulate |
| **2026-02-08** | Domain-match filter (penalize non-AI roles) | IMMEDIATE - filtering wrong roles |
| **2026-02-08** | Seen-jobs TTL (21 day re-evaluation) + zero-cycle alerts | IMMEDIATE - recycling old jobs |
| 2026-01-28 | Fixed Telegram bot menu and CMO callbacks | Telegram bot working |
| 2026-01-09 | Migrated from Railway to Oracle Cloud | New infrastructure |
| 2025-12-22 | Response Detection (AI inbox scanning) | Automatic interview detection |
| 2025-12-21 | Vibe Coding Philosophy + true EN/ES alternation | LinkedIn CMO enhanced |
| 2025-12-20 | Ashby API scraping (59 companies) | More job sources |
| 2025-12-18 | Scoring threshold calibration (60/58/55) | Better routing |
| 2025-12-17 | First production application sent | Milestone |
| 2025-12-16 | ATS form submission working | Auto-apply live |
| 2025-12-13 | Initial ATS API integration | Foundation |

---

**Built by Elena Revicheva with AI Co-Founders**

*This system runs autonomously 24/7 on Oracle Cloud, finding and applying to AI/ML jobs while you sleep.*

*Last Updated: February 9, 2026*
