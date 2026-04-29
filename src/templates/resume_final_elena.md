# ELENA REVICHEVA

**AI Product Engineer | Applied LLM Systems | AI-Assisted Software Development**

Panama City, Panama | Remote Worldwide | On-site | Hybrid

📧 aipa@aideazz.xyz | elena.revicheva2016@gmail.com | 📱 +507 616 66 716 (WhatsApp/Telegram)
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portfolio](https://aideazz.xyz/card)
🌐 ENS: aideazz.eth

---

## SUMMARY

Executive-turned-AI-builder. Former Deputy CEO and Chief Legal Officer in E-Government (Russia, 2011–2018) — 7 years running large-scale digital infrastructure programs at board level. Since 2025, shipped 12+ live AI products and agents as solo founder of AIdeazz.xyz.

Primary strength is **AI-augmented development**: using Cursor, Claude Code, and Groq to design, generate, and iterate production code under clear human intent, constraints, and validation — not traditional manual coding. This is how one person ships 9 autonomous AI agents and manages 12 active repositories. Can talk to a CEO and a developer in the same conversation.

Seeking roles as **AI Product Engineer**, **Applied LLM Engineer**, **Founding AI Engineer**, or **Fractional AI Consultant/Builder**.

---

## HOW I BUILD

**I develop exclusively using AI-augmented workflows — Cursor IDE and Claude Code as primary tools.** This is not a limitation; it is a deliberate, modern approach that produced 12+ production AI systems currently running in the wild. Every architecture decision, system design, and production outcome is mine — the AI compresses execution time, the judgment is entirely human. If your hiring process includes a proctored coding assessment or live whiteboard test, I will say so directly rather than go through a process designed for a different kind of engineer. If production systems matter more than whiteboard performance, I can show you mine in detail.

---

## KEY ACHIEVEMENTS

• **12+ live AI products and agents** operating autonomously in production — solo-built using AI-augmented development (Cursor + Claude Code)
• **99% cost reduction** vs traditional multi-role development teams ($900K → <$15K)
• **Full two-way AI memory loop**: voice notes into CTO bot at night → spoken morning briefing audio delivered to Telegram at 8AM via AWS Lambda — cognitive offload for a solo operator running 12 active products
• **LangGraph pipeline in production**: 7-node StateGraph (VJH) with human-approval interrupt, SQLite checkpointer, 131-test eval harness (Claude Haiku as independent judge)
• **Semantic RAG in production**: pgvector + OpenAI embeddings in EspaLuz — 2-layer memory (exact history + cosine semantic search) injected into every Claude reply
• **AWS Lambda + EventBridge**: serverless scheduled deployment (Sprint Briefing Agent), ~$2/month
• **PayPal subscriptions live** — users across 19 countries
• **12 active GitHub repositories**, all monitored and reviewed by autonomous CTO AIPA

---

## TECHNICAL STACK

**AI/ML:** Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B) · Whisper · OpenAI TTS · LangChain · LangGraph (StateGraph, checkpointer, human interrupt) · Semantic RAG (pgvector + OpenAI embeddings) · MCP · ElizaOS

**Languages:** Python · TypeScript · JavaScript · Node.js · SQL

**Frameworks:** FastAPI · Flask · Express.js · React · Vite · Tailwind CSS

**Databases:** PostgreSQL (pgvector, ivfflat, cosine similarity) · Oracle Autonomous Database 26ai (mTLS) · SQLite

**Cloud & Infra:** Oracle Cloud Infrastructure (OCI) · AWS Lambda · AWS EventBridge · AWS S3 · Railway · PM2 · Ubuntu · Docker

**APIs:** GitHub API (Octokit) · Telegram Bot API · WhatsApp Business API · PayPal Subscriptions · Twitter/X · Resend · Playwright (ATS automation) · Replicate · Luma Labs

**Web3:** Polygon · Thirdweb · IPFS · DAO Design · Smart Contract Interaction

---

## PROFESSIONAL EXPERIENCE

### Founder and AI Product Engineer
**AIdeazz.xyz** | Panama/Remote | 2025–Present

Founder and lead builder of an AI-first ecosystem of applied LLM products and autonomous AI agents, developed using AI-augmented (Cursor + Claude Code) workflows.

**CTO AIPA — AI Technical Co-Founder (Production)**

Autonomous AI system for technical decision-making, code review, and daily briefing across 12 active repositories.

• Automated PR review and security scanning via GitHub API; model routing (Groq for speed, Claude for critical analysis)
• Voice input pipeline: voice notes → Whisper transcription → intent detection → Oracle diary/task storage (mTLS)
• **Sprint Briefing Agent** (AWS Lambda, Apr 2026): EventBridge fires daily at 8AM Panama → Lambda reads 12 repos + owner's Oracle voice notes/tasks (S3 wallet, thin-mode Oracle connector) → Groq clustering + Claude narrative → OpenAI TTS → Telegram MP3 audio. Full two-way loop: voice notes in at night → spoken briefing out in the morning. ~$2/month AWS cost.

*Technologies: TypeScript, Node.js, Claude, Groq, OpenAI TTS, Oracle Cloud (mTLS + S3 wallet), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2*

---

**VibeJobHunter AIPA — Autonomous AI Job Search System (Production)**

Full-stack AI pipeline that scrapes, scores, filters, and applies to jobs autonomously with human-in-the-loop for edge cases.

• **LangGraph pipeline** (7 nodes, StateGraph): scrape → gate → score → route → apply/outreach/discard. Human-approval interrupt via Telegram commands (`/approve_vjh_{id}` / `/reject_vjh_{id}`). SQLite checkpoint persistence.
• **4-layer eval harness** (131 tests, ~$0.03/run): deterministic scoring, bias compensation, 22-job golden set, Claude Haiku as independent judge (≥75% agreement) — catches regressions before deploy
• Multi-ATS Playwright automation (Greenhouse, Lever, Ashby) + founder email outreach via Resend API
• Hard gate excludes Senior/Staff/Principal/ML roles; daily cap 5 applications + 2 founder outreach emails

*Technologies: Python, LangGraph, Claude (Haiku + Sonnet), Playwright, SQLite, Resend, Telegram Bot API*

---

**EspaLuz — AI Spanish/English Tutor (Production, Paying Users)**

Bilingual EN/ES AI tutor with 2-layer persistent memory, semantic RAG, OCR, TTS, and multimodal learning.

• Deployed on WhatsApp Business API and Telegram; early traction across 19 Spanish-speaking countries; PayPal subscriptions live
• **2-layer memory**: LangChain `PostgresChatMessageHistory` (exact conversation history) + pgvector semantic RAG (`espaluz_embeddings` table, OpenAI `text-embedding-3-small`, cosine similarity > 0.75, top_k=3) — injected into Claude system prompt on every reply
• Separate session namespaces per platform (WhatsApp / Telegram); shared `espaluz_rag.py` module

*Technologies: Python, GPT-4, LangChain, pgvector (PostgreSQL), OpenAI embeddings, Whisper, WhatsApp API, Railway*

---

**CMO AIPA — AI Marketing Agent (Production)**

Autonomous AI agent for marketing strategy and content execution — daily bilingual (EN/ES) content, strategic reasoning, integrated with CTO AIPA for automated release announcements. *Technologies: Python, FastAPI, Claude, Make.com, Buffer, Railway*

**Atuona Creative AI** (atuona.xyz) — Multimodal AI creative pipeline: LLM → image → video → blockchain publishing. *Technologies: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs, Thirdweb, Polygon*

**ALGOM Alpha** — AI crypto education bot on X (@reviceva). *Technologies: Node.js, ElizaOS, CCXT, Twitter API*

---

### Operational Co-Founder
**OmniBazaar** (Decentralized Marketplace) | Remote | 2024–2025
• Structured DAO LLC (Marshall Islands); designed governance, tokenomics, DAO operating agreements

### Deputy CEO and Chief Legal Officer
**JSC "E-GOV OPERATOR"** | Russia | 2011–2018
• Led large-scale public-sector digital transformation; board-level governance; cross-functional teams (IT, legal, compliance); enterprise technology programs

### Deputy CEO (Business Development)
**Fundery LLC** (Fintech/Blockchain) | Russia | 2017–2018
• ICO compliance, investor relations, regulatory documentation, blockchain launch strategy

---

## EDUCATION AND CERTIFICATIONS

• **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025
• **How-To-DAO Cohort Graduate** | 2025
• **Master of Arts in Social Psychology** | Penza State University | 2018
• **Blockchain Regulation** | MGIMO | 2017
• **Presidential Program for Executive Management** | RANEPA | 2015
• Internship: Nyskapingsparken Innovation Park, Bergen, Norway

---

## LANGUAGES

Russian (Native) | English (Fluent) | Spanish (Intermediate) | French (Elementary)

---

## TARGET ROLES

AI Product Engineer | Applied LLM Engineer | Founding AI Engineer | Fractional AI Consultant/Builder | AI Ops / AI Program Manager

Open to: Full-time, Part-time, Contract, Remote

---

📧 aipa@aideazz.xyz | 💬 +507 616 66 716 (WhatsApp/Telegram) | 🔗 aideazz.xyz/card
