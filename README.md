# 🤖 VibeJobHunter + AI Marketing Co-Founder

**Autonomous Job Hunting Engine + AI Co-Founder for Personal Branding**

> Built by Elena Revicheva with AI Co-Founders (not just AI tools!)

[![Deployed on Railway](https://img.shields.io/badge/Deployed-Railway-blueviolet)](https://railway.app/)
[![AI Powered](https://img.shields.io/badge/AI-Claude%20Sonnet-blue)](https://anthropic.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What This Does

**Two autonomous systems running 24/7 on Railway:**

### 1. 🔍 Autonomous Job Hunting Engine
- **Scrapes 3000+ jobs/hour** from ATS APIs (Greenhouse, Lever, Ashby)
- **AI-powered scoring** via Claude (matches to your profile)
- **Auto-applies to Greenhouse** with Playwright browser automation
- **Handles email verification** (reads codes from Zoho Mail IMAP)
- **Founder outreach** - finds contacts, generates personalized messages
- **Telegram notifications** - real-time updates on applications

### 2. 🧠 AI Marketing Co-Founder (LinkedIn CMO)
- **TRUE AI Co-Founder** with strategic thinking & learning
- **Daily LinkedIn posts** via Claude API → Make.com
- **Bilingual content** (English/Spanish)
- **Performance tracking** & strategy adaptation
- **Zero manual work** - posts at 21:30 UTC daily

---

## ✅ What's Actually Working (December 2025)

| Feature | Status | Details |
|---------|--------|---------|
| **ATS Job Scraping** | ✅ LIVE | 130+ companies (Greenhouse, Lever, Ashby) |
| **AI Job Scoring** | ✅ LIVE | Claude-powered with keyword bonuses |
| **Greenhouse Auto-Apply** | ✅ LIVE | Form filling + email verification |
| **Resume Selection** | ✅ LIVE | 3 PDF variants auto-selected by role |
| **Founder Outreach** | ✅ LIVE | Email finding + personalized messages |
| **Email Service** | ✅ LIVE | Resend API from verified domain |
| **LinkedIn CMO** | ✅ LIVE | Daily posts via Make.com |
| **Telegram Bot** | ✅ LIVE | Real-time notifications + commands |
| **Database Tracking** | ✅ LIVE | SQLite for all applications |

---

## 📊 Current Performance

```
HOURLY AUTONOMOUS CYCLE:
├─ Jobs scraped:      ~3000 (from 130+ company APIs)
├─ After career gate: ~700 (22% pass rate)
├─ Scored 60+:        ~5-10 (qualified for auto-apply)
└─ Applications/day:  3-5 (quality-capped)

TARGET ROLES:
├─ Founding Engineer
├─ Senior/Staff AI Engineer
├─ AI Solutions Architect
└─ Principal Engineer

ATS PLATFORMS:
├─ Greenhouse: 73 companies (~2000 jobs)
├─ Ashby: 37 companies (~900 jobs)
├─ Lever: 19 companies (~150 jobs)
└─ HN Who's Hiring, RemoteOK
```

---

## 🚀 Quick Start

### Option A: Deploy on Railway (Recommended)

```bash
# 1. Clone and setup
git clone https://github.com/ElenaRevicheva/VibeJobHunterAIPA_AIMCF.git
cd VibeJobHunterAIPA_AIMCF
cp .env.example .env

# 2. Configure environment variables (see below)

# 3. Deploy
railway up
```

### Option B: Run Locally

```bash
pip install -r requirements.txt
python -m src.main autonomous --interval 1
```

---

## ⚙️ Configuration

### Required Environment Variables

```bash
# AI (Required)
ANTHROPIC_API_KEY=sk-ant-...

# Email Service (Required for applications)
RESEND_API_KEY=re_...
FROM_EMAIL=Your Name <you@yourdomain.com>

# Applicant Info
APPLICANT_FIRST_NAME=Your
APPLICANT_LAST_NAME=Name
APPLICANT_EMAIL=you@yourdomain.com
APPLICANT_PHONE=+1-555-555-5555
APPLICANT_LINKEDIN=https://linkedin.com/in/yourprofile

# Zoho Mail (for reading verification codes)
ZOHO_EMAIL=you@yourdomain.com
ZOHO_APP_PASSWORD=xxxxxxxxxxxx  # 12-char app-specific password

# Telegram (Optional but recommended)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# LinkedIn CMO (Optional)
MAKE_WEBHOOK_URL_LINKEDIN=https://hook.us2.make.com/...

# ATS Settings
ATS_DRY_RUN=false
ATS_SUBMISSION_ENABLED=true
```

---

## 🏗️ Architecture

```
Railway (24/7 Autonomous)
    │
    ├─── Job Hunting Engine (Hourly)
    │    ├─ Scrape ATS APIs (Greenhouse/Lever/Ashby)
    │    ├─ Filter through career gate
    │    ├─ Score with Claude AI
    │    ├─ Auto-apply (score ≥ 60)
    │    │   ├─ Research company (Claude)
    │    │   ├─ Select resume variant
    │    │   ├─ Fill Greenhouse form (Playwright)
    │    │   ├─ Handle email verification (IMAP)
    │    │   └─ Submit application
    │    ├─ Founder outreach (score ≥ 58)
    │    └─ Notify via Telegram
    │
    └─── LinkedIn CMO (Daily 21:30 UTC)
         ├─ Generate content (Claude)
         ├─ Post via Make.com webhook
         └─ Track performance
```

---

## 📁 Key Files

```
src/
├── autonomous/
│   ├── orchestrator.py          # 🧠 Main brain - hourly cycles
│   ├── job_monitor.py           # 🔍 Fetches from all sources
│   ├── ats_submitter.py         # 🚀 Greenhouse form submission
│   ├── greenhouse_email_verifier.py  # 📧 IMAP verification
│   ├── company_researcher.py    # 🔬 Claude company research
│   └── founder_finder_v2.py     # 👤 Founder contact finding
│
├── scrapers/
│   └── ats_scraper.py           # 🕷️ Greenhouse/Lever/Ashby APIs
│
├── agents/
│   └── job_matcher.py           # 🎯 AI-powered scoring
│
├── templates/
│   └── resume_selector.py       # 📄 3 resume variants
│
└── notifications/
    ├── linkedin_cmo_v4.py       # 📣 Daily LinkedIn posting
    └── telegram_notifier.py     # 📱 Telegram notifications

autonomous_data/
├── resumes/                     # PDF resume variants
│   ├── founding_engineer.pdf
│   ├── senior_ai_engineer.pdf
│   └── ai_solutions_architect.pdf
└── vibejobhunter.db            # SQLite database
```

**Full documentation:** See `SYSTEM_DOCUMENTATION.md`

---

## 🎯 Scoring Thresholds

```python
AUTO_APPLY_THRESHOLD = 60    # Score ≥ 60 → auto-submit application
OUTREACH_THRESHOLD = 58      # Score ≥ 58 → founder outreach
REVIEW_THRESHOLD = 55        # Score ≥ 55 → save for review
MAX_DAILY_APPLICATIONS = 5   # Quality over quantity
```

---

## 🧠 AI Marketing Co-Founder

The LinkedIn CMO is a **TRUE AI Co-Founder** (not just automation):

| Capability | Implementation |
|------------|----------------|
| **Creative Generation** | Claude API generates unique content daily |
| **Strategic Thinking** | Analyzes market trends, adapts messaging |
| **Bilingual** | English/Spanish content alternating |
| **Autonomous** | Runs without human input |
| **Learning** | Tracks performance, improves over time |

**Posts daily at 21:30 UTC via Make.com → LinkedIn**

---

## 🎓 Tech Stack

| Layer | Technology |
|-------|------------|
| **AI/LLM** | Claude Sonnet 4 (Anthropic) |
| **Backend** | Python 3.11, FastAPI, asyncio |
| **Browser Automation** | Playwright (Greenhouse forms) |
| **Email** | IMAP (Zoho), Resend API |
| **Database** | SQLite |
| **Hosting** | Railway (24/7) |
| **Social Posting** | Make.com webhooks |
| **Notifications** | Telegram Bot API |

---

## 📈 Expected Results

**Job Hunting (Autonomous):**
- 3000+ jobs scraped per cycle
- 3-5 quality applications per day
- Focus on AI/ML founding/senior roles

**LinkedIn CMO:**
- 7 posts/week (daily)
- Bilingual reach (EN/ES)
- Zero manual work

---

## 🚀 Portfolio

**Built by Elena Revicheva:**
- 11 AI products in 10 months (solo)
- 7 live AI agents with paying users
- Ex-CEO/CLO turned AI founder

**🤖 Live AIPAs:**
1. **VibeJobHunter** (this repo) - Job automation + LinkedIn CMO
2. **ALGOM Alpha** - Web3 Trading AI on [X](https://x.com/reviceva)
3. **EspaLuz WhatsApp** - AI language tutor: [wa.me/50766623757](https://wa.me/50766623757)
4. **EspaLuz Telegram** - AI tutor: [t.me/EspaLuzFamily_bot](https://t.me/EspaLuzFamily_bot)
5. **EspaLuz Influencer** - Marketing bot: [t.me/Influencer_EspaLuz_bot](https://t.me/Influencer_EspaLuz_bot)

**🌐 Live Products:**
- [AIdeazz.xyz](https://aideazz.xyz) - AI Agents Portfolio
- [EspaLuz Web](https://espaluz-ai-language-tutor.lovable.app) - SaaS Language Learning
- [ATUONA](https://atuona.xyz) - NFT Poetry Gallery

---

## 👤 Author

**Elena Revicheva**  
AI-First Engineer & Founder

- 🌍 Panama City, Panama (Remote globally)
- 💼 Open to: Founding Engineer roles
- 📧 aipa@aideazz.xyz
- 🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [X](https://x.com/reviceva)

---

## 📝 License

MIT License - Use freely for your job hunt!

---

## 🔗 Links

- **Production:** https://vibejobhunter-production.up.railway.app
- **API Docs:** https://vibejobhunter-production.up.railway.app/docs
- **Full System Docs:** `SYSTEM_DOCUMENTATION.md`
- **Strategy:** `CAREER_FOCUS.md`

---

**Built with** ❤️ **by Elena + AI Co-Founders**

**Status:** ✅ LIVE - Autonomous applications running since December 2025

*Last updated: December 21, 2025*
