# ELENA REVICHEVA

**Ingeniera de IA Aplicada | Construyo Sistemas de IA que Funcionan en Producción**

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

Construyo usando **Cursor IDE y Claude Code como herramientas principales de uso diario** — un flujo de trabajo asistido por IA que produjo 12+ sistemas en producción en menos de un año, a una fracción de lo que costaría un equipo tradicional. Cada decisión de diseño y resultado del sistema es mío; la IA comprime el tiempo de ejecución. Este enfoque es deliberado y moderno, no un atajo.

**Nota para equipos de selección:** Si tu proceso incluye una prueba de codificación supervisada o una pizarra en vivo, lo diré directamente desde el inicio — ese no es mi flujo de trabajo. Si lo que importa son sistemas en producción que funcionan, puedo mostrarte los míos.

---

## RESUMEN PROFESIONAL

En los últimos 12 meses, construí y lancé 12 productos de IA — como fundadora independiente, sin equipo. El equivalente a lo que la mayoría de las empresas asigna a 4–5 ingenieros, al menos del 1% del costo.

No son demos ni prototipos. Son sistemas operando 24/7: un motor de búsqueda de empleo que aplica de forma autónoma, un tutor de idiomas que recuerda a sus estudiantes, un agente de revisión de código que vigila 12 repositorios, un briefing de voz entregado cada mañana a las 8AM. Usuarios reales. Pagos reales. Infraestructura real.

Antes de la IA, trabajé 7 años como Subdirectora General y Directora Legal dirigiendo grandes programas de infraestructura digital para el gobierno ruso — tecnología enterprise, decisiones a nivel de consejo directivo, equipos multidisciplinarios. Sé pensar a nivel de sistemas y hablar tanto con decisores como con desarrolladores, en la misma conversación.

**Lo que busco:** Un rol donde pueda construir productos de IA que importen — como ingeniera fundadora, ingeniera de IA aplicada, o consultora de IA fraccional.

---

## QUÉ HE CONSTRUIDO — RESULTADOS CLAVE

| | |
|---|---|
| **12+ productos de IA en producción** | Operando de forma autónoma, 24/7, con $0/mes en infraestructura cloud |
| **99% de reducción de costos** | Entregué sola lo que costaría ~$900K con un equipo tradicional |
| **Usuarios en 19 países** | Suscripciones activas vía PayPal |
| **1.900+ empleos procesados** | Por una IA que aplica, hace seguimiento y sabe cuándo pedir aprobación humana |
| **~$2/mes en AWS** | Sistema serverless que lee 12 productos y entrega un briefing de voz diario |
| **$0.03 por verificación de calidad** | Sistema de pruebas automatizadas que detecta problemas antes de llegar a los usuarios |

---

## EXPERIENCIA PROFESIONAL

### Ingeniera de IA Aplicada y Fundadora
**AIdeazz.xyz** | Panamá / Remoto | 2025 – Presente

---

### VibeJobHunter — Sistema Autónomo de Búsqueda de Empleo

**Qué hace:** Encuentra empleos, los puntúa según compatibilidad, aplica automáticamente y se detiene para pedir aprobación humana solo cuando la decisión es genuinamente dudosa. Sin búsqueda manual. Sin formularios repetitivos. Solo resultados.

**Resultados:** Procesó 1.900+ ofertas de empleo. Generó 250+ aplicaciones personalizadas y 140+ mensajes de outreach. Construido con una capa de pruebas de calidad — 131 verificaciones automatizadas se ejecutan antes de cada actualización, incluyendo una IA que audita de forma independiente la lógica de puntuación para detectar regresiones.

**Cómo funciona (para el lector técnico):** Pipeline LangGraph con estado (StateGraph de 7 nodos) con persistencia de sesión SQLite e interrupción con aprobación humana para puntuaciones límite. Evaluación de 4 capas: scoring por palabras clave, compensación de sesgo, golden set de 22 empleos, y Claude Haiku como juez LLM independiente (umbral ≥75% de acuerdo). Automatización de formularios multi-ATS vía Playwright. Outreach vía API Resend.

*Tech: Python · LangGraph · LangChain · Claude · Playwright · SQLite · Resend · Telegram Bot API*

---

### EspaLuz — Tutor de IA en Español/Inglés (Usuarios de Pago, 19 Países)

**Qué hace:** Un tutor de español/inglés en WhatsApp y Telegram que realmente recuerda a sus estudiantes. En lugar de empezar desde cero en cada sesión, recuerda conversaciones pasadas y muestra contexto relevante automáticamente — como lo haría un buen tutor humano. Los estudiantes pagan una suscripción mensual.

**Resultados:** Activo en 19 países hispanohablantes. Suscripciones PayPal en funcionamiento. Desplegado en WhatsApp y Telegram desde una base de código compartida.

**Cómo funciona (para el lector técnico):** Memoria de 2 capas — historial de conversación LangChain (exactas las últimas 5 conversaciones) + búsqueda semántica sobre el historial completo vía pgvector (embeddings OpenAI, similitud coseno > 0.75). Ambas capas se inyectan en el prompt del sistema de la IA antes de cada respuesta. Espacios de sesión separados por plataforma.

*Tech: Python · GPT-4 · LangChain · pgvector · embeddings OpenAI · Whisper · WhatsApp Business API · Railway*

---

### CTO AIPA — Socio Técnico de IA

**Qué hace:** Un sistema de IA que vigila los 12 productos las 24 horas — revisa cambios de código, señala riesgos de seguridad, y cada mañana a las 8AM entrega un briefing de voz a mi teléfono: qué cambió durante la noche, qué me dije que haría ayer, qué necesita atención hoy.

**Resultados:** Cada cambio de código en 12 repositorios revisado automáticamente. Cada briefing matutino entregado en horario. Las notas de voz grabadas de noche se convierten en parte del audio de la mañana siguiente. Ciclo de retroalimentación completo, totalmente autónomo.

**Cómo funciona (para el lector técnico):** Webhook de GitHub → análisis de seguridad y complejidad → enrutamiento de modelos (Claude para críticos, Groq para estándar). Voz → transcripción Whisper → base de datos Oracle. Sprint Briefing Agent en AWS Lambda: cron de EventBridge a las 8AM Panamá → lee GitHub + Oracle (diario/tareas) vía wallet S3 (conector Oracle thin-mode) → Groq agrupa señales → Claude escribe narrativa → OpenAI TTS genera audio → entrega por Telegram. ~$2/mes.

*Tech: TypeScript · Node.js · Claude · Groq · OpenAI TTS · Oracle Cloud (mTLS) · AWS Lambda · AWS EventBridge · AWS S3 · GitHub API · PM2*

---

### Agente de Marketing IA (CMO AIPA)

**Qué hace:** Escribe y publica contenido bilingüe (inglés/español) diariamente — estratégico, no basado en plantillas. Cuando un producto lanza una nueva funcionalidad, el agente de marketing lo detecta y publica automáticamente sobre ello.

*Tech: Python · FastAPI · Claude · Make.com · Buffer · Railway*

---

### Productos Adicionales

**Atuona Creative AI** (atuona.xyz) — Pipeline creativo de IA: texto → imagen → video → publicación blockchain. *Tech: TypeScript · Node.js · Claude Opus · Replicate · Luma Labs · Thirdweb · Polygon*

**ALGOM Alpha** — Bot de educación cripto e IA en X (@reviceva). *Tech: Node.js · ElizaOS · CCXT · Twitter API*

---

### Cofundadora Operativa
**OmniBazaar** (Marketplace Descentralizado) | Remoto | 2024 – 2025
- Estructuración de DAO LLC (Islas Marshall); diseño de gobernanza, tokenomics y acuerdos DAO

### Subdirectora General y Directora Legal
**JSC "E-GOV OPERATOR"** | Rusia | 2011 – 2018
- Liderazgo de grandes programas de transformación digital para el gobierno regional ruso a nivel de consejo directivo
- Gestión de equipos multidisciplinarios (IT, legal, compliance); programas de tecnología enterprise

### Subdirectora General (Desarrollo de Negocio)
**Fundery LLC** (Fintech/Blockchain) | Rusia | 2017 – 2018
- Cumplimiento ICO, relaciones con inversores, documentación regulatoria, estrategia de lanzamiento blockchain

---

## HABILIDADES TÉCNICAS

*(Para quienes quieren el stack completo)*

**IA y Agentes:** Claude (Opus, Sonnet, Haiku) · OpenAI GPT-4 · Groq (Llama 3.3 70B, Whisper) · LangGraph · LangChain · RAG Semántico (pgvector + embeddings OpenAI) · enrutamiento de modelos · tool calling · orquestación multi-paso · ingeniería de prompts

**Evaluación:** Harness de 4 capas · LLM-como-juez · pruebas de golden set · detección de regresiones

**Lenguajes:** Python · TypeScript · JavaScript · SQL

**Backend:** Node.js · Express · FastAPI · Flask · REST APIs · flujos asíncronos · webhooks

**Frontend:** React 18 + TypeScript + Vite · Tailwind CSS · Framer Motion

**Infraestructura:** PostgreSQL (pgvector) · Oracle Autonomous Database (mTLS) · Oracle Cloud (OCI) · AWS Lambda · AWS EventBridge · AWS S3 · Railway · Supabase · Docker · PM2 · Ubuntu

**Integraciones:** GitHub API · Telegram Bot API · WhatsApp Business API · PayPal · Twitter/X · Playwright · Resend · Make.com · Buffer

**Web3:** Polygon · Thirdweb · IPFS · Smart Contracts

---

## EDUCACIÓN Y CERTIFICACIONES

- **Polkadot Blockchain Academy** (PBA-X Wave #3) | 2025
- **How-To-DAO Cohort Graduate** | 2025
- **Máster en Psicología Social** | Universidad Estatal de Penza | 2018 | Rusia
- **Regulación Blockchain** | MGIMO | 2017 | Moscú
- **Programa Presidencial de Dirección Ejecutiva** | RANEPA | 2015 | Moscú
- **Prácticas** | Nyskapingsparken Innovation Park | Bergen, Noruega

---

## IDIOMAS

Ruso (Nativo) | Inglés (Fluido) | Español (Intermedio) | Francés (Básico)

---

## ROLES OBJETIVO

Ingeniera de IA Aplicada · AI Product Engineer · Founding AI Engineer · Constructora de Herramientas Internas de IA · Consultora de IA Fraccional ($40–70/hr)

Disponible para: Tiempo completo · Medio tiempo · Contrato · Remoto

---

📧 aipa@aideazz.xyz | 📱 +507 616 66 716 (WhatsApp/Telegram) | 🔗 [aideazz.xyz/card](https://aideazz.xyz/card)
