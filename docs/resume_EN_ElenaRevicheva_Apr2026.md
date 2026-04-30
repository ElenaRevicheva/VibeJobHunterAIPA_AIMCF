# ELENA REVICHEVA

**Applied AI Engineer | LLM Systems · AI Agents · Autonomous Pipelines** | **AI Systems Operator | AI Automation Lead

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portfolio](https://aideazz.xyz/card)

Costa del Este, Panama City | Remote Worldwide | UTC-5

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


## PROFESSIONAL SUMMARY

Applied AI Engineer with hands-on experience building and operating production LLM systems — agentic pipelines with LangGraph, 2-layer semantic memory with RAG/pgvector, automated evaluation harnesses, and serverless cloud deployment on AWS Lambda.

Background combines 7+ years of executive leadership in large-scale digital infrastructure programs (Deputy CEO & CLO, Russian E-Government sector) with 12+ months of solo AI product execution: 12 production systems, 12 active repositories, early users across 19 countries. Can translate technical architecture to business decisions — and back — in the same conversation. I combine executive-level thinking with practical system execution — able to translate
business needs into working AI solutions.

I use AI-assisted development to accelerate execution, while maintaining full ownership of system design, debugging, and production behavior. Comfortable working within existing teams, tools, and processes — not only building from scratch. 

Seeking roles as **Applied AI Engineer**, **AI Product Engineer**, **Founding AI Engineer**, or **Fractional AI Consultant/Builder**.


---
## HOW I BUILD

**I build production AI systems using an AI-augmented development workflow — Cursor IDE and Claude Code as daily primary tools.** This is not a shortcut; it is a deliberate, modern methodology that produced 12+ production systems currently running in the wild. Every architecture decision, system design, and production outcome is mine — the AI compresses execution time, the judgment is entirely human.

If your hiring process includes a proctored coding assessment or a live whiteboard test, I will say so upfront: that is not my workflow. If production systems matter more than whiteboard performance, I can show you mine in detail.
---

## CORE TECHNICAL SKILLS

### LLM Systems and Agents
Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B, Whisper) · model routing · tool/function calling · multi-step orchestration · prompt engineering · structured outputs · multi-turn context design

### Agent Frameworks & Memory
**LangGraph** (StateGraph, SQLite checkpointer, human-in-the-loop interrupt) · **LangChain** (PostgresChatMessageHistory, retrieval chains) · **Semantic RAG** (pgvector + OpenAI `text-embedding-3-small`, cosine similarity > 0.75, ivfflat index, top_k=3)

### Evaluation and Quality Assurance
4-layer eval harness: keyword scoring (L1) · bias compensation (L2) · golden-set routing (L3) · **Claude Haiku as independent LLM judge** (L4, ≥75% agreement threshold, 22 golden-set jobs) · ~$0.03/run · regression-catching before every deploy · Worked with early users to iterate on products behavior and prioritize features based on real usage

### AI-Augmented Development
Cursor IDE (primary environment) · Claude Code · AI-assisted code generation, refactoring, and system iteration · rapid prototyping → production

### Programming
Python · TypeScript · JavaScript · SQL

### Backend and APIs
Node.js · Express · FastAPI · Flask · REST APIs · async workflows · webhook handling · PostgreSQL

### Frontend
React 18 + TypeScript + Vite · Tailwind CSS · Framer Motion

### Databases and Infrastructure
PostgreSQL (pgvector, ivfflat, cosine similarity) · Oracle Autonomous Database (mTLS) · Oracle Cloud Infrastructure (OCI) · **AWS Lambda** (Node.js, serverless) · **AWS EventBridge** (scheduled cron) · AWS S3 · Railway · Supabase · Docker · PM2 · Ubuntu

### Infrastructure & Operations
Cloud deployment, process management, system monitoring, and self-healing architectures for reliable 24/7 operation

### Integrations
GitHub API (Octokit) · Telegram Bot API · WhatsApp Business API · PayPal Subscriptions · Twitter/X API · Make.com · Buffer · Resend · Playwright (ATS automation)

### GEO plus SEO Automation
AI-driven content systems, structured data, discoverability for search engines and AI crawlers, automated publishing and lead pipelines

### Web3
Polygon · Thirdweb · IPFS · NFT Platforms · Smart Contract Interaction

---

## PROFESSIONAL EXPERIENCE

### Applied AI Engineer & Founder
**AIdeazz.xyz** | Panama / Remote | 2025 – Present

Founder and sole builder of an AI-first ecosystem of 12+ production LLM systems and autonomous agents — developed using AI-augmented workflows (Cursor + Claude Code). Designed, built, and currently operate AI systems and automation pipelines across real-world
business and personal use cases, from idea to production and ongoing optimization. Production systems with real users (early traction), payments, and continuous operation.

---

**VibeJobHunter AIPA — Autonomous Job Search Pipeline (Production)**

Full-stack AI pipeline that scrapes, scores, filters, and applies to jobs autonomously — with human-in-the-loop approval for edge cases. Autonomous Job Pipeline: end-to-end system for job discovery, scoring, application, and follow-up, generating 250+ tailored applications and 140+ outreach messages

- **LangGraph StateGraph** (7 nodes): scrape → gate → score → route → apply / outreach / discard. SQLite checkpointer (`thread_id` per job for full deduplication); human-approval interrupt for score band 60–69 via Telegram (`/approve_vjh_{id}` / `/reject_vjh_{id}`)
- **4-layer evaluation harness** (131 tests, ~$0.03/run): Layers 1–3 deterministic (keyword scoring, bias compensation, 22-job golden set); Layer 4 = Claude Haiku as independent LLM judge at ≥75% agreement — catches scoring regressions before deploy
- Multi-ATS Playwright automation (Greenhouse, Lever, Ashby) + founder email outreach via Resend API
- Hard gate: role category, company stage, and size filters prevent auto-applying to credential-filtered roles; daily cap 5 applications + 2 outreach emails

*Tech: Python, LangGraph, LangChain, Claude (Haiku + Sonnet), Playwright, SQLite, Resend, Telegram Bot API*

---

**EspaLuz — AI Spanish/English Tutor (Production, Paying Users)**

Bilingual EN/ES AI tutor with 2-layer persistent memory, semantic RAG, OCR, TTS, and multimodal learning — deployed on WhatsApp Business API and Telegram. subscription-based assistant for expats to Spanish speaking countries with messaging, voice, and
persistent user context (early paying users via PayPal)

- **2-layer memory architecture**: LangChain `PostgresChatMessageHistory` (exact last 5 conversation turns) + **pgvector semantic RAG** (`espaluz_embeddings` table, OpenAI `text-embedding-3-small`, cosine similarity > 0.75, top_k=3) — injected into Claude system prompt before every reply. This means the bot remembers what you said last week and surfaces relevant past context without you repeating yourself.
- Separate session namespaces per platform (`telegram_*` / `whatsapp_*`); shared `espaluz_rag.py` module across both deployments
- Early traction across 19 Spanish-speaking countries; PayPal subscriptions live 

*Tech: Python, GPT-4, LangChain, pgvector (PostgreSQL), OpenAI embeddings, Whisper, WhatsApp Business API, Railway*

---

**CTO AIPA — AI Technical Co-Founder (Production)**

Autonomous AI system for code review, technical decision-making, and daily briefing across 12 active GitHub repositories.

- Automated PR review and security scanning via GitHub API; intelligent model routing (Groq Llama 3.3 70B for speed, Claude for critical/security analysis)
- Voice input pipeline: voice notes → Whisper transcription → intent detection → Oracle `knowledge_base` table (diary/task storage, mTLS)
- **Sprint Briefing Agent** (AWS Lambda, Apr 2026): EventBridge cron fires at 8AM Panama daily → Lambda reads 12 GitHub repos overnight activity + retrieves owner's voice notes and tasks from Oracle via S3 wallet (thin-mode Oracle connector — no Instant Client, pure JS) → Groq clusters the signals → Claude writes a narrative → OpenAI TTS (onyx voice) renders MP3 → delivered to Telegram. Full two-way memory loop: voice notes spoken at night → briefing audio plays in the morning. ~$2/month AWS cost.

*Tech: TypeScript, Node.js, Claude, Groq, OpenAI TTS, Oracle Cloud (mTLS + S3 wallet), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2*

---

**AI Marketing Agent (CMO AIPA) — Production**

AI Marketing Automation (GEO + SEO): fully automated content, discoverability, lead
capture, and outreach system operating with minimal manual input. Autonomous bilingual (EN/ES) content agent for marketing strategy and content execution — integrated with CTO AIPA for automated release announcements.

*Tech: Python, FastAPI, Claude, Make.com, Buffer, Railway*

---

**Additional Deployed Products**

**ALGOM Alpha** — AI crypto education and market analysis bot on X (@reviceva). *Tech: Node.js, ElizaOS, CCXT, Twitter API*

**Atuona Creative AI** (atuona.xyz) — Multimodal AI creative pipeline: LLM → image → video → blockchain NFT Drops publishing. *Tech: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs API, Thirdweb.com, Polygon*

---

**Key Portfolio Metrics**

| Metric | Result |
|--------|--------|
| Production AI systems | 12+ operating autonomously |
| Active GitHub repositories | 12 |
| Early users across Spanish-speaking countries | 19 |
| Cost vs traditional development | ~99% reduction ($900K → <$15K). Significant cost reduction compared to traditional development approaches (from team-based budgets to lean, AI-assisted builds) |
| LangGraph pipeline | 7-node StateGraph, SQLite checkpointer, human interrupt |
| Semantic RAG | pgvector + OpenAI embeddings, 2-layer memory, confirmed live |
| Eval harness | 131 tests, 4 layers, LLM-as-judge, ~$0.03/run | autonomous job discovery and outreach pipeline processing 1,900+
job listings, with voice-enabled Telegram interface for on-demand shortlisting,
generating 250+ tailored applications and 140+ outreach messages |
| AWS Lambda | Sprint Briefing Agent, EventBridge cron, ~$2/month |
| Production AI systems on Oracle Cloud (24/7 runtime, zero crash-restarts) |
|Multi-model routing architecture (76% requests routed to cost-optimized models, 24% to high-capability models for complex tasks) |
| Self-healing system architecture with automated monitoring and recovery, enabling continuous operation without manual intervention |

---

### Operational Co-Founder
**OmniBazaar** (Decentralized Marketplace) | Remote | 2024 – 2025
- Structured DAO LLC (Marshall Islands); designed governance, tokenomics, and DAO operating agreements aligned with smart contracts

### Deputy CEO and Chief Legal Officer
**JSC "E-GOV OPERATOR"** | Russia | 2011 – 2018
- Led large-scale public-sector digital transformation at board level
- Managed cross-functional teams (IT, legal, compliance, enterprise technology programs)
- Board-level governance in Russian regional E-Government sector

### Deputy CEO (Business Development)
**Fundery LLC** (Fintech/Blockchain) | Russia | 2017 – 2018
- ICO compliance, investor relations, regulatory documentation, blockchain launch strategy

---

## EDUCATION AND CERTIFICATIONS

- ** Anthropic Academy** The Anthropic Claude Certification Program | 2026 | Currently in progress
- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025 | Online
- **How-To-DAO Cohort Graduate** | 2025 | Online
- **MA Social Psychology** | Penza State University | 2018 | Russia
- **Blockchain Regulation** | MGIMO | 2017 | Moscow
- **Presidential Program for Executive Management** | RANEPA | 2015 | Moscow
- **Internship** | Nyskapingsparken Innovation Park | Bergen, Norway

---

## LANGUAGES

Russian (Native) | English (Fluent) | Spanish (Intermediate) | French (Elementary)

---

## TARGET ROLES

Applied AI Engineer · AI Product Engineer · Founding AI Engineer · Agentic AI Engineer · Internal AI Tools Engineer · Fractional AI Consultant/Builder ($40–70/hr)
· Agent Systems Engineer (Application Layer) · AI Solutions Engineer · AI Systems Operator · AI Automation Lead · AI Integration Specialist · Internal AI Tools Lead · AI Operations / AI Program Manager

Comfortable working across teams as an internal lead or embedded specialist, designing and delivering AI-driven solutions from concept to production.

Open to: Full-time · Part-time · Contract · Remote

---

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram) | 🔗 [aideazz.xyz/card](https://aideazz.xyz/card)
