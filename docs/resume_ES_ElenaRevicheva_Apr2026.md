# ELENA REVICHEVA

**Ingeniera de IA Aplicada | Sistemas LLM · Agentes de IA · Pipelines Autónomos**

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portafolio](https://aideazz.xyz/card)

Costa del Este, Juan Díaz, Ciudad de Panamá | Remoto Global | UTC-5

---

## DATOS PERSONALES

| | |
|---|---|
| **Fecha de nacimiento** | 11 de diciembre de 1985 |
| **Nacionalidad** | Rusa |
| **Residencia en Panamá** | Carné de Residente Permanente |
| **Permiso de trabajo** | Tipo 4B |
| **Licencia de conducir** | Tipo C |
| **Ubicación** | Costa del Este, Juan Díaz, Ciudad de Panamá |

---

## CÓMO CONSTRUYO

**Construyo sistemas de IA en producción usando un flujo de trabajo de desarrollo asistido por IA — Cursor IDE y Claude Code como herramientas principales de uso diario.** Esta no es una solución atajo; es una metodología deliberada y moderna que ha producido 12+ sistemas en producción funcionando actualmente. Cada decisión de arquitectura, diseño de sistema y resultado productivo es mío — la IA comprime el tiempo de ejecución, el criterio es completamente humano.

Si tu proceso de selección incluye una prueba de codificación supervisada o una pizarra en vivo, lo diré directamente desde el inicio: ese no es mi flujo de trabajo. Si los sistemas en producción importan más que el desempeño en pizarra, puedo mostrarte los míos en detalle.

---

## RESUMEN PROFESIONAL

Ingeniera de IA Aplicada con experiencia práctica construyendo y operando sistemas LLM en producción — pipelines agénticos con LangGraph, memoria semántica de 2 capas con RAG/pgvector, arneses de evaluación automatizados y despliegue serverless en AWS Lambda.

Mi perfil combina 7+ años de liderazgo ejecutivo en programas de infraestructura digital a gran escala (Subdirectora General, sector E-Government ruso) con 12+ meses de ejecución de productos de IA como fundadora independiente: 12 sistemas en producción, 12 repositorios activos, usuarios en 19 países. Traduzco arquitectura técnica a decisiones de negocio — y viceversa — en la misma conversación.

Busco roles como **Ingeniera de IA Aplicada**, **AI Product Engineer**, **Founding AI Engineer** o **Consultora de IA Fraccional**.

---

## HABILIDADES TÉCNICAS CLAVE

### Sistemas LLM y Agentes
Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B, Whisper) · enrutamiento de modelos · tool/function calling · orquestación multi-paso · ingeniería de prompts · salidas estructuradas · diseño de contexto multi-turno

### Frameworks de Agentes y Memoria
**LangGraph** (StateGraph, checkpointer SQLite, interrupción con aprobación humana) · **LangChain** (PostgresChatMessageHistory, cadenas de recuperación) · **RAG Semántico** (pgvector + embeddings OpenAI `text-embedding-3-small`, similitud coseno > 0.75, índice ivfflat, top_k=3)

### Evaluación y Control de Calidad
Arnés de evaluación de 4 capas: scoring por palabras clave (C1) · compensación de sesgo (C2) · enrutamiento por golden set (C3) · **Claude Haiku como juez LLM independiente** (C4, umbral ≥75% de acuerdo, 22 trabajos en golden set) · ~$0.03/ejecución · detección de regresiones antes de cada despliegue

### Desarrollo Asistido por IA
Cursor IDE (entorno principal) · Claude Code · generación y refactorización de código asistida por IA · prototipado rápido → producción

### Programación
Python · TypeScript · JavaScript · SQL

### Backend y APIs
Node.js · Express · FastAPI · Flask · REST APIs · flujos asíncronos · manejo de webhooks · PostgreSQL

### Frontend
React 18 + TypeScript + Vite · Tailwind CSS · Framer Motion

### Bases de Datos e Infraestructura
PostgreSQL (pgvector, ivfflat, similitud coseno) · Oracle Autonomous Database (mTLS) · Oracle Cloud Infrastructure (OCI) · **AWS Lambda** (Node.js, serverless) · **AWS EventBridge** (cron programado) · AWS S3 · Railway · Supabase · Docker · PM2 · Ubuntu

### Integraciones
GitHub API (Octokit) · Telegram Bot API · WhatsApp Business API · PayPal Subscriptions · Twitter/X API · Make.com · Buffer · Resend · Playwright (automatización ATS)

### Web3
Polygon · Thirdweb · IPFS · Plataformas NFT · Interacción con Smart Contracts

---

## EXPERIENCIA PROFESIONAL

### Ingeniera de IA Aplicada y Fundadora
**AIdeazz.xyz** | Panamá / Remoto | 2025 – Presente

Fundadora y constructora principal de un ecosistema AI-first de 12+ sistemas LLM en producción y agentes autónomos — desarrollados con flujos de trabajo asistidos por IA (Cursor + Claude Code).

---

**VibeJobHunter AIPA — Pipeline Autónomo de Búsqueda de Empleo (Producción)**

Pipeline de IA de pila completa que raspa, puntúa, filtra y aplica a empleos de forma autónoma — con aprobación humana en el loop para casos límite.

- **LangGraph StateGraph** (7 nodos): scraping → filtro → puntuación → enrutamiento → aplicar / outreach / descartar. Checkpointer SQLite (`thread_id` por trabajo para deduplicación completa); interrupción de aprobación humana para banda de puntuación 60–69 vía Telegram (`/approve_vjh_{id}` / `/reject_vjh_{id}`)
- **Arnés de evaluación de 4 capas** (131 pruebas, ~$0.03/ejecución): Capas 1–3 deterministas (scoring por palabras clave, compensación de sesgo, golden set de 22 trabajos); Capa 4 = Claude Haiku como juez LLM independiente con umbral ≥75% de acuerdo — detecta regresiones antes de cada despliegue
- Automatización Playwright multi-ATS (Greenhouse, Lever, Ashby) + outreach por email a fundadores vía API Resend
- Filtro duro: categoría de rol, etapa y tamaño de empresa para evitar aplicaciones a roles con filtros de credenciales; límite diario 5 aplicaciones + 2 correos de outreach

*Tech: Python, LangGraph, LangChain, Claude (Haiku + Sonnet), Playwright, SQLite, Resend, Telegram Bot API*

---

**EspaLuz — Tutor de IA Español/Inglés (Producción, Usuarios de Pago)**

Tutor de IA bilingüe EN/ES con memoria persistente de 2 capas, RAG semántico, OCR, TTS y aprendizaje multimodal — desplegado en WhatsApp Business API y Telegram.

- **Arquitectura de memoria de 2 capas**: LangChain `PostgresChatMessageHistory` (últimas 5 conversaciones exactas) + **RAG semántico con pgvector** (tabla `espaluz_embeddings`, embeddings OpenAI `text-embedding-3-small`, similitud coseno > 0.75, top_k=3) — inyectados en el prompt de Claude antes de cada respuesta. El bot recuerda lo que dijiste la semana pasada y muestra contexto relevante sin que tengas que repetirte.
- Espacios de sesión separados por plataforma (`telegram_*` / `whatsapp_*`); módulo compartido `espaluz_rag.py`
- Tracción temprana en 19 países hispanohablantes; suscripciones PayPal activas

*Tech: Python, GPT-4, LangChain, pgvector (PostgreSQL), embeddings OpenAI, Whisper, WhatsApp Business API, Railway*

---

**CTO AIPA — Co-Fundador Técnico de IA (Producción)**

Sistema autónomo de IA para revisión de código, toma de decisiones técnicas y briefing diario en 12 repositorios GitHub activos.

- Revisión automática de PRs y escaneo de seguridad vía GitHub API; enrutamiento inteligente de modelos (Groq Llama 3.3 70B para velocidad, Claude para análisis crítico/seguridad)
- Pipeline de voz: notas de voz → transcripción Whisper → detección de intención → almacenamiento en tabla `knowledge_base` de Oracle (diario/tareas, mTLS)
- **Sprint Briefing Agent** (AWS Lambda, abr. 2026): cron de EventBridge se activa a las 8AM Panamá → Lambda lee actividad nocturna de 12 repos GitHub + recupera notas de voz y tareas del propietario desde Oracle vía wallet S3 (conector Oracle thin-mode — sin Instant Client, JS puro) → Groq agrupa las señales → Claude escribe la narrativa → OpenAI TTS (voz onyx) genera MP3 → entregado a Telegram. Bucle de memoria bidireccional completo: notas de voz por la noche → audio de briefing por la mañana. ~$2/mes en AWS.

*Tech: TypeScript, Node.js, Claude, Groq, OpenAI TTS, Oracle Cloud (mTLS + wallet S3), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2*

---

**Agente de Marketing IA (CMO AIPA) — Producción**

Agente de contenido bilingüe (EN/ES) autónomo para estrategia de marketing y ejecución de contenido — integrado con CTO AIPA para anuncios automáticos de lanzamientos.

*Tech: Python, FastAPI, Claude, Make.com, Buffer, Railway*

---

**Productos Adicionales Desplegados**

**ALGOM Alpha** — Bot de educación cripto e IA en X (@reviceva). *Tech: Node.js, ElizaOS, CCXT, Twitter API*

**Atuona Creative AI** (atuona.xyz) — Pipeline creativo multimodal de IA: LLM → imagen → video → publicación blockchain. *Tech: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs API, Thirdweb, Polygon*

---

**Métricas Clave del Portafolio**

| Métrica | Resultado |
|---------|-----------|
| Sistemas de IA en producción | 12+ operando autónomamente |
| Repositorios GitHub activos | 12 |
| Usuarios por países | 19 |
| Reducción de costos vs. desarrollo tradicional | ~99% ($900K → <$15K) |
| Pipeline LangGraph | StateGraph 7 nodos, checkpointer SQLite, interrupción humana |
| RAG semántico | pgvector + embeddings OpenAI, memoria 2 capas, live en prod |
| Arnés de evaluación | 131 pruebas, 4 capas, juez LLM, ~$0.03/ejecución |
| AWS Lambda | Sprint Briefing Agent, cron EventBridge, ~$2/mes |

---

### Cofundadora Operativa
**OmniBazaar** (Marketplace Descentralizado) | Remoto | 2024 – 2025
- Estructuración de DAO LLC (Islas Marshall); diseño de gobernanza, tokenomics y acuerdos DAO alineados con smart contracts

### Subdirectora General y Directora Legal
**JSC "E-GOV OPERATOR"** | Rusia | 2011 – 2018
- Liderazgo de iniciativas de transformación digital del sector público a nivel de consejo directivo
- Gestión de equipos multidisciplinarios (IT, legal, compliance, programas tecnológicos enterprise)
- Gobernanza corporativa en el sector E-Government regional ruso

### Subdirectora General (Desarrollo de Negocio)
**Fundery LLC** (Fintech/Blockchain) | Rusia | 2017 – 2018
- Cumplimiento ICO, relaciones con inversores, documentación regulatoria, estrategia de lanzamiento blockchain

---

## EDUCACIÓN Y CERTIFICACIONES

- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025 | Online
- **How-To-DAO Cohort Graduate** | 2025 | Online
- **Máster en Psicología Social** | Universidad Estatal de Penza | 2018 | Rusia
- **Regulación Blockchain** | MGIMO | 2017 | Moscú
- **Programa Presidencial de Dirección Ejecutiva** | RANEPA | 2015 | Moscú
- **Prácticas** | Nyskapingsparken Innovation Park | Bergen, Noruega

---

## IDIOMAS

Ruso (Nativo) | Inglés (Fluido) | Español (Intermedio) | Francés (Básico)

---

## ROLES OBJETIVO

Ingeniera de IA Aplicada · AI Product Engineer · Founding AI Engineer · Agentic AI Engineer · Internal AI Tools Engineer · Consultora de IA Fraccional ($40–70/hr)

Disponible para: Tiempo completo · Medio tiempo · Contrato · Remoto

---

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram) | 🔗 [aideazz.xyz/card](https://aideazz.xyz/card)
