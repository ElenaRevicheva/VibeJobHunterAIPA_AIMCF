# ELENA REVICHEVA

**Applied AI Engineer | I Build AI Systems That Work in Production**

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portfolio](https://aideazz.xyz/card)

Costa del Este, Juan Díaz, Panama City | Remote Worldwide | UTC-5

---

## PERSONAL INFORMATION

| | |
|---|---|
| **Date of Birth** | December 11, 1985 |
| **Nationality** | Russian |
| **Panama Residence** | Carné de Residente Permanente |
| **Work Permit** | Type 4B |
| **Driver's License** | Type C |
| **Location** | Costa del Este, Juan Díaz, Panama City |

---

## HOW I BUILD

I build using **Cursor IDE and Claude Code as daily primary tools** — an AI-augmented workflow that produced 12+ production systems in under a year, at a fraction of what a traditional team would cost. Every design decision and system outcome is mine; the AI compresses the time it takes to execute. This approach is deliberate and modern, not a shortcut.

**Note for hiring teams:** If your process includes a proctored coding test or live whiteboard session, I'll say so upfront — that's not my workflow. If what matters is production systems that run, I can show you mine.

---

## PROFESSIONAL SUMMARY

In the past 12 months, I built and shipped 12 AI products — as a solo founder, without a team. The equivalent of what most companies would staff 4–5 engineers to do, at under 1% of the cost.

These are not demos or prototypes. They are systems running 24/7: a job search engine that applies autonomously, a language tutor that remembers its students, a code review agent watching 12 repositories, a daily voice briefing delivered every morning at 8AM. Real users. Real payments. Real infrastructure.

Before AI, I spent 7 years as Deputy CEO and Chief Legal Officer running large-scale digital programs for the Russian government — enterprise technology, board-level decisions, cross-functional teams. I know how to think at a systems level and how to talk to decision-makers, not just developers.

**What I'm looking for:** A role where I can build AI products that matter — as a founding engineer, applied AI engineer, or fractional builder.

---

## WHAT I'VE BUILT — KEY RESULTS

| | |
|---|---|
| **12+ AI products in production** | Running autonomously, 24/7, on $0/month cloud infrastructure |
| **99% cost reduction** | Delivered solo what would cost ~$900K with a traditional team |
| **Users in 19 countries** | Live subscription payments via PayPal |
| **1,900+ job listings processed** | By an AI that applies, follows up, and knows when to ask a human |
| **~$2/month AWS bill** | For a serverless system that reads 12 products and delivers a daily voice briefing |
| **$0.03 per quality check** | Automated testing system that catches problems before they reach users |

---

## PROFESSIONAL EXPERIENCE

### Applied AI Engineer & Founder
**AIdeazz.xyz** | Panama / Remote | 2025 – Present

---

### VibeJobHunter — Autonomous Job Search System

**What it does:** Finds jobs, scores them by fit, applies automatically, and pauses to ask for human approval only when a decision is genuinely borderline. No manual searching. No repetitive form-filling. Just results.

**Results:** Processed 1,900+ job listings. Generated 250+ tailored applications and 140+ outreach messages. Built with a quality-testing layer — 131 automated checks run before every update, including an AI that independently audits the scoring logic to catch regressions.

**How it works (for the technical reader):** LangGraph stateful pipeline (7-node StateGraph) with SQLite session persistence and human-in-the-loop interrupt for borderline scores. 4-layer evaluation harness: keyword scoring, bias compensation, 22-job golden set, and Claude Haiku as independent LLM judge (≥75% agreement threshold). Multi-ATS form automation via Playwright. Outreach via Resend API.

*Tech: Python · LangGraph · LangChain · Claude · Playwright · SQLite · Resend · Telegram Bot API*

---

### EspaLuz — AI Language Tutor (Paying Users, 19 Countries)

**What it does:** A Spanish/English tutor on WhatsApp and Telegram that actually remembers its students. Instead of starting from scratch every session, it recalls past conversations and surfaces relevant context automatically — the way a good human tutor would. Students pay a monthly subscription.

**Results:** Live in 19 Spanish-speaking countries. PayPal subscriptions active. Deployed on both WhatsApp and Telegram from a shared codebase.

**How it works (for the technical reader):** 2-layer memory — LangChain conversation history (exact last 5 turns) + semantic search over full history via pgvector (OpenAI embeddings, cosine similarity > 0.75). Both layers injected into the AI's system prompt before every reply. Separate session namespaces per platform.

*Tech: Python · GPT-4 · LangChain · pgvector · OpenAI embeddings · Whisper · WhatsApp Business API · Railway*

---

### CTO AIPA — AI Technical Partner

**What it does:** An AI system that watches all 12 products around the clock — reviewing code changes, flagging security risks, and every morning at 8AM delivering a spoken audio briefing to my phone: what changed overnight, what I told myself to do yesterday, what needs attention today.

**Results:** Every code change across 12 repositories reviewed automatically. Every morning briefing delivered on schedule. Voice notes spoken at night become part of the next morning's audio. Full feedback loop, fully autonomous.

**How it works (for the technical reader):** GitHub webhook → security + complexity analysis → model routing (Claude for critical, Groq for standard). Voice input → Whisper transcription → Oracle database. Sprint Briefing Agent on AWS Lambda: EventBridge cron at 8AM Panama → reads GitHub + Oracle diary/tasks via S3 wallet (thin-mode Oracle connector) → Groq clusters signals → Claude writes narrative → OpenAI TTS renders audio → Telegram delivery. ~$2/month.

*Tech: TypeScript · Node.js · Claude · Groq · OpenAI TTS · Oracle Cloud (mTLS) · AWS Lambda · AWS EventBridge · AWS S3 · GitHub API · PM2*

---

### AI Marketing Agent (CMO AIPA)

**What it does:** Writes and publishes bilingual (English/Spanish) content daily — strategy-aware, not templated. When a product ships a new feature, the marketing agent picks it up and posts about it automatically.

*Tech: Python · FastAPI · Claude · Make.com · Buffer · Railway*

---

### Additional Products

**Atuona Creative AI** (atuona.xyz) — AI creative pipeline: text → image → video → blockchain publishing. *Tech: TypeScript · Node.js · Claude Opus · Replicate · Luma Labs · Thirdweb · Polygon*

**ALGOM Alpha** — AI crypto education bot on X (@reviceva). *Tech: Node.js · ElizaOS · CCXT · Twitter API*

---

### Operational Co-Founder
**OmniBazaar** (Decentralized Marketplace) | Remote | 2024 – 2025
- Structured DAO LLC (Marshall Islands); designed governance, tokenomics, DAO operating agreements

### Deputy CEO and Chief Legal Officer
**JSC "E-GOV OPERATOR"** | Russia | 2011 – 2018
- Led large-scale digital transformation programs for Russian regional government at board level
- Managed cross-functional teams (IT, legal, compliance); enterprise technology programs

### Deputy CEO (Business Development)
**Fundery LLC** (Fintech/Blockchain) | Russia | 2017 – 2018
- ICO compliance, investor relations, regulatory documentation, blockchain launch strategy

---

## TECHNICAL SKILLS

*(For those who want the full stack)*

**AI & Agents:** Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B, Whisper) · LangGraph · LangChain · Semantic RAG (pgvector + OpenAI embeddings) · model routing · tool calling · multi-step orchestration · prompt engineering

**Evaluation:** 4-layer harness · LLM-as-judge · golden-set testing · regression detection

**Languages:** Python · TypeScript · JavaScript · SQL

**Backend:** Node.js · Express · FastAPI · Flask · REST APIs · async workflows · webhooks

**Frontend:** React 18 + TypeScript + Vite · Tailwind CSS · Framer Motion

**Infrastructure:** PostgreSQL (pgvector) · Oracle Autonomous Database (mTLS) · Oracle Cloud (OCI) · AWS Lambda · AWS EventBridge · AWS S3 · Railway · Supabase · Docker · PM2 · Ubuntu

**Integrations:** GitHub API · Telegram Bot API · WhatsApp Business API · PayPal · Twitter/X · Playwright · Resend · Make.com · Buffer

**Web3:** Polygon · Thirdweb · IPFS · Smart Contracts

---

## EDUCATION AND CERTIFICATIONS

- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025
- **How-To-DAO Cohort Graduate** | 2025
- **MA Social Psychology** | Penza State University | 2018 | Russia
- **Blockchain Regulation** | MGIMO | 2017 | Moscow
- **Presidential Program for Executive Management** | RANEPA | 2015 | Moscow
- **Internship** | Nyskapingsparken Innovation Park | Bergen, Norway

---

## LANGUAGES

Russian (Native) | English (Fluent) | Spanish (Intermediate) | French (Elementary)

---

## TARGET ROLES

Applied AI Engineer · AI Product Engineer · Founding AI Engineer · Internal AI Tools Builder · Fractional AI Consultant ($40–70/hr)

Open to: Full-time · Part-time · Contract · Remote

---

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram) | 🔗 [aideazz.xyz/card](https://aideazz.xyz/card)
