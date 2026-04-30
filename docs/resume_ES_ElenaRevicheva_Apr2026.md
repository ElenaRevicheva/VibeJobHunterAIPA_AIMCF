# ELENA REVICHEVA

**Ingeniera de IA Aplicada | Sistemas LLM · Agentes de IA · Pipelines Autónomos | AI Systems Operator | AI Automation Lead**

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram)
🔗 [LinkedIn](https://linkedin.com/in/elenarevicheva) | [GitHub](https://github.com/ElenaRevicheva) | [Portfolio](https://aideazz.xyz/card)

Costa del Este, Panama City | Remoto Mundial | UTC-5

---

## INFORMACIÓN PERSONAL

| | |
|---|---|
| **Fecha de Nacimiento** | 11 de diciembre de 1985 |
| **Nacionalidad** | Rusa |
| **Residencia en Panamá** | Carné de Residente Permanente |
| **Permiso de Trabajo Panameño** | Tipo 4B |
| **RUC - PERSONA NATURAL EXTRANJERA** | 8-NT-2-781965 DV 90, Actividad Empresarial Ocupación 21320 - PROGRAMADORES INFORMATICOS |
| **Licencia de Conducir Panameña** | Tipo C |
| **Ubicación** | Costa del Este, Juan Díaz, Ciudad de Panamá |

---

## RESUMEN PROFESIONAL

Ingeniera de IA Aplicada con experiencia práctica construyendo y operando sistemas LLM en producción — pipelines agénticos con LangGraph, memoria semántica de 2 capas con RAG/pgvector, arneses de evaluación automatizados y despliegue en la nube con Oracle y AWS Lambda.

Mi trayectoria combina 7+ años de liderazgo ejecutivo en programas de infraestructura digital a gran escala (Vicepresidenta Ejecutiva & Directora Legal, sector E-Gobierno ruso) con 12+ meses de ejecución en solitario de productos de IA: 12 sistemas en producción, 12 repositorios activos, usuarios tempranos en 19 países. Puedo traducir arquitectura técnica en decisiones de negocio — y viceversa — en la misma conversación.

Utilizo desarrollo asistido por IA para acelerar la ejecución, manteniendo plena responsabilidad sobre el diseño de sistemas, depuración y comportamiento en producción. Cómoda trabajando dentro de equipos, herramientas y procesos existentes — no solo construyendo desde cero.

Busco roles como **Ingeniera de IA Aplicada**, **AI Product Engineer**, **Founding AI Engineer** o **Consultora/Desarrolladora Fractional de IA**.

---

## CÓMO CONSTRUYO

**Construyo sistemas de IA en producción usando un flujo de trabajo de desarrollo aumentado por IA — Cursor IDE y Claude Code como herramientas primarias diarias.** Esto no es un atajo; es una metodología deliberada y moderna que produjo 12+ sistemas en producción funcionando activamente. Cada decisión de arquitectura, diseño de sistema y resultado en producción es mío — la IA comprime el tiempo de ejecución, el criterio es enteramente humano.

Si tu proceso de selección incluye una evaluación de código supervisada o una prueba en pizarra en vivo, prefiero ser transparente: ese no es mi flujo de trabajo. Mi fortaleza está en construir y operar sistemas reales. Estoy dispuesta a revisar arquitecturas y decisiones de producción en detalle.

---

## HABILIDADES TÉCNICAS

### Sistemas LLM y Agentes
Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B, Whisper) · enrutamiento de modelos · tool/function calling · orquestación multi-paso · prompt engineering · outputs estructurados · diseño de contexto multi-turno

### Frameworks de Agentes y Memoria
**LangGraph** (StateGraph, SQLite checkpointer, human-in-the-loop interrupt) · **LangChain** (PostgresChatMessageHistory, cadenas de recuperación) · **Semantic RAG** (pgvector + OpenAI `text-embedding-3-small`, similitud coseno > 0.75, índice ivfflat, top_k=3)

### Evaluación y Aseguramiento de Calidad
Arnés de evaluación de 4 capas: puntuación por palabras clave (L1) · compensación de sesgo (L2) · enrutamiento por golden-set (L3) · **Claude Haiku como juez LLM independiente** (L4, umbral ≥75% de acuerdo, 22 trabajos golden-set) · ~$0.03/ejecución · detección de regresiones antes de cada deploy · Trabajé con usuarios tempranos para iterar el comportamiento de los productos y priorizar funcionalidades basadas en uso real

### Desarrollo Aumentado por IA
Cursor IDE (entorno principal) · Claude Code · generación de código asistida por IA, refactorización e iteración de sistemas · prototipado rápido → producción

### Programación
Python · TypeScript · JavaScript · SQL

### Backend y APIs
Node.js · Express · FastAPI · Flask · REST APIs · flujos de trabajo asíncronos · manejo de webhooks · PostgreSQL

### Frontend
React 18 + TypeScript + Vite · Tailwind CSS · Framer Motion

### Bases de Datos e Infraestructura
PostgreSQL (pgvector, ivfflat, similitud coseno) · Oracle Autonomous Database (mTLS) · Oracle Cloud Infrastructure (OCI) · **AWS Lambda** (Node.js, serverless) · **AWS EventBridge** (cron programado) · AWS S3 · Railway · Supabase · Docker · PM2 · Ubuntu

### Infraestructura y Operaciones
Despliegue en la nube, gestión de procesos, monitoreo de sistemas y arquitecturas autorreparables para operación 24/7 confiable

### Integraciones
GitHub API (Octokit) · Telegram Bot API · WhatsApp Business API · PayPal Subscriptions · Twitter/X API · Make.com · Buffer · Resend · Playwright (automatización ATS)

### Automatización GEO + SEO
Sistemas de contenido impulsados por IA, datos estructurados, visibilidad para motores de búsqueda y crawlers de IA, publicación automatizada y pipelines de captación de leads

### Web3
Polygon · Thirdweb · IPFS · Plataformas NFT · Interacción con Smart Contracts

---

## EXPERIENCIA PROFESIONAL

### Ingeniera de IA Aplicada & Fundadora
**AIdeazz.xyz** | Panamá / Remoto | 2025 – Presente

Fundadora y única desarrolladora de un ecosistema AI-first de 12+ sistemas LLM en producción y agentes autónomos — construido con flujos de trabajo aumentados por IA (Cursor + Claude Code). Diseñé, construí y actualmente opero sistemas de IA y pipelines de automatización para casos de uso reales de negocio y personales, desde la idea hasta producción y optimización continua. Sistemas en producción con usuarios reales (tracción temprana), pagos y operación continua.

---

**VibeJobHunter AIPA — Pipeline Autónomo de Búsqueda de Empleo (Producción)**

Pipeline de IA full-stack que scrapea, puntúa, filtra y aplica a empleos de forma autónoma — con aprobación humana en el bucle para casos límite. Generó 250+ aplicaciones personalizadas y 140+ mensajes de outreach procesando 1,900+ listings en producción.

- **LangGraph StateGraph** (7 nodos): scrape → gate → score → route → apply / outreach / discard. SQLite checkpointer (`thread_id` por empleo para deduplicación completa); interrupción de aprobación humana para banda de puntuación 60–69 vía Telegram (`/approve_vjh_{id}` / `/reject_vjh_{id}`)
- **Arnés de evaluación de 4 capas** (131 pruebas, ~$0.03/ejecución): Capas 1–3 deterministas (puntuación por palabras clave, compensación de sesgo, golden set de 22 empleos); Capa 4 = Claude Haiku como juez LLM independiente a ≥75% de acuerdo — detecta regresiones de puntuación antes del deploy
- Automatización multi-ATS con Playwright (Greenhouse, Lever, Ashby) + outreach por email a fundadores vía Resend API
- Filtro estricto: categoría de rol, etapa y tamaño de empresa impiden aplicaciones automáticas a roles con requisitos de credenciales; límite diario de 5 aplicaciones + 2 emails de outreach

*Tech: Python, LangGraph, LangChain, Claude (Haiku + Sonnet), Playwright, SQLite, Resend, Telegram Bot API*

---

**EspaLuz — Tutor de IA Español/Inglés (Producción, Tracción temprana)**

Tutor de IA bilingüe EN/ES basado en suscripción con memoria persistente de 2 capas, RAG semántico, OCR, TTS y aprendizaje multimodal — desplegado en WhatsApp Business API y Telegram. Usuarios pagando desde el inicio vía PayPal; tracción en 19 países hispanohablantes.

- **Arquitectura de memoria de 2 capas**: LangChain `PostgresChatMessageHistory` (últimas 5 conversaciones exactas) + **pgvector semantic RAG** (tabla `espaluz_embeddings`, OpenAI `text-embedding-3-small`, similitud coseno > 0.75, top_k=3) — inyectado en el system prompt de Claude antes de cada respuesta. El bot recuerda lo que dijiste la semana pasada y recupera contexto pasado relevante sin que tengas que repetirte.
- Espacios de sesión separados por plataforma (`telegram_*` / `whatsapp_*`); módulo compartido `espaluz_rag.py` entre ambos despliegues
- Tracción temprana en 19 países hispanohablantes; suscripciones PayPal activas

*Tech: Python, GPT-4, LangChain, pgvector (PostgreSQL), OpenAI embeddings, Whisper, WhatsApp Business API, Railway*

---

**CTO AIPA — Co-Fundador Técnico de IA (Producción)**

Sistema de IA autónomo para revisión de código, toma de decisiones técnicas y briefing diario en 12 repositorios activos de GitHub.

- Revisión automatizada de PRs y escaneo de seguridad vía GitHub API; enrutamiento inteligente de modelos (Groq Llama 3.3 70B para velocidad, Claude para análisis crítico/seguridad)
- Pipeline de entrada por voz: notas de voz → transcripción Whisper → detección de intención → tabla Oracle `knowledge_base` (almacenamiento de diario/tareas, mTLS)
- **Sprint Briefing Agent** (AWS Lambda, abril 2026): EventBridge cron se activa a las 8AM hora de Panamá diariamente → Lambda lee la actividad nocturna de 12 repos de GitHub + recupera notas de voz y tareas del propietario desde Oracle vía un proxy REST seguro en el servidor CTO → Groq agrupa las señales → Claude redacta una narrativa → OpenAI TTS (voz onyx) genera el MP3 → entregado a Telegram. Bucle de memoria bidireccional completo: notas de voz habladas de noche → audio del briefing se escucha por la mañana. ~$2/mes en AWS.

*Tech: TypeScript, Node.js, Claude, Groq, OpenAI TTS, Oracle Cloud (mTLS), AWS Lambda, AWS EventBridge, AWS S3, GitHub API, PM2*

---

**AI Marketing Agent (CMO AIPA) — Producción**

Agente de contenido bilingüe (EN/ES) autónomo: automatización de contenido GEO+SEO, visibilidad, captación de leads y pipeline de outreach — integrado con CTO AIPA para anuncios automatizados de lanzamientos. Opera con mínima intervención manual.

*Tech: Python, FastAPI, Claude, Make.com, Buffer, Railway*

---

**Productos Adicionales Desplegados**

**ALGOM Alpha** — Bot de IA para educación cripto y análisis de mercado en X (@reviceva). *Tech: Node.js, ElizaOS, CCXT, Twitter API*

**Atuona Creative AI** (atuona.xyz) — Pipeline de IA creativa multimodal: LLM → imagen → video → publicación de NFT Drops en blockchain. *Tech: TypeScript, Node.js, Claude Opus, Replicate, Luma Labs API, Thirdweb.com, Polygon*

---

**Métricas Clave del Portfolio**

| Métrica | Resultado |
|---------|-----------|
| Sistemas de IA en producción | 12+ operando de forma autónoma |
| Repositorios activos en GitHub | 12 |
| Usuarios tempranos en países hispanohablantes | 19 |
| Coste vs. desarrollo tradicional | Reducción ~99% ($900K → <$15K) vs. equipos tradicionales |
| Pipeline LangGraph | StateGraph de 7 nodos, SQLite checkpointer, interrupción humana |
| Semantic RAG | pgvector + OpenAI embeddings, memoria 2 capas, confirmado en vivo |
| Arnés de evaluación | 131 pruebas, 4 capas, LLM-as-judge, ~$0.03/ejecución |
| Throughput del pipeline de empleo | 1,900+ listings procesados · 250+ aplicaciones · 140+ mensajes de outreach |
| AWS Lambda | Sprint Briefing Agent, EventBridge cron, ~$2/mes |
| Disponibilidad Oracle Cloud | Operación 24/7, cero reinicios por fallos |
| Enrutamiento multi-modelo | 76% modelos optimizados por coste · 24% alta capacidad para tareas complejas |
| Resiliencia del sistema | Arquitectura autorreparable, recuperación automatizada, sin intervención manual |

---

### Co-Fundadora Operacional
**OmniBazaar** (Marketplace Descentralizado) | Remoto | 2024 – 2025
- Estructuré DAO LLC (Islas Marshall); diseñé gobernanza, tokenomics y acuerdos operativos DAO alineados con smart contracts

### Vicepresidenta Ejecutiva y Directora Legal
**JSC "E-GOV OPERATOR"** | Rusia | 2011 – 2018
- Lideré transformación digital del sector público a gran escala a nivel de consejo directivo
- Gestioné equipos multifuncionales (TI, legal, cumplimiento normativo, programas de tecnología empresarial)
- Gobernanza a nivel de consejo en el sector de E-Gobierno regional ruso

### Vicepresidenta Ejecutiva (Desarrollo de Negocio)
**Fundery LLC** (Fintech/Blockchain) | Rusia | 2017 – 2018
- Cumplimiento normativo ICO, relaciones con inversores, documentación regulatoria, estrategia de lanzamiento blockchain

---

## EDUCACIÓN Y CERTIFICACIONES

- **Anthropic Academy** — Programa de Certificación Claude | 2026 | En Progreso
- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025 | Online
- **How-To-DAO Cohort Graduate** | 2025 | Online
- **Máster en Psicología Social** | Universidad Estatal de Penza | 2018 | Rusia
- **Regulación Blockchain** | MGIMO | 2017 | Moscú
- **Programa Presidencial de Gestión Ejecutiva** | RANEPA | 2015 | Moscú
- **Pasantía** | Nyskapingsparken Innovation Park | Bergen, Noruega

---

## IDIOMAS

Ruso (Nativo) | Inglés (Fluido) | Español (Intermedio) | Francés (Elemental)

---

## ROLES OBJETIVO

Ingeniera de IA Aplicada · AI Product Engineer · Founding AI Engineer · Agentic AI Engineer · Internal AI Tools Engineer · Fractional AI Consultant/Builder ($40–70/hr) · Agent Systems Engineer (Application Layer) · AI Solutions Engineer · AI Systems Operator · AI Automation Lead · AI Integration Specialist · Internal AI Tools Lead · AI Operations / AI Program Manager

Cómoda trabajando en equipos como líder interna o especialista integrada, diseñando y entregando soluciones impulsadas por IA desde el concepto hasta producción.

Disponible para: Tiempo completo · Tiempo parcial · Contrato · Remoto

---

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram) | 🔗 [aideazz.xyz/card](https://aideazz.xyz/card)
