# ELENA REVICHEVA

**Executive-Turned-AI-Builder | 7yr Board-Level Leadership + 9 Production AI Systems**

Panama (UTC-5) | Remote Worldwide
aipa@aideazz.xyz | +507 616 66 716
LinkedIn: linkedin.com/in/elenarevicheva | GitHub: github.com/ElenaRevicheva | Portfolio: aideazz.xyz/portfolio

---

## PROFESSIONAL SUMMARY

Seven years as Deputy CEO running large-scale digital infrastructure programs at the board level — then pivoted to building AI systems hands-on. Since 2025: designed, deployed, and operate 9 production AI agents on Oracle Cloud at $0/month infrastructure cost, using AI-assisted development workflows (Cursor, Claude Code).

The combination is rare: I can architect an LLM pipeline, deploy it to production, and explain it to a CEO and a developer in the same conversation. I build for outcomes, not demos — every system listed below is live, serving real users, 24/7.

---

## KEY RESULTS

- **9 production AI systems** running 24/7 on a single Oracle Cloud VM — $0/month infra (startup credits + Always Free tier)
- **Autonomous job discovery pipeline** processing 1,900+ listings → 250+ tailored applications + 140+ founder outreach messages via Resend
- **76/24 multi-model routing** — 76% requests to cost-optimized models (Groq Llama), 24% to high-capability models (Claude) for critical paths. Deliberate cost/quality tradeoff, not default.
- **AI Marketing Engine (GEO + SEO)** — built a system that makes a business discoverable by both Google and AI assistants (ChatGPT, Perplexity, Claude): JSON-LD structured data, automated daily blog publishing with GSC gap topic selection, Dev.to cross-posting for DA 90+ backlinks, UTM attribution pipeline, AI-powered lead triage with urgency scoring, and automated cold outreach — all running autonomously
- **3-layer automated resilience** — health cron (every 5 min) + systemd/PM2 restart policies + OCI keepalive. Systems recover from failures without human intervention.
- **Bilingual AI tutor with paying subscribers** — WhatsApp + Telegram, persistent memory, voice transcription, OCR, PayPal subscriptions (early traction, honest: very early stage)

---

## CORE SKILLS

**LLM Systems & Agents**
Claude (Opus, Sonnet, Haiku), OpenAI GPT-4o, Groq (Llama 3.3 70B, Whisper), multi-model routing, tool calling, multi-step agent orchestration, prompt engineering, structured outputs, persistent memory systems, conversation context management, model fallback chains

**AI-Assisted Development**
Cursor, Claude Code — daily workflow for rapid build/deploy/iterate cycles. Not a gap to hide — this is how production AI gets built fast in 2026.

**GEO + SEO Marketing Automation**
JSON-LD schema markup (Organization, Person, FAQPage), AI bot permissions (GPTBot, ClaudeBot, PerplexityBot), noscript static content for AI crawlers, sitemap generation, canonical/hreflang management, Google Search Console, GA4, automated content publishing with GSC gap topic selection, UTM attribution, reCAPTCHA Enterprise

**Programming**
TypeScript, Python, JavaScript, SQL

**Backend & APIs**
Node.js, Express, FastAPI, REST APIs, webhook architectures, asynchronous workflows, GitHub API (Octokit), Telegram Bot API (Grammy), WhatsApp Business API

**Databases & Infrastructure**
Oracle Autonomous Database 26ai (mTLS, thick mode), PostgreSQL, Oracle Cloud Infrastructure (OCI), PM2, systemd, IPFS/4everland hosting

**Multi-Modal AI**
Replicate (Flux Pro — image generation), Luma Labs (Dream Machine — video), Runway ML (Gen-3), Whisper (voice transcription), OCR — full text→image→video→publish pipeline in production

**Integrations**
GitHub webhooks, Telegram, WhatsApp, PayPal Subscriptions, Resend (transactional email), Hunter.io, Google Places API, Make.com, Buffer, Twitter/X API

**Eval & Quality**
117-test eval harness (unit + integration + golden-set layers), $0 API cost, 0.52s runtime. Deterministic + LLM hybrid analysis for code review pipeline.

---

## PRODUCTION AI SYSTEMS

### CTO AIPA — AI Code Review & Technical Co-Founder
Automated GitHub PR/push review system with deterministic security analysis + LLM-generated feedback.
- GitHub webhooks → diff fetch → security/complexity/architecture scan → model routing (Claude for critical, Groq for standard) → GitHub comment + Oracle persistence
- Groq → Claude Haiku fallback chain prevents shared-process crashes on rate limits
- Telegram + HTTP API interface for on-demand technical Q&A across all repos
- **Tech:** TypeScript, Node.js, Express, Claude, Groq, Oracle DB, GitHub API, PM2

### AI Marketing Engine — GEO + SEO Automation (Phases 1–5)
Full-stack marketing system that makes AIdeazz discoverable by Google AND AI assistants.
- **Phase 1 (GEO/SEO):** 3 JSON-LD schemas, noscript block for AI crawlers, sitemap (11 URLs with live Hashnode slugs), robots.txt with AI bot permissions, www→apex 301 redirect, hreflang EN/ES, GA4 analytics
- **Phase 2 (Content):** Daily automated blog publishing via Claude → Hashnode API → Dev.to cross-post (DA 90+ canonical backlink). GSC gap topic selection picks the keyword with least current traffic. Oracle content_log tracks every post.
- **Phase 3 (Attribution):** Inquiry form with UTM capture → Oracle business_leads → Resend email notification → reCAPTCHA Enterprise verification. End-to-end from form submit to team inbox.
- **Phase 4 (Outreach):** Automated cold email pipeline — YC companies + Google Places + document ingestion → Hunter.io → Claude-generated emails → Resend with honest send tracking. Daily cap enforced.
- **Phase 5 (Lead Triage):** AI classification of inbound inquiries + outreach replies → urgency scoring (1–5) → web dashboard + Telegram alerts. Groq → Haiku → optional Sonnet refine.
- **Tech:** TypeScript, Python, Node.js, React, Oracle DB, Claude, Groq, Resend, Google Places API, Hunter.io, GSC API, GA4

### VibeJobHunter — Autonomous Job Discovery & Outreach Pipeline
End-to-end job search automation: scrape → filter → score → apply → outreach.
- Hard-gate filtering (company size, role category, salary floor) + AI match scoring (60+ threshold)
- ATS auto-apply (Greenhouse, Lever, Ashby via Playwright) + founder email outreach via Resend
- Voice-enabled Telegram interface for on-demand job shortlisting (Whisper STT)
- 117-test eval harness for scoring calibration
- **Tech:** Python, FastAPI, Claude, Groq Whisper, Playwright, Oracle Cloud, Telegram Bot API

### EspaLuz — Bilingual AI Language Tutor (Paying Subscribers)
WhatsApp + Telegram AI tutor with persistent per-user memory, voice transcription, OCR, and PayPal subscription billing.
- Multi-modal: text + voice + image input → personalized language coaching
- Persistent conversation memory in Oracle DB — tutor remembers each student's level and progress
- PayPal webhook integration for subscription management
- **Tech:** Python, GPT-4o, Whisper, Oracle DB, WhatsApp Business API, Telegram Bot API, PayPal

### Atuona Creative AI — Multi-Modal Creative Agent
AI agent for poetry, visual storytelling, and short film production. Persistent emotional/creative state.
- Full LLM → image → video pipeline: Claude Opus generates text → Flux Pro creates visuals → Luma/Runway produces video → automated social formatting → blockchain publishing
- 48+ NFTs published on Polygon via Thirdweb
- Persistent creative memory (moods, metaphors, character insights) saved to JSON state file
- **Tech:** TypeScript, Claude Opus, Replicate, Luma Labs, Runway, Telegram Bot API, Thirdweb, Polygon

### Additional Live Systems
- **CMO AIPA** — Automated LinkedIn/Instagram content publishing synced with technical releases (Python, Claude, Make.com, Buffer)
- **ALGOM Alpha** — AI crypto education bot on X/Twitter with market analysis (Node.js, ElizaOS)
- **OpenClaw Vibejob Shortlist** — Voice-enabled Telegram bot for YC AI company shortlisting

---

## EXECUTIVE BACKGROUND (2011–2018)

**Deputy CEO & Chief Legal Officer** — JSC "E-GOV OPERATOR" | Russia | 2011–2018
- Led large-scale public-sector digital transformation programs at board level — 7 years
- Managed cross-functional teams (IT, legal, compliance) in highly regulated environment
- This is why I can explain AI systems to non-technical stakeholders: I've sat in the room where decisions get made

**Deputy CEO (Business Development)** — Fundery LLC (Fintech) | Russia | 2017–2018
- ICO compliance, investor relations, blockchain launch strategy

---

## EDUCATION

| Program | Institution | Year |
|---------|------------|------|
| Polkadot Blockchain Academy (PBA-X Wave 3) | Online | 2025 |
| MA Social Psychology | Penza State University, Russia | 2018 |
| Presidential Program for Executive Management | RANEPA, Moscow (incl. internship in Bergen, Norway) | 2015 |

---

## LANGUAGES

Russian (Native) · English (Fluent) · Spanish (Intermediate) · French (Elementary)

---

## TARGET ROLES

Fractional AI Builder / Consultant · Founding AI Hire (Pre-Seed/Seed) · AI Automation Specialist · Internal AI Tools Builder · AI Integration Engineer · AI Ops / AI Program Manager
