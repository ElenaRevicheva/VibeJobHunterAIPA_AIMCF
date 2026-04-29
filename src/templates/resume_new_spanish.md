# ELENA REVICHEVA

**Ingeniera de Producto en IA | Sistemas LLM Aplicados | Desarrollo de Software Asistido por IA**

Ciudad de Panamá, Panamá | Remoto Global | Presencial | Híbrido

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)  
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portafolio](https://aideazz.xyz/card)

---

## RESUMEN PROFESIONAL

Ingeniera de Producto en IA y fundadora con experiencia práctica construyendo y operando productos LLM en producción mediante flujos de desarrollo asistidos por IA, centrados en Cursor. Especializada en sistemas LLM aplicados, agentes de IA y ejecución rápida de productos AI-first.

Mi principal fortaleza es la **codificación colaborativa humano–IA**: uso de herramientas de IA (Cursor, Claude, GPT, Groq) para diseñar, generar e iterar código de producción bajo intención humana clara, restricciones técnicas y validación continua. Ex Subdirectora General y Directora Legal en e-government, con más de 7 años de experiencia ejecutiva, aportando criterio de producto, disciplina de ejecución, due diligence legal y contexto de negocio al trabajo de ingeniería.

Busco roles en empresas enfocadas en IA como **AI Product Engineer**, **Applied LLM Engineer**, **AI Engineer**, **Founding Engineer**.

---

## CÓMO CONSTRUYO

**Desarrollo con flujos de trabajo asistidos por IA — Cursor IDE y Claude Code como herramientas principales.** Esto no es un atajo; es la metodología detrás de 12+ sistemas en producción. Cada decisión de arquitectura, integración y diseño de sistema es mía — la IA comprime el tiempo de ejecución, el criterio y la responsabilidad son completamente humanos. Si tu proceso incluye una prueba de codificación en vivo o un examen supervisado de sintaxis, lo diré con claridad desde el principio: ese no es mi flujo de trabajo. Si lo que importa es que los sistemas funcionen en producción, puedo mostrarte los míos directamente.

---

## HABILIDADES CLAVE

### IA y LLMs
Claude (Opus, Sonnet, Haiku), OpenAI GPT-4, Groq (Llama 3.3 70B, Whisper), Model Context Protocol (MCP), LangChain, LangGraph (StateGraph, checkpointer, aprobación humana en el loop), RAG semántico (pgvector + embeddings OpenAI), Prompt Engineering, diseño de contexto multi-turno, tool/function calling

### Desarrollo Asistido por IA
Cursor IDE (entorno principal), generación y refactorización de código asistida por IA, flujos de validación human-in-the-loop, prototipado rápido e iteración hasta producción

### Programación
Python, TypeScript, JavaScript, SQL

### Backend y APIs
FastAPI, Flask, Node.js, Express, REST APIs, flujos asíncronos

### Frontend
React, Vite, Tailwind CSS, Framer Motion

### Bases de Datos e Infraestructura
PostgreSQL (pgvector, índice ivfflat, búsqueda semántica), Oracle Autonomous Database (mTLS), Oracle Cloud Infrastructure (OCI), AWS Lambda (serverless), AWS EventBridge (cron programado), AWS S3, Railway, Supabase, Docker, PM2, Ubuntu

### Integraciones
GitHub API (Octokit), Telegram Bot API, WhatsApp Business API, PayPal Subscriptions, Twitter/X API, Make.com, Buffer

### Web3
Polygon, Thirdweb, IPFS, plataformas NFT, interacción con smart contracts

---

## EXPERIENCIA PROFESIONAL

### Fundadora y AI Product Engineer
**AIdeazz.xyz** | Panamá / Remoto | 2025 – Presente

Fundadora y principal builder de un ecosistema AI-first de productos LLM aplicados y agentes autónomos de IA, desarrollados mediante flujos asistidos por IA (centrados en Cursor).

**Responsabilidades:**
- Diseño de arquitectura de sistemas y lógica de producto
- Uso de herramientas de IA (Cursor, Claude, GPT, Groq) para generar, refactorizar y evolucionar código de producción
- Integración de APIs, bases de datos, bots y sistemas de pago
- Despliegue, monitoreo y operación independiente de servicios en producción

**Resultados Clave:**
- 12+ productos y agentes de IA en producción, operando de forma autónoma
- 12 repositorios activos en GitHub
- Usuarios en 19 países; monetización activa vía PayPal
- ~99% de reducción de costos frente a equipos tradicionales multi-rol
- Construido íntegramente con desarrollo asistido por IA (Cursor + Claude Code) — no codificación manual tradicional

---

### CTO AIPA — Asistente Técnico de IA (Sistema en Producción)

Sistema autónomo de IA para soporte en toma de decisiones técnicas y revisión de código en múltiples repositorios.

- Análisis automático de repositorios y revisión de PRs vía GitHub API
- Enrutamiento de modelos entre Claude (análisis profundo) y Groq (inferencia de baja latencia)
- Flujos de generación de código y PRs aprobados por humanos
- Memoria persistente del sistema usando Oracle Autonomous Database con mTLS

**Tecnologías:** TypeScript, Node.js, Express, Claude, Groq, Oracle Cloud, GitHub API, PM2

---

### CMO AIPA — Agente de Marketing de IA (Sistema en Producción)

Agente autónomo de IA para estrategia y ejecución de marketing.

- Generación diaria de contenido bilingüe (EN/ES)
- Razonamiento estratégico para mensajes y timing
- Integración con sistemas técnicos para anuncios automáticos de releases

**Tecnologías:** Python, FastAPI, Claude, Make.com, Buffer, Railway

---

### EspaLuz — Tutor de IA Español/Inglés (Sistema en Producción)

Tutor bilingüe EN/ES con memoria persistente de 2 capas, RAG semántico, OCR, TTS y aprendizaje multimodal.

- Desplegado en WhatsApp Business API y Telegram; tracción temprana en 19 países hispanohablantes; suscripciones PayPal activas
- **Memoria de 2 capas:** LangChain `PostgresChatMessageHistory` (historial exacto) + búsqueda semántica pgvector (tabla `espaluz_embeddings`, embeddings OpenAI `text-embedding-3-small`, similitud coseno > 0.75, top_k=3) — inyectada en el prompt de Claude en cada respuesta
- Espacios de sesión separados por plataforma (WhatsApp / Telegram)

**Tecnologías:** Python, GPT-4, LangChain, pgvector (PostgreSQL), embeddings OpenAI, Whisper, WhatsApp API, Railway

---

### VibeJobHunter AIPA — Sistema Autónomo de Búsqueda de Empleo (Producción)

Pipeline de IA que clasifica, puntúa, filtra y aplica a empleos de forma autónoma con aprobación humana en casos límite.

- **Pipeline LangGraph** (7 nodos, StateGraph): scraping → filtro → puntuación → enrutamiento → aplicar/outreach/descartar. Interrupción para aprobación humana vía Telegram. Persistencia con SQLite checkpointer.
- **Harness de evaluación de 4 capas** (131 pruebas): scoring determinista, compensación de sesgo, golden set de 22 empleos, Claude Haiku como juez independiente (≥75% acuerdo). ~$0.03/ejecución.
- Automatización Playwright para múltiples ATS (Greenhouse, Lever, Ashby) + outreach a fundadores vía Resend API

**Tecnologías:** Python, LangGraph, Claude (Haiku + Sonnet), Playwright, SQLite, Resend, Telegram Bot API

---

### CTO AIPA — Asistente Técnico de IA (Sistema en Producción)

Sistema autónomo para revisión de código en 12 repositorios + briefing diario por voz.

- Revisión automática de PRs vía GitHub API; enrutamiento de modelos (Groq/velocidad, Claude/análisis crítico)
- **Sprint Briefing Agent** (AWS Lambda, abr 2026): EventBridge dispara Lambda a las 8AM Panamá → lee 12 repos + notas de voz/tareas de Oracle (wallet S3, conector Oracle thin-mode) → Groq + Claude → TTS OpenAI → audio MP3 a Telegram. Bucle bidireccional: notas de voz por la noche → briefing hablado por la mañana. ~$2/mes en AWS.

**Tecnologías:** TypeScript, Node.js, Claude, Groq, OpenAI TTS, Oracle Cloud (mTLS + wallet S3), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2

---

## PRODUCTOS ADICIONALES DESPLEGADOS

**Atuona Creative AI** (atuona.xyz) — Co-founder creativo de IA multimodal para escritura, storytelling visual y cine con IA
- Pipeline LLM → imagen → video con contexto persistente, formateo automático para redes sociales y publicación en blockchain
- Tech: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs API, Telegram Bot API, Thirdweb, Polygon

**AIdeazz.xyz** — Plataforma bilingüe de ecosistema de IA para agentes emocionalmente inteligentes
- Tech: React, TypeScript

**ALGOM Alpha** — Bot educativo de IA sobre cripto en X (@reviceva)
- Tech: Node.js, ElizaOS

---

## EXPERIENCIA ANTERIOR

### Cofundadora Operativa
**OmniBazaar** (Marketplace Descentralizado) | Remoto | 2024 – 2025
- Estructuración de DAO LLC (Islas Marshall)
- Diseño de gobernanza, tokenomics y flujos operativos
- Redacción de acuerdos DAO alineados con smart contracts

### Subdirectora General y Directora Legal
**JSC "E-GOV OPERATOR"** | Rusia | 2011 – 2018
- Liderazgo de iniciativas de transformación digital en sector público
- Gestión de equipos multidisciplinarios (IT, legal, compliance)
- Supervisión de programas tecnológicos enterprise y operaciones de consejo corporativo

### Subdirectora General (Desarrollo de Negocio)
**Fundery LLC** (Fintech / Blockchain) | Rusia | 2017 – 2018
- Gestión de cumplimiento ICO y relaciones con inversores
- Liderazgo en negociaciones contractuales y estrategia de lanzamiento blockchain

---

## EDUCACIÓN Y CERTIFICACIONES

- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025 | Online
- **How-To-DAO Cohort Graduate** | 2025 | Online
- **Máster en Psicología Social** | Universidad Estatal de Penza | 2018 | Rusia
- **Regulación Blockchain** | MGIMO | 2017 | Moscú
- **Programa Presidencial de Dirección Ejecutiva** | RANEPA | 2015
- **Prácticas** | Nyskapingsparken Innovation Park | Bergen, Noruega

---

## IDIOMAS

🇷🇺 Ruso (Nativo) | 🇬🇧 Inglés (Fluido) | 🇪🇸 Español (Intermedio) | 🇫🇷 Francés (Básico)

---

## ROLES OBJETIVO

AI Product Engineer | Applied LLM Engineer | Founding AI Engineer | Consultora/Constructora de IA Fraccional ($40–70/hr) | AI Ops / AI Program Manager

---

## DISPONIBILIDAD

Disponible para tiempo completo, medio tiempo, contrato y remoto

---

📧 aipa@aideazz.xyz | 💬 +507 616 66 716 (WhatsApp/Telegram)

