# VibeJobHunter — AI Job Discovery & Qualification Engine

**An agentic LangGraph pipeline that discovers, scores, and qualifies jobs 24/7 — delivering ready-to-send applications with the final decision always human-controlled — while an AI Marketing Co-Founder builds your personal brand on LinkedIn.**

Built solo by [Elena Revicheva](https://linkedin.com/in/elenarevicheva) using human-AI collaborative development.

[![Live on Oracle Cloud](https://img.shields.io/badge/Deployed-Oracle%20Cloud-red)](https://cloud.oracle.com)
[![AI Powered](https://img.shields.io/badge/AI-Claude%20Sonnet-blue)](https://anthropic.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem

Applying to AI/engineering roles manually means 100+ hours of repetitive work: searching job boards, reading descriptions, tailoring resumes, filling ATS forms, writing outreach messages — while also building a personal brand. For a solo founder relocating internationally, this is unsustainable.

## The Solution

VibeJobHunter runs autonomously 24/7 on Oracle Cloud:

- **Discovers** jobs from 11 sources every hour (218+ company ATS APIs + YC + Bright Data SERP job-board search + more)
- **Gates and scores** each job through a hard career filter + Claude AI scoring (100-point system, domain-match filtering)
- **Routes** through a LangGraph state machine (gate → score → route → notify) with SQLite checkpointing and a human-approval interrupt
- **Qualifies leads, not fake submissions** — every accepted job lands as a ready-to-act lead (tailored resume + AI cover letter) in Telegram and HubSpot; the human sends it. By design: an audit found "auto-apply" theater produces zero real outcomes, so the system was rebuilt around honest human-controlled applications
- **Generates personalized outreach** to founders at borderline companies, with follow-up reminders
- **Detects recruiter responses** in the inbox and promotes them across HubSpot (deal stage) + Trello (action card) + Telegram (alert) — three surfaces, one truth
- **Posts daily LinkedIn content** via an AI Marketing Co-Founder (bilingual EN/ES)

---

## Architecture

```
Oracle Cloud (24/7 systemd service)
│
├── Job Hunting Engine (runs every hour)
│   │
│   ├── 1. DISCOVER ──────────────────────────────────
│   │   ├── ATS APIs: 218 companies (Greenhouse, Lever, Ashby, Workable)
│   │   ├── Bright Data SERP: job-board search (Wellfound/Lever/
│   │   │   Greenhouse/Ashby) — replaced exhausted SerpAPI
│   │   ├── YC Work at a Startup (Algolia search)
│   │   ├── RemoteOK, WWR, AI Jobs, HN + more (11 sources)
│   │   └── ~2,000 jobs evaluated per cycle
│   │
│   ├── 2. GATE & SCORE ──────────────────────────────
│   │   ├── Hard career gate (~4-6% pass): wrong-role/big-co/
│   │   │   coding-assessment/pedigree/location hard-rejects
│   │   ├── Claude AI scoring (100 pts: AI Product 25, Autonomy 25,
│   │   │   Full-Stack 20, Business 15, Bilingual 5, Web3 10)
│   │   ├── YC company bonus: +15 pts
│   │   └── Deduplication: seen-jobs cache + per-job SQLite checkpoint
│   │
│   ├── 3. LANGGRAPH PIPELINE (7-node StateGraph) ────
│   │   ├── gate → score → route → notify, SQLite checkpointer
│   │   ├── Human-approval interrupt for borderline scores
│   │   │   (/approve_vjh_{id} | /reject_vjh_{id} via Telegram)
│   │   └── Content-hash job IDs for sources that omit IDs
│   │
│   ├── 4. DELIVER LEADS (human-controlled by design) ─
│   │   ├── Smart 3-way resume selection (EN default / founder /
│   │   │   Spanish-LATAM) — synced to latest resume
│   │   ├── AI cover letter generation (Claude)
│   │   ├── [HIRING-VJH-LEAD] deal → HubSpot "I Act TODAY" stage
│   │   └── Human reviews + submits — no fake auto-apply
│   │
│   └── 5. RESPONSES & FOLLOW UP ─────────────────────
│       ├── Inbox response detector (noise-domain blocklist)
│       ├── Real replies → HubSpot stage + Trello card + Telegram
│       └── Outreach reminders day 5 / day 8, daily caps
│
├── LinkedIn CMO (AI Marketing Co-Founder)
│   ├── Daily post at 10:10 AM Panama time
│   ├── Claude generates fresh content each day
│   ├── Bilingual alternation (EN ↔ ES)
│   ├── 14 rotating images (no repeats)
│   └── Posts via Make.com webhook
│
└── Telegram Bot (Real-time Control)
    ├── Today's summary, job listings, stats
    ├── Pending outreach with copy-paste messages
    ├── Pause/resume hunting
    ├── Trigger LinkedIn/Instagram posts on demand
    └── Full workflow & manual task guides
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **AI/LLM** | Claude (Haiku + Sonnet), Anthropic API | Job scoring, cover letters, content generation, company research |
| **Agent Pipeline** | LangGraph (7-node StateGraph, AsyncSqliteSaver) | Checkpointed per-job state, dedup, human-in-the-loop interrupt |
| **Evaluation** | pytest eval harness — 131 tests, 4 layers, LLM-as-judge (~$0.03/run) | Catches gate/scoring regressions before every deploy |
| **Backend** | Python 3.11, FastAPI, asyncio | Async job fetching from 11 sources in parallel |
| **Job Sources** | Greenhouse/Lever/Ashby/Workable APIs, YC Algolia, Bright Data SERP | Structured API access + resilient SERP when paid APIs die |
| **CRM** | HubSpot API (via CTO AIPA `/api/crm-event` hub) + Trello bridge | Every lead and recruiter reply lands where action happens |
| **Email** | Resend API, Zoho IMAP, Hunter.io | Sending, response detection, email discovery |
| **Database** | SQLite | Application tracking, LangGraph checkpoints, scoring history |
| **Infrastructure** | Oracle Cloud, systemd | Always-on, auto-restart, zero monthly cost |
| **Marketing** | Make.com webhooks, Claude | Automated LinkedIn content pipeline |
| **Notifications** | Telegram Bot API | Real-time interactive control panel |

---

## What's Working (June 2026)

| Feature | Status | Details |
|---------|--------|---------|
| ATS Job Discovery | **LIVE** | 218 companies across 4 ATS platforms, ~2,000 jobs/cycle |
| Bright Data SERP Job Search | **LIVE** | Job-board search (Wellfound/Lever/Greenhouse/Ashby) — shipped same day SerpAPI quota died |
| Career Gate | **LIVE** | Hard rejects: wrong roles, big-co, coding-assessment & pedigree walls, location mismatches (~4-6% pass) |
| LangGraph Pipeline | **LIVE** | 7-node StateGraph, SQLite checkpointer, human-approval interrupt |
| AI Job Scoring | **LIVE** | Claude-powered 100-point scoring + domain filter |
| Honest LEAD Mode | **LIVE** | Ready-to-send applications delivered to Telegram + HubSpot; human submits — by design |
| HubSpot Integration | **LIVE** | `[HIRING-VJH-LEAD]` / `[HIRING-VJH-SERP-LEAD]` deals → "I Act TODAY" stage |
| Response Detector | **LIVE** | Inbox replies → HubSpot stage + Trello action card + Telegram alert |
| Smart Resume Selection | **LIVE** | 3-way (EN default / founder voice / Spanish-LATAM), synced to June 2026 resumes |
| Eval Harness | **LIVE** | 131 tests, 4 layers, Claude-as-judge — run before every deploy |
| LinkedIn CMO | **LIVE** | Daily bilingual posts at 10:10 AM Panama |
| Telegram Bot | **LIVE** | Interactive menu, approvals, real-time stats |

---

## Recent Engineering Highlights (May–June 2026)

- **The honesty pivot.** An internal audit revealed the "auto-apply" path had logged ~700 "applications" while actually submitting **zero** — it recorded intent, not outcomes. Rebuilt the system around honest **LEAD mode** in hours: the agent finds, gates, scores, and prepares; the human sends. Rule earned: *measure the side-effect, not the intent — verify from logs and the database, never from counters.*
- **131-test eval harness with LLM-as-judge.** Layers 1–3 deterministic (keyword scoring, bias compensation, 22-job golden set); Layer 4 is Claude Haiku as an independent judge at ≥75% agreement, ~$0.03/run. Catches scoring regressions before every deploy.
- **Same-day provider migration.** SerpAPI's quota died silently (every query 429 → zero job leads for days). Diagnosed from logs, migrated job search to Bright Data organic SERP restricted to ATS domains, normalized to the existing job shape — leads flowing again the same day, downstream untouched.
- **Missing-ID resilience.** Several job sources return postings without IDs; the pipeline silently dropped every one as an error. Fixed with deterministic content-hash IDs (`company|title|url`) — processable *and* dedup-stable across cycles.
- **Three-surface response loop.** Recruiter replies detected in the inbox (with a platform-noise blocklist) now promote the deal in HubSpot, create a Trello card on the current-month board, and alert via Telegram — three surfaces, one truth.
- **Resume system sync.** All resume slots (PDFs + the markdown mirrors that feed cover-letter generation) carry the same June 2026 content — applications are consistent end-to-end, with automatic Spanish selection for LATAM companies.

---

## Quick Start

```bash
# Clone
git clone https://github.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF.git
cd VibeJobHunterAIPA_AIMCF

# Setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys and profile

# Run
python web_server.py
```

See [`.env.example`](.env.example) for all configuration options.

---

## Project Structure

```
├── src/
│   ├── autonomous/          # Core engine (orchestrator, job monitor, ATS submitter, follow-ups)
│   ├── agents/              # AI scoring, content generation, job matching
│   ├── scrapers/            # ATS scraper (218 cos), Dice MCP client, premium boards
│   ├── notifications/       # Telegram bot, LinkedIn CMO, email service
│   ├── templates/           # 6 resume variants + cover letter formatter
│   ├── filters/             # Career gate, red flag detection
│   ├── core/                # Config, models, candidate profile
│   └── utils/               # Caching, rate limiting, Claude helper, retry logic
├── docs/                    # System documentation, career strategy, integration guides
├── autonomous_data/         # Runtime data (resumes, caches, logs) — gitignored
├── web_server.py            # FastAPI entry point (systemd service)
├── .env.example             # All configuration options with descriptions
└── requirements.txt         # Python dependencies
```

---

## How I Built This

**Role:** Solo architect, engineer, and product designer.

I built VibeJobHunter as part of [AIdeazz](https://aideazz.xyz) — an ecosystem of 12+ production AI systems I shipped solo after relocating to Panama with zero technical background.

**My approach:** Human-AI collaborative development using Cursor + Claude + GPT to design, generate, and iterate production code. I combine 7 years of executive product judgment (Deputy CEO, Chief Legal Officer) with hands-on engineering execution.

**Key engineering decisions:**
- **Async-first architecture** — all 8 job sources fetch in parallel using `asyncio`, keeping cycle time under 5 minutes
- **Domain-match filtering** — pre-scoring filter that drops obviously wrong roles (DevOps, QA, DBA) before burning Claude API tokens
- **Additive source integration** — each new job source (like Dice MCP) plugs in without touching existing scrapers
- **Graceful degradation** — if any source fails, the engine continues with remaining sources
- **File-based persistence** — JSONL logs + JSON caches survive service restarts without database migration complexity

---

## Other Products in the AIdeazz Ecosystem

| Product | What It Does | Status |
|---------|-------------|--------|
| [EspaLuz](https://espaluz-ai-language-tutor.lovable.app) | Bilingual AI tutor with emotional memory (WhatsApp/Telegram) | Live subscriptions, 19 countries |
| CTO AIPA | AI engineering ops: PR review, voice-to-action, daily audio Sprint Briefing (~$2/mo AWS) | Live 24/7 |
| CMO AIPA | AI Marketing & RevOps: GEO/AEO content, LLM buying-intent lead gate, Bright Data enrichment → HubSpot | Live 24/7 |
| [Building in Public Podcast](https://podcast.aideazz.xyz) | Voice note → blog + social + published episode (Spotify, YouTube, Listen Notes, Podcast Index) | Live |
| [ATUONA](https://atuona.xyz) | Multimodal creative AI → NFT publishing | Live |

**Portfolio:** [aideazz.xyz](https://aideazz.xyz) · 12+ production systems, 12 active repos

---

## Documentation

- [`docs/SYSTEM_DOCUMENTATION.md`](docs/SYSTEM_DOCUMENTATION.md) — Full technical documentation with workflow diagrams
- [`docs/CAREER_FOCUS.md`](docs/CAREER_FOCUS.md) — Target roles, scoring criteria, company strategy
- [`docs/CTO_CMO_INTEGRATION_SUMMARY.md`](docs/CTO_CMO_INTEGRATION_SUMMARY.md) — How the AI Co-Founders integrate

---

## Author

**Elena Revicheva** — AI Product Engineer & Founder

Building personal AI systems using human-AI collaborative development.

- [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [AIdeazz](https://aideazz.xyz)
- Based in Panama | Bilingual EN/ES | Remote worldwide

---

## License

MIT — Use freely. If you build your own job hunting engine, I'd love to hear about it.

---

*Last updated: June 10, 2026*
