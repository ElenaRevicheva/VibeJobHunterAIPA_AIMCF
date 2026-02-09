# VibeJobHunter — Autonomous AI Job Hunting Engine

**An AI system that discovers, scores, and applies to jobs autonomously — while an AI Marketing Co-Founder builds your personal brand on LinkedIn.**

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

- **Discovers** jobs from 8 sources every hour (218+ company APIs + Dice MCP + YC + RemoteOK + more)
- **Scores** each job against your profile using Claude AI (100-point system with domain-match filtering)
- **Auto-applies** to high-scoring roles via ATS form submission (Greenhouse, Lever, Ashby, Workable)
- **Generates personalized outreach** to founders at borderline companies
- **Follows up** automatically after 5 days of no response
- **Posts daily LinkedIn content** via an AI Marketing Co-Founder (bilingual EN/ES)
- **Reports everything** to you via Telegram bot with full interactive controls

---

## Architecture

```
Oracle Cloud (24/7 systemd service)
│
├── Job Hunting Engine (runs every hour)
│   │
│   ├── 1. DISCOVER ──────────────────────────────────
│   │   ├── ATS APIs: 218 companies (Greenhouse, Lever, Ashby, Workable)
│   │   ├── Dice MCP: 8 keyword queries via Model Context Protocol
│   │   ├── YC Work at a Startup (Algolia search)
│   │   ├── RemoteOK, Wellfound, WWR, AI Jobs, HN
│   │   └── ~50-80 new jobs per cycle
│   │
│   ├── 2. FILTER & SCORE ────────────────────────────
│   │   ├── Domain-match filter (drops DevOps, QA, DBA, etc.)
│   │   ├── Claude AI scoring (100 pts: AI Product 25, Autonomy 25,
│   │   │   Full-Stack 20, Business 15, Bilingual 5, Web3 10)
│   │   ├── YC company bonus: +15 pts
│   │   └── Deduplication via seen-jobs cache
│   │
│   ├── 3. ROUTE ─────────────────────────────────────
│   │   ├── Score ≥ 60 → AUTO-APPLY (ATS form submission)
│   │   ├── Score 50-59 → FOUNDER OUTREACH (AI message generation)
│   │   ├── Score 40-49 → REVIEW QUEUE
│   │   └── Score < 40 → DISCARD
│   │
│   ├── 4. APPLY ─────────────────────────────────────
│   │   ├── Smart resume selection (6 role-specific variants)
│   │   ├── AI cover letter generation (Claude)
│   │   ├── ATS form filling + PDF upload
│   │   └── Email verification handling (Zoho IMAP)
│   │
│   └── 5. FOLLOW UP ─────────────────────────────────
│       ├── Track all outreach in JSONL log
│       ├── Auto-remind after 5 days, escalate at 8 days
│       └── Daily outreach cap: 2 messages/day
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
| **AI/LLM** | Claude Sonnet 4 (Anthropic) | Job scoring, cover letters, content generation, company research |
| **Backend** | Python 3.11, FastAPI, asyncio | Async job fetching from 8+ sources in parallel |
| **Job Sources** | Dice MCP, Greenhouse/Lever/Ashby/Workable APIs, YC Algolia | Structured API access, no scraping needed |
| **Email** | Resend API, Zoho IMAP, Hunter.io | Sending, verification code reading, email discovery |
| **Database** | SQLite | Application tracking, deduplication, scoring history |
| **Infrastructure** | Oracle Cloud, systemd | Always-on, auto-restart, zero monthly cost |
| **Marketing** | Make.com webhooks, Claude | Automated LinkedIn content pipeline |
| **Notifications** | Telegram Bot API | Real-time interactive control panel |

---

## What's Working (February 2026)

| Feature | Status | Details |
|---------|--------|---------|
| ATS Job Discovery | **LIVE** | 218 companies across 4 ATS platforms |
| Dice MCP Integration | **LIVE** | 8 targeted keyword queries, ~55 jobs/cycle |
| AI Job Scoring | **LIVE** | Claude-powered 100-point scoring + domain filter |
| Auto-Apply (Greenhouse) | **LIVE** | Form filling, resume upload, email verification |
| Founder Outreach | **LIVE** | AI-generated personalized LinkedIn messages |
| Follow-Up Engine | **LIVE** | Automatic reminders at day 5 and day 8 |
| Smart Resume Selection | **LIVE** | 6 role-specific resume variants |
| LinkedIn CMO | **LIVE** | Daily bilingual posts at 10:10 AM Panama |
| Telegram Bot | **LIVE** | Interactive menu with real-time stats |
| Outreach Daily Cap | **LIVE** | Max 2 outreach messages per day |
| Seen Jobs Dedup | **LIVE** | 30-day TTL cache prevents re-processing |

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

I built VibeJobHunter over 3 months as part of [AIdeazz](https://aideazz.xyz) — an ecosystem of 8 AI products I shipped solo in 10 months after relocating to Panama in 2022 with zero technical background.

**My approach:** Human-AI collaborative development using Cursor + Claude + GPT to design, generate, and iterate production code. I combine 7 years of executive product judgment (Deputy CEO, Chief Legal Officer) with hands-on engineering execution.

**Key engineering decisions:**
- **Async-first architecture** — all 8 job sources fetch in parallel using `asyncio`, keeping cycle time under 5 minutes
- **Domain-match filtering** — pre-scoring filter that drops obviously wrong roles (DevOps, QA, DBA) before burning Claude API tokens
- **Additive source integration** — each new job source (like Dice MCP) plugs in without touching existing scrapers
- **Graceful degradation** — if any source fails, the engine continues with remaining sources
- **File-based persistence** — JSONL logs + JSON caches survive service restarts without database migration complexity

---

## Other Products in the AIdeazz Ecosystem

| Product | What It Does | Users |
|---------|-------------|-------|
| [EspaLuz](https://espaluz-ai-language-tutor.lovable.app) | Bilingual AI tutor with emotional memory (WhatsApp/Telegram) | Live subscriptions, 19 countries |
| CTO AIPA | Autonomous AI Co-Founder for technical decisions | Internal tool |
| CMO AIPA | AI Marketing Co-Founder (LinkedIn + Instagram) | Runs daily in this repo |
| [ATUONA](https://atuona.xyz) | NFT Poetry Gallery | Live |

**Portfolio:** [aideazz.xyz](https://aideazz.xyz)

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

*Last updated: February 9, 2026*
