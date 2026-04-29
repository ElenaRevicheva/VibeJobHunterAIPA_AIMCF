# ELENA REVICHEVA

**AI Product Engineer | Applied LLM Systems | AI-Assisted Software Development**

Panama City, Panama | Remote Worldwide | On-site | Hybrid

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)  
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portfolio](https://aideazz.xyz/card)

---

## PROFESSIONAL SUMMARY

AI Product Engineer and founder with hands-on experience building and operating production LLM-powered products using AI-assisted, Cursor-centric development workflows. Specialized in applied LLM systems, AI agents, and rapid AI-first product execution.

Primary strength is **human-AI collaborative coding**: using AI tools (Cursor, Claude, GPT, Groq) to design, generate, and iterate production code under clear human intent, constraints, and validation. Former Deputy CEO and Chief Legal Officer in e-government, with 7+ years of executive leadership experience, bringing strong product judgment, execution discipline, legal due diligence, and business context to engineering work.

Seeking roles in AI-focused companies as an **AI Product Engineer**, **Applied LLM Engineer**, **AI Engineer**, or **Founding Engineer**.

---

## CORE SKILLS

### AI and LLMs
Claude (Opus, Sonnet, Haiku), OpenAI GPT-4, Groq (Llama 3.3 70B, Whisper), Model Context Protocol (MCP), LangChain, LangGraph (StateGraph, checkpointer, human-in-the-loop interrupt), Prompt Engineering, Multi-turn Context Design, Tool/Function Calling, Semantic RAG (pgvector + OpenAI embeddings)

### AI-Assisted Development
Cursor IDE (primary development environment), AI-assisted Code Generation and Refactoring, Human-in-the-loop Validation Workflows, Rapid Prototyping to Production Iteration

### Programming
Python, TypeScript, JavaScript, SQL

### Backend and APIs
FastAPI, Flask, Node.js, Express, REST APIs, Async Workflows

### Frontend
React, Vite, Tailwind CSS, Framer Motion

### Databases and Infrastructure
PostgreSQL (pgvector, ivfflat index, semantic search), Oracle Autonomous Database (mTLS), Oracle Cloud Infrastructure (OCI), AWS Lambda (Node.js runtime, serverless), AWS EventBridge (scheduled cron), AWS S3, Railway, Supabase, Docker, PM2, Ubuntu

### Integrations
GitHub API (Octokit), Telegram Bot API, WhatsApp Business API, PayPal Subscriptions, Twitter/X API, Make.com, Buffer

### Web3
Polygon, Thirdweb, IPFS, NFT Platforms, Smart Contract Interaction

---

## PROFESSIONAL EXPERIENCE

### Founder and AI Product Engineer
**AIdeazz.xyz** | Panama/Remote | 2025 – Present

Founder and lead builder of an AI-first ecosystem of applied LLM products and autonomous AI agents, developed using AI-assisted (Cursor-centric) workflows.

**Responsibilities:**
- Designed system architecture and product logic
- Used AI tools (Cursor, Claude, GPT, Groq) to generate, refactor, and evolve production code
- Integrated APIs, databases, bots, and payment systems
- Deployed, monitored, and operated production services independently

**Key Outcomes:**
- 12+ live AI products and agents deployed, operating autonomously in production
- 12 active GitHub repositories
- Users across 19 countries
- Live subscription monetization via PayPal
- Approximately 99% cost reduction compared to traditional multi-role development teams
- Built and shipped entirely using AI-augmented development (Cursor + Claude Code) — not traditional manual coding

---

### CTO AIPA - AI Technical Co-Founder (Production System)

Autonomous AI system supporting technical decision-making, code review, and daily briefing across 12 active repositories.

- Automated PR review and security scanning via GitHub API; model routing (Groq for speed, Claude for critical analysis)
- Human-approved AI code generation and PR workflows
- Persistent system memory using Oracle Autonomous Database with mTLS
- Voice input: voice notes → Whisper transcription → intent detection → Oracle diary/task storage

**Sprint Briefing Agent** (AWS Lambda, shipped Apr 2026) — daily autonomous morning briefing:
- Runs every day at 8AM on AWS Lambda (serverless, ~$2/month) triggered by EventBridge scheduler
- Reads all 12 GitHub repos overnight + retrieves owner's saved voice notes and tasks from Oracle (via S3 wallet, thin-mode Oracle connector — no server dependency)
- Passes combined signals to Groq (clustering) → Claude (narrative) → OpenAI TTS → Telegram audio
- Full two-way loop: voice notes in at night → spoken briefing out in the morning

**Technologies:** TypeScript, Node.js, Express, Claude, Groq, OpenAI, Oracle Cloud (mTLS + S3 wallet), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2

---

### CMO AIPA - AI Marketing Agent (Production System)

Autonomous AI agent for marketing strategy and content execution.

- Daily AI-generated bilingual (EN/ES) content
- Strategic reasoning for messaging and timing
- Integrated with technical system for automated release announcements

**Technologies:** Python, FastAPI, Claude, Make.com, Buffer, Railway

---

### EspaLuz - AI Spanish/English Tutor (Production System)

Built bilingual EN/ES AI tutor with 2-layer persistent memory, semantic RAG, OCR, TTS, and multimodal learning.

- Deployed on WhatsApp Business API and Telegram; early traction across 19 Spanish-speaking countries; PayPal subscriptions live
- **2-layer memory system:** LangChain `PostgresChatMessageHistory` (exact conversation history) + pgvector semantic search (`espaluz_embeddings` table, OpenAI `text-embedding-3-small`, cosine similarity > 0.75, top_k=3) — injected into Claude system prompt on every reply
- Separate session namespaces per platform (WhatsApp / Telegram); shared `espaluz_rag.py` module

**Technologies:** Python, GPT-4, LangChain, pgvector (PostgreSQL), OpenAI embeddings, Whisper, WhatsApp API, Railway

---

### VibeJobHunter AIPA - Autonomous AI Job Search System (Production System)

Full-stack AI pipeline that autonomously scrapes, scores, filters, and applies to jobs — with human-in-the-loop approval for edge cases.

- **LangGraph pipeline** (StateGraph, 7 nodes): scrape → gate → score → route → apply/outreach/discard. SQLite checkpointer for full session persistence; human-approval interrupt for 60–69 score band (Telegram `/approve` / `/reject` commands)
- **4-layer eval harness** (131 tests, ~$0.03/run): Layer 1–3 deterministic (keyword scoring, bias compensation, 22-job golden set); Layer 4 Claude Haiku as independent judge, ≥75% agreement threshold — catches regressions before deploy
- Multi-ATS Playwright automation (Greenhouse, Lever, Ashby); founder outreach via Resend API
- Hard gate: company size, stage, role category filters prevent auto-applying to roles that credential-filter (Senior/Staff/Principal/ML Engineer excluded)
- Daily cap: 5 applications + 2 founder outreach emails; all decisions logged to checkpoint DB

**Technologies:** Python, LangGraph, LangChain, Claude (Haiku + Sonnet), Playwright, SQLite, Resend API, Telegram Bot API

---

## ADDITIONAL DEPLOYED PRODUCTS

**Atuona Creative AI** (atuona.xyz) — Multimodal AI creative co-founder for writing, visual storytelling, and AI film
- LLM → image → video pipeline with persistent context, automated social formatting, and blockchain publishing
- Tech: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs API, Telegram Bot API, Thirdweb, Polygon

**AIdeazz.xyz** — Bilingual AI ecosystem platform for emotionally intelligent agents
- Tech: React, TypeScript

**ALGOM Alpha** — AI crypto education bot on X (@reviceva)
- Tech: Node.js, ElizaOS

---

## EARLIER EXPERIENCE

### Operational Co-Founder
**OmniBazaar** (Decentralized Marketplace Startup) | Remote | 2024 – 2025
- Structured DAO LLC (Marshall Islands)
- Designed governance, tokenomics, and operational workflows
- Drafted DAO operating agreements aligned with smart contracts

### Deputy CEO and Chief Legal Officer
**JSC "E-GOV OPERATOR"** | Russia | 2011 – 2018
- Led large-scale public-sector digital transformation initiatives
- Managed cross-functional teams (IT, legal, compliance)
- Oversaw enterprise technology programs and corporate board operations

### Deputy CEO (Business Development)
**Fundery LLC** (Fintech/Blockchain) | Russia | 2017 – 2018
- Managed ICO compliance, investor relations, and regulatory documentation
- Led contract negotiations and blockchain launch strategy

---

## EDUCATION AND CERTIFICATIONS

- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025 | Online
- **How-To-DAO Cohort Graduate** | 2025 | Online
- **Master of Arts in Social Psychology** | Penza State University | 2018 | Russia
- **Blockchain Regulation** | MGIMO | 2017 | Moscow
- **Presidential Program for Executive Management** | RANEPA | 2015
- **Internship** | Nyskapingsparken Innovation Park | Bergen, Norway

---

## LANGUAGES

🇷🇺 Russian (Native) | 🇬🇧 English (Fluent) | 🇪🇸 Spanish (Intermediate) | 🇫🇷 French (Elementary)

---

## TARGET ROLES

AI Product Engineer | Applied LLM Engineer | AI Engineer | Founding Engineer | AI Solutions Architect

---

## AVAILABILITY

Open to Full-time, Part-time, Contract, Remote

---

📧 aipa@aideazz.xyz | 💬 +507 616 66 716 (WhatsApp/Telegram)

