"""
Enhanced Telegram Bot for VibeJobHunter
Interactive commands for job hunting control and status

ADDED: Voice + free-form questions (additive, non-overwriting)
- Voice messages → transcribed with Whisper → answered from real job data
- Text questions (e.g. "what companies did I apply to today?") → honest answers

16 Oct 2026 (Elena, bilingual): answers are grounded in her shared memory (telegram_qa_helper.answer_grounded) and
come back in the language she used; screenshots are read; a voice note in gets a text AND a voice reply, and so does
a typed message that asks for voice. Only her TELEGRAM_CHAT_ID reaches the bot. Model and user text is sent plain.
PDF and Word .docx documents are read from their text layer and answered the same way (handle_document).
"""

import os
import re
import asyncio
import tempfile
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        CallbackQueryHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print(" python-telegram-bot not installed. Install with: pip install python-telegram-bot")

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# 16 Oct 2026 (Elena): the screens say only what really happens today. Checked on Oracle against the code and the
# journal; one copy each, shared by the /command and its button. Telegram Markdown v1: no "_" outside backticks.
# Buttons whose screens showed April data or a fake "0 jobs" (Today, Jobs, Stats, Outreach, Pause, Resume, Status,
# the "coming soon" CMO ones) are off the menu; their handlers are untouched.
# ═══════════════════════════════════════════════════════════════════════════
MENU_TEXT = """📋 *VIBEJOBHUNTER MENU*

💼 *YOUR JOB FLOW — nothing to remember*
1️⃣ New job → the kit fills the HubSpot deal by itself (company note, CV, letter, Comet prompt) → open 🔥 I act today → apply. The daily apply queue and kit alerts arrive here.
2️⃣ Interview booked (LinkedIn, WhatsApp, anywhere) → in the *CTO AIPA bot* send `/research_employer <company>` → if the company has an open job deal, deep research on the company + its products is saved on it and the bot confirms when OpenClaw has it (no deal yet: give Claude Code the posting link first)
3️⃣ In OpenClaw: `/new` → `prep me for <company>` → a mock interview on that company's likely questions, steering clear of what the research says not to claim

Choose an option below:"""

START_TEXT = """🤖 *VibeJobHunter*

I find and screen remote AI jobs every hour and put the good ones in HubSpot 🔥 I act today, where the kit writes your materials. *You apply* — I do not apply or email employers for you.

/menu — your job flow
/workflow — what runs by itself
/manual — what is yours
/help — commands that work"""

WORKFLOW_TEXT = """🔄 *HOW VIBEJOBHUNTER WORKS*

It finds and screens jobs, and the kit writes your materials. *You apply.* It does not apply, fill in forms or email employers for you.

*1️⃣ Finds jobs*: one cycle about every hour
• Job boards of 160 companies (Greenhouse, Ashby, Lever, Workable and more), Himalayas, Get on Board, YC OSS, Hacker News, Dice, RemoteOK, WeWorkRemotely, Remotive, Puente, AI-Native-Builder
• A Google Jobs feed, twice a day. Jobs that pass your rules and the judge go straight into 🔥 I act today with no alert here (the 08:15 queue lists them); borderline ones arrive here as BORDERLINE.
• Off on purpose: Wellfound, AI-Jobs, YC Work at a Startup, LinkedIn (Bright Data). Torre is failing right now.

*2️⃣ Screens them*
• Re-reads the live posting and drops it if closed
• The job must be fully remote, open to LATAM or worldwide, and AI-augmented work, with no posted pay under $3,000/month
• Scores each job: 60+ goes to your learned rules, then an AI judge · 55–59 is shown as a lead · under 55 is dropped. 55–59 leads skip your learned rules and the judge.

*3️⃣ Learns from you*: every hour
It re-reads your decided HubSpot job deals and the reason you gave for each No-fit, including screenshots on the deal. Those reasons become rules and examples for the judge.

*4️⃣ Alerts you here and creates the deal*
📋 Apply yourself (⚠️ UNVERIFIED when the posting could not be read) → a job deal in HubSpot 🔥 I act today

*5️⃣ The kit fills the deal*: every 10 min, from CTO AIPA
🔎 company brief · CV shaped to the posting, or your tailored CV with the reason · ✅ cover letter · 🎯 role defense · 🛡️ technical defense · 📋 Comet prompt

*6️⃣ Mornings*
• 07:55 Panama: closed postings are moved out of 🔥 I act today to Lost
• 08:15 Panama: the apply queue, sent here only when there are new jobs
• 08:45 Panama: a kit alert, sent here only if a deal is missing a piece

*7️⃣ Replies*
Your Zoho and Gmail inboxes are checked every hourly cycle, looking back 24 hours. A reply the AI reads as positive or a question (sometimes an intro or a newsletter, not only employers) goes to HubSpot and is alerted here once. An interview invite with a booking link should do the same; that was added 15 Oct and none has arrived yet.

*8️⃣ Evenings*
• 20:00 Panama: a daily public post on LinkedIn and Instagram, written by the AI (a template only if every model fails), posted without a preview

*👤 Your part*
Apply from 🔥 I act today → move the deal to ⏳ Sent, or to Lost with a reason. Interview booked anywhere → CTO AIPA bot `/research_employer <company>` → OpenClaw `/new`, then `prep me for <company>`.

*Switched off:* auto-apply, ATS form filling and founder emails. The old follow-up emailer still checks but has nothing to send (last one 24 May)."""

MANUAL_TEXT = """👤 *WHAT YOU DO BY HAND*

The bot finds and screens jobs, and the kit writes your materials on the HubSpot deal. *Applying, replying and booking calls are yours.* Nothing is sent for you.

*Every morning*
1️⃣ Open HubSpot → 🔥 I act today. When there are new jobs, the 08:15 Panama apply queue here lists them.
2️⃣ Open a deal and read the 🔎 company brief, 🎯 role defense and 🛡️ technical defense
3️⃣ Apply on the posting with the CV and ✅ cover letter on the deal. The 📋 Comet prompt is there if you use Comet for the form.
4️⃣ ⚠️ UNVERIFIED deal: open the link first and check the job is still open
5️⃣ Move the deal: ⏳ Sent once you have applied, or Lost with one line on why it is not a fit (a screenshot on the deal works too). Within the hour, that reason trains the judge.

*A job you found yourself*
Give the link to Claude Code and it becomes a deal with the same kit. This bot cannot do that.

*When an employer replies*
• The alert comes here. You answer and book the call yourself.
• Whose-turn reminders come at 07:00 Panama in the *CTO AIPA bot*, with a HubSpot task

*Interview booked* (LinkedIn, WhatsApp, email, anywhere)
1️⃣ *CTO AIPA bot:* `/research_employer <company>` → if the company has an open job deal, the research is saved on it and the bot replies "✅ OpenClaw has it now" (no deal yet: give Claude Code the posting link first)
2️⃣ *OpenClaw:* `/new` → `prep me for <company>` → a mock interview on that company's likely questions, steering clear of what the research says not to claim. Add `en español` for a Spanish interview.
3️⃣ After the call, move the deal on in HubSpot"""

HELP_TEXT = """📖 *COMMANDS THAT WORK*

/menu: your 3-step job flow, with buttons
/workflow: what runs by itself, and what is yours
/manual: your steps every morning, when a reply comes, and when an interview is booked
/priority: the YC priority company list. It does not change which jobs reach you. Skip `/priority refresh` and the 🔄 Refresh button on that screen: either freezes the whole bot and the job hunter for up to 2 minutes.
/help: this list
⚠️ The 📘 menu button posts publicly with no preview: LinkedIn and Instagram, plus a Hashnode and dev.to article whenever a CTO update is waiting.

*Arrives here by itself*
• 📋 Apply yourself / ⚠️ UNVERIFIED: a new job, already a HubSpot deal
• 08:15 Panama: the apply queue, only when there are new jobs
• 08:45 Panama: a kit alert, only if a deal is missing a piece
• Replies the AI reads as positive or a question (sometimes an intro or a newsletter, not only employers), once each
• BORDERLINE jobs from the Google Jobs feed, worth your eyes
• After each hourly cycle with new jobs: a cycle summary. Its applications and founder outreach lines read 0 because those features are switched off.
• After 12 empty cycles in a row: an alert that there are 0 new jobs
• On every restart: "AUTONOMOUS ENGINE STARTED". Its promises are old; this screen says what really runs.
• Daily digest around 15:00 Panama. Ignore its Auto-applied, Outreach, Follow-up, Warm Intro and Applied Today lines: those features are off, so they read 0, stay empty or show old data.

*Ask about your jobs* by text, voice note, screenshot or document (PDF or Word .docx), in English or Spanish. Answers come from your live HubSpot job deals, your verified facts and your corrections, and the bot says so when it does not know. A voice note gets a text and a voice reply; when you type, ask for voice ("reply with voice", "respóndeme con voz"). A screenshot of a posting gets fit and gaps, an interviewer's question gets an answer from your verified examples, a recruiter's message gets a reply draft. A PDF or Word document is read the same way, and a contract, NDA or offer gets its key terms, dates, money and the clauses to check (a reading aid, not legal advice). A scan with no text layer, a password-protected file or an old .doc is not guessed at: the bot says so and what to send instead. Russian voice notes are answered in English.

*For company research and interview prep:* CTO AIPA bot `/research_employer <company>` · OpenClaw `prep me for <company>` (English or Spanish)"""


def _menu_keyboard():
    """Only buttons whose screens are true today (16 Oct 2026)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 How it works", callback_data="workflow"),
         InlineKeyboardButton("👤 What is mine", callback_data="manual")],
        [InlineKeyboardButton("🎯 Priority Companies", callback_data="priority")],
        [InlineKeyboardButton("📘 Post publicly NOW (LinkedIn + IG)", callback_data="post_linkedin")],
    ])


# ═══════════════════════════════════════════════════════════════════════════
# THE SAME VOICE RULE in all three bots (Elena, 16 Oct 2026): a voice note in → the answer as text AND a voice note;
# a typed message that asks for voice (voice / voz / audio / "out loud" / "respóndeme con voz", any language) → text
# AND voice; otherwise text only. A product term ("voice agent", "agente de voz") is not a request.
# ═══════════════════════════════════════════════════════════════════════════
_VOICE_WORDS = re.compile(r"\b(voice|voz|voix|audio|aloud|out\s+loud|голос\w*|вслух|аудио)\b", re.IGNORECASE)
_VOICE_PRODUCT_TERMS = re.compile(
    r"\bvoice[\s-]*(agents?|assistants?|ai|bots?|apps?|latency|models?|interfaces?|cloning|actors?|over)\b|"
    r"\b(agentes?|asistentes?|bots?|modelos?|latencia|interfaz)\s+de\s+voz\b", re.IGNORECASE)


def _asks_for_voice(text: str) -> bool:
    """True when a typed message (or a screenshot caption) asks for the answer by voice."""
    if not text:
        return False
    return bool(_VOICE_WORDS.search(_VOICE_PRODUCT_TERMS.sub(" ", text)))


def _for_speech(text: str) -> str:
    """Port of cto-aipa src/telegram-bot.ts forSpeech: no links, code, Markdown, emoji or /commands; at most 1,500
    characters, cut on a sentence end found after character 500."""
    if not text:
        return ""
    s = re.sub(r"```[\s\S]*?```", " ", text)
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"(?m)^\s*/\w+.*$", "", s)
    s = s.replace("_", " ")
    s = re.sub(r"[*`\[\]#>]", "", s)
    try:
        import regex  # stdlib re has no \p{Extended_Pictographic}
        s = regex.sub(r"\p{Extended_Pictographic}|\uFE0F", "", s)
    except ImportError:
        s = re.sub("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", "", s)
    s = "\n".join(l for l in (re.sub(r"[ \t]+", " ", x).strip() for x in s.split("\n")) if l)
    if len(s) <= 1500:
        return s
    cut = s[:1500]
    end = max(cut.rfind(". "), cut.rfind(".\n"), cut.rfind("! "), cut.rfind("? "), cut.rfind("\n"))
    return (cut[:end + 1] if end > 500 else cut[:cut.rfind(" ")]).strip()


# Whisper verbose_json names the language in English words.
_WHISPER_LANG = {"spanish": "es", "english": "en", "russian": "ru", "es": "es", "en": "en", "ru": "ru"}

# Screenshot reader (VJH-3): the vision functions of scripts/judge_feedback_sync.py, given this prompt.
_SCREENSHOT_PROMPT = (
    "On the FIRST line write exactly one of these labels: TYPE: job posting | TYPE: interviewer question | "
    "TYPE: recruiter or employer message | TYPE: other "
    "(interviewer question = a question she must answer: an interview, screening or application-form question). "
    "Then transcribe ALL the text visible in this screenshot, exactly as written and in its original language, "
    "keeping the line breaks. Do not summarise, translate or add anything. On the very last line write exactly: "
    "END OF TEXT")
_SCREENSHOT_KINDS = ("job posting", "interviewer question", "recruiter or employer message", "other")
_SCREENSHOT_MAX_BYTES = 6_000_000     # the same cap as judge_feedback_sync._file_bytes
_JUDGE_SYNC = None


def _judge_sync_module():
    """scripts/judge_feedback_sync.py, loaded once (its main() is guarded; the top level is constants only)."""
    global _JUDGE_SYNC
    if _JUDGE_SYNC is None:
        import importlib.util
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "scripts" / "judge_feedback_sync.py"
        spec = importlib.util.spec_from_file_location("vjh_judge_feedback_sync", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _JUDGE_SYNC = mod
    return _JUDGE_SYNC


def _image_mime(raw: bytes) -> str:
    """The image signature check of judge_feedback_sync._file_bytes, with the mime taken from the magic bytes."""
    head = bytes(raw[:12]) if raw else b""
    if head.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"GIF8"):
        return "image/gif"
    return ""


def _screenshot_kind(label: str) -> str:
    """The vision model's TYPE label → one of _SCREENSHOT_KINDS, by stem ('TYPE: interview question', 'TYPE: posting',
    'TYPE: employer message' all count). '' when the label names no kind at all (not a TYPE label)."""
    label = (label or "").lower()
    for stems, kind in ((("interview",), "interviewer question"),
                        (("recruit", "employer"), "recruiter or employer message"),
                        (("posting", "job", "vacan", "oferta"), "job posting"),
                        (("question", "screening", "pregunta"), "interviewer question"),
                        (("message", "mensaje"), "recruiter or employer message"),
                        (("other", "otro"), "other")):
        if any(s in label for s in stems):
            return kind
    return ""


def _split_screenshot_read(txt: str):
    """(kind, text, cut) from the vision reply. The TYPE line is asked for FIRST, so a long posting cut off at the
    token limit keeps its type; a TYPE line at the end is accepted too. cut = the 'END OF TEXT' line is missing and
    no TYPE line closes the read."""
    lines = (txt or "").strip().splitlines()
    ended = bool(lines) and re.match(r"^\W*END OF TEXT\W*$", lines[-1].strip(), re.IGNORECASE) is not None
    if ended:
        lines = lines[:-1]
    n = len(lines)
    for i in list(range(min(3, n))) + list(range(n - 1, max(n - 4, 2), -1)):
        m = re.match(r"^\W*TYPE\s*:\s*(.+?)\W*$", lines[i], re.IGNORECASE)
        kind = _screenshot_kind(m.group(1)) if m else ""
        if kind:
            body = "\n".join(lines[:i] + lines[i + 1:]).strip()
            return kind, body, (not ended and i < n - 1)
    return "other", "\n".join(lines).strip(), not ended


# ═══════════════════════════════════════════════════════════════════════════
# Documents (16 Oct 2026, Elena: "like Chalán in Pitz"): a PDF or Word .docx is read from its TEXT LAYER with the
# libraries already in the venv (PyPDF2 3.0.1, python-docx 1.2.0), in a thread, and answered like a screenshot. A scan
# with no text layer, a password, a file over 20 MB or another type gets an honest line, never a guess.
# ═══════════════════════════════════════════════════════════════════════════
_DOC_MAX_BYTES = 20_000_000       # Telegram's getFile limit for bots
_DOC_MAX_CHARS = 15_000           # text kept for the answer; the rest is cut and the reply says so
_DOC_MAX_PAGES = 40               # PDF pages read at most
_DOC_MIN_TEXT = 30                # fewer readable characters than this = no text layer (a scan, photos)
_DOCX_MAX_UNZIPPED = 200_000_000  # a .docx's parts together, uncompressed: python-docx loads every part into memory
_PDF_MIME = "application/pdf"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _document_gate(filename: str, mime: str) -> str:
    """Before downloading: 'read' (a PDF or .docx by name or mime, or a file with no extension: its bytes decide),
    'doc' (an old Word .doc) or 'other' (another type by name, e.g. .xlsx)."""
    ext = os.path.splitext(filename or "")[1].lower()
    mime = (mime or "").lower()
    if ext in (".pdf", ".docx") or mime in (_PDF_MIME, _DOCX_MIME):
        return "read"
    if ext == ".doc" or mime == "application/msword":
        return "doc"
    return "other" if ext else "read"


def _document_format(raw: bytes) -> str:
    """'pdf' | 'docx' | 'ole' (an old Word .doc, or any password-protected Office file) | '' — from the bytes, never
    from the name or the mime type the phone attached."""
    head = bytes(raw[:1024]) if raw else b""
    if b"%PDF-" in head:
        return "pdf"
    if head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if head.startswith(b"PK\x03\x04"):
        import io
        import zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                return "docx" if "word/document.xml" in z.namelist() else ""
        except Exception:
            return ""
    return ""


def _pdf_text(raw: bytes) -> dict:
    """PyPDF2: the text of the first _DOC_MAX_PAGES pages, stopping once _DOC_MAX_CHARS are read. A PDF that opens
    with an empty password (copy-restricted only) is read; any other encryption is 'locked'. AES needs PyCryptodome,
    which Oracle's venv does not have: PyPDF2 then raises DependencyError — when opening an AES-256 file, or on every
    page of an AES-128 one — and that is 'locked' too, never 'damaged' or 'a scan'. A page whose extraction raised is
    counted apart from a page with no text ('failed_pages'), so a reader error is never reported as a scan."""
    from io import BytesIO
    from PyPDF2 import PdfReader
    try:
        from PyPDF2.errors import DependencyError
    except ImportError:                   # an older PyPDF2 without it: nothing of that type is ever raised
        class DependencyError(Exception):
            pass
    try:
        reader = PdfReader(BytesIO(raw))
    except DependencyError:               # AES-256 and no crypto library in the venv
        return {"status": "locked"}
    if reader.is_encrypted:
        try:
            opened = reader.decrypt("")
        except Exception:                 # e.g. AES with no crypto library in the venv
            opened = 0
        if not opened:
            return {"status": "locked"}
    total = len(reader.pages)
    parts, chars, read, empty, failed = [], 0, 0, 0, 0
    for i in range(min(total, _DOC_MAX_PAGES)):
        read += 1
        try:
            t = (reader.pages[i].extract_text() or "").strip()
        except DependencyError:           # AES-128 opened with the empty password, but its text needs PyCryptodome
            return {"status": "locked"}
        except Exception as e:
            logger.info(f"📄 PDF page {i + 1} text could not be extracted: {str(e)[:120]}")
            failed += 1
            continue
        if len(re.sub(r"\s+", "", t)) < 3:
            empty += 1
            continue
        parts.append(t)
        chars += len(t)
        if chars > _DOC_MAX_CHARS:
            break
    return {"status": "ok", "text": "\n\n".join(parts), "pages": total, "pages_read": read, "empty_pages": empty,
            "failed_pages": failed}


def _docx_text(raw: bytes) -> dict:
    """python-docx: every paragraph in reading order — body, tables, content controls, text boxes and tracked
    insertions (deleted text and a text box's duplicate fallback copy are skipped). Headers and footers are left out."""
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        # python-docx loads EVERY part into memory, so the whole package is capped, not only the text part
        if (sum(i.file_size for i in z.infolist()) > _DOCX_MAX_UNZIPPED
                or z.getinfo("word/document.xml").file_size > 50_000_000):
            raise ValueError("the .docx is too large uncompressed (a zip bomb, or huge embedded media)")
    import docx
    body = docx.Document(io.BytesIO(raw)).element.body
    lines, chars = [], 0
    for p in body.iter(_W + "p"):
        if next(p.iterancestors(_MC_FALLBACK), None) is not None:
            continue
        bits = []
        for el in p.iter(_W + "t", _W + "tab", _W + "br", _W + "cr"):
            # only this paragraph's own runs: not a tab stop in its properties, not a text box's paragraph inside it
            if el.getparent().tag != _W + "r" or next(el.iterancestors(_W + "p"), None) is not p:
                continue
            bits.append((el.text or "") if el.tag == _W + "t" else ("\t" if el.tag == _W + "tab" else "\n"))
        line = "".join(bits).strip()
        if line:
            lines.append(line)
            chars += len(line) + 1
            if chars > _DOC_MAX_CHARS:
                break
    return {"status": "ok", "text": "\n".join(lines)}


def _read_document(raw: bytes) -> dict:
    """{status, fmt, text, cut, cut_at, pages, pages_read, empty_pages, failed_pages}. status: ok | no_text | locked |
    unreadable | no_reader (PyPDF2 / python-docx missing here) | doc (an old .doc or a password-protected Word file) |
    other (not a PDF or Word file). Blocking: run it in a thread."""
    fmt = _document_format(raw)
    res = {"status": "ok", "fmt": fmt, "text": "", "cut": False, "cut_at": "", "pages": 0, "pages_read": 0,
           "empty_pages": 0, "failed_pages": 0}
    if fmt not in ("pdf", "docx"):
        res["status"] = "doc" if fmt == "ole" else "other"
        return res
    try:
        res.update(_pdf_text(raw) if fmt == "pdf" else _docx_text(raw))
    except ImportError as e:                       # the reader library is missing here: never blame the file
        logger.warning(f"📄 No {fmt} reader installed: {e}")
        res["status"] = "no_reader"
    except Exception as e:
        logger.warning(f"📄 {fmt} could not be opened: {str(e)[:160]}")
        res["status"] = "unreadable"
    if res["status"] != "ok":
        return res
    text = (res["text"] or "").strip()
    if len(re.sub(r"\s+", "", text)) < _DOC_MIN_TEXT:
        # pages the reader failed on are not "a scan": with no text read, that is an unreadable file
        res.update(status="unreadable" if res.get("failed_pages") else "no_text", text="")
        return res
    if len(text) > _DOC_MAX_CHARS:
        text = text[:_DOC_MAX_CHARS]
        space = text.rfind(" ")
        text, res["cut_at"] = (text[:space] if space > _DOC_MAX_CHARS - 200 else text), "chars"
    elif res["pages_read"] < res["pages"]:
        res["cut_at"] = "pages"
    res.update(text=text, cut=bool(res["cut_at"]))
    return res


def _document_problem_reply(status: str, label: str, label_es: str, ext: str = "", pages: int = 0,
                            pages_read: int = 0) -> str:
    """The honest line for a document the bot did not read: what happened and what to send instead. It never says
    anything about the content."""
    if status == "no_text":
        if pages and pages > pages_read:
            where = f"the first {pages_read} of its {pages} pages have"
        elif pages:
            where = f"its {pages} page has" if pages == 1 else f"its {pages} pages have"
        else:
            where = "it has"
        return (f"📄 I opened {label}, but {where} no text I can read: it looks like a scan or photos saved as a "
                "document. I will not guess what it says. Send screenshots of the pages as photos and I will read "
                f"them. / Abrí {label_es}, pero no tiene texto que pueda leer: parece un escaneo o fotos guardadas "
                "como documento. No voy a adivinar su contenido. Envía capturas de las páginas como fotos y las leo.")
    # a file NAMED .pdf/.docx whose bytes are not one must not be called "a .pdf file"
    kind = f"a {ext} file" if ext and ext not in (".pdf", ".docx") else "not a real PDF or Word file"
    # any old Office binary (or a password-protected Office file) looks the same: say Word only when named Word
    word = ext in (".doc", ".docx")
    ole_en = ("an old Word .doc file or a password-protected Word file" if word else
              "an old Office file (.doc, .xls, .ppt) or a password-protected Office file")
    ole_es = "un Word .doc antiguo o un Word con contraseña" if word else         "un archivo de Office antiguo (.doc, .xls, .ppt) o un archivo de Office con contraseña"
    return {
        "too_big": (f"📄 {label} is over 20 MB. Telegram does not let a bot download files that big, so I did not "
                    "read it. Send a smaller file or screenshots of the pages that matter. / "
                    f"{label_es} pesa más de 20 MB: Telegram no deja que un bot descargue archivos tan grandes, así "
                    "que no lo leí. Envía uno más pequeño o capturas de las páginas importantes."),
        "doc": (f"📄 {label} is {ole_en}. I read only PDF and Word "
                ".docx without a password, so I did not read it and I will not guess what it says. Save it as .docx "
                f"or PDF and send it again. / {label_es} es {ole_es}. Solo leo "
                "PDF y Word .docx sin contraseña, así que no lo leí y no voy a adivinar su contenido. Guárdalo como "
                ".docx o PDF y envíalo otra vez."),
        "other": (f"📄 I read PDF and Word .docx documents, screenshots and photos. {label} is {kind}, so I "
                  "did not read it and I will not guess what it says. Send it as a PDF or .docx, or as a screenshot. "
                  f"/ Leo documentos PDF y Word .docx, capturas y fotos. {label_es} es otro tipo de archivo, así que "
                  "no lo leí y no voy a adivinar su contenido. Envíalo como PDF o .docx, o como captura."),
        "locked": (f"📄 {label} is password-protected or encrypted, so I could not open it and I will not guess what "
                   "it says. Send a copy without the password, or screenshots of the pages. / "
                   f"{label_es} tiene contraseña o está cifrado: no pude abrirlo y no voy a adivinar su contenido. "
                   "Envía una copia sin contraseña o capturas de las páginas."),
        "timeout": (f"📄 Reading {label} took too long, so I stopped. I will not guess what it says. Send a smaller "
                    "file or screenshots of the pages that matter. / "
                    f"Leer {label_es} tardó demasiado y paré. No voy a adivinar su contenido. Envía un archivo más "
                    "pequeño o capturas de las páginas importantes."),
        "download": (f"📄 I could not download {label}. Please send it again. / "
                     f"No pude descargar {label_es}. Envíalo otra vez."),
        "no_reader": (f"📄 I cannot read {label} right now: the reader for this file type is missing on the server. "
                      "The file is not the problem, and I will not guess what it says. Send it as a PDF or as "
                      f"screenshots. / No puedo leer {label_es} ahora: falta el lector de este tipo de archivo en el "
                      "servidor. El archivo no tiene la culpa y no voy a adivinar su contenido. Envíalo como PDF o "
                      "como capturas."),
    }.get(status, (f"📄 I could not read {label}: the file looks damaged, or it is not a real PDF or Word file. I "
                   "will not guess what it says. Export it again as PDF, or send screenshots of the pages. / "
                   f"No pude leer {label_es}: el archivo parece dañado o no es un PDF o Word real. No voy a adivinar "
                   "su contenido. Expórtalo otra vez como PDF o envía capturas de las páginas."))


def _document_notes(res: dict, label: str) -> str:
    """Notes the bot adds to the answer itself, so a cut or a scanned page is never left to the model to mention."""
    notes = []
    if res.get("cut"):
        if res.get("cut_at") == "pages":
            part = f"the first {res['pages_read']} of its {res['pages']} pages"
        elif res.get("pages", 0) > res.get("pages_read", 0):
            part = f"the first {_DOC_MAX_CHARS:,} characters, from {res['pages_read']} of its {res['pages']} pages"
        else:
            part = f"the first {_DOC_MAX_CHARS:,} characters"
        notes.append(f"(📄 I read only the first part of {label}: {part}. The rest is not in this answer. / "
                     "Leí solo la primera parte del documento; el resto no está en esta respuesta.)")
    if res.get("empty_pages"):
        verb = "has" if res["empty_pages"] == 1 else "have"
        notes.append(f"(📄 {res['empty_pages']} of the {res['pages_read']} pages I read {verb} no readable text (blank, "
                     "or scans or images), so what they show is not in this answer. Send them as screenshots if they "
                     f"matter. / {res['empty_pages']} de las páginas leídas no tienen texto legible (en blanco, o "
                     "escaneos); envíalas como capturas si importan.)")
    if res.get("failed_pages"):
        verb = "was" if res["failed_pages"] == 1 else "were"
        notes.append(f"(📄 {res['failed_pages']} of the {res['pages_read']} pages I read {verb} not readable: the PDF "
                     "reader failed on them, so what they show is not in this answer. Send them as screenshots if "
                     f"they matter. / {res['failed_pages']} de las páginas leídas no se pudieron leer (falló el lector "
                     "de PDF); envíalas como capturas si importan.)")
    return ("\n\n" + "\n\n".join(notes)) if notes else ""


class EnhancedTelegramBot:
    """
    Interactive Telegram bot for VibeJobHunter
    
    🆕 UPGRADED January 2026: Comprehensive menu system
    
    MAIN MENU COMMANDS:
    /menu - Interactive menu with all options
    /workflow - Visual explanation of how the engine works
    /manual - What YOU need to do (steps that can't be automated)
    /today - Today's complete activity summary
    /outreach - Pending LinkedIn/Twitter messages to send manually
    
    ORIGINAL COMMANDS:
    /start - Welcome message and help
    /jobs - Show top jobs found today
    /stats - Show application statistics
    /apply <company> - Generate materials for a company
    /pause - Pause autonomous job hunting
    /resume - Resume autonomous job hunting
    /keywords <keywords> - Update job search keywords
    /companies - Show tracked companies
    /recent - Show recent applications
    /status - Show system status

    VOICE & QUESTIONS (added, additive):
    - Send a voice message → transcribed with Whisper → answered from real data
    - Type: "What companies did I apply to today?" → honest list from logs
    """
    
    def __init__(self, token: str, chat_id: str, db_helper=None):
        self.token = token
        self.chat_id = chat_id
        self.db_helper = db_helper
        self.is_paused = False
        
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot not installed")
        
        self.app = Application.builder().token(token).build()
        self._register_handlers()
    
    def _chat_lock_filter(self):
        """ONE chat lock built from TELEGRAM_CHAT_ID (16 Oct 2026): answers now carry her pipeline, screenshots and
        voice cost money, and the 📘 button posts publicly. A missing or non-numeric id applies NO lock, so she can
        never be locked out of her own bot."""
        raw = self.chat_id if self.chat_id not in (None, "") else os.getenv("TELEGRAM_CHAT_ID", "")
        try:
            self._allowed_chat_id = int(str(raw).strip())
        except (TypeError, ValueError):
            self._allowed_chat_id = None
            logger.warning("⚠️ TELEGRAM_CHAT_ID is missing or not a number: the VJH bot chat lock is OFF")
            return None
        return filters.Chat(chat_id=self._allowed_chat_id)

    def _chat_allowed(self, update) -> bool:
        """The same lock for updates a filter cannot gate (CallbackQueryHandler takes no filters in PTB 20.7)."""
        allowed = getattr(self, "_allowed_chat_id", None)
        if allowed is None:
            return True
        chat = getattr(update, "effective_chat", None)
        return bool(chat) and chat.id == allowed

    def _register_handlers(self):
        """Register all command handlers"""
        lock = self._chat_lock_filter()
        # CommandHandler's own default is UpdateType.MESSAGES; the lock is added on top of it. No lock → None (default).
        cmd = (filters.UpdateType.MESSAGES & lock) if lock else None

        def locked(f):
            return (f & lock) if lock else f

        # 🆕 NEW MAIN MENU COMMANDS (January 2026)
        self.app.add_handler(CommandHandler("menu", self.cmd_menu, filters=cmd))
        self.app.add_handler(CommandHandler("workflow", self.cmd_workflow, filters=cmd))
        self.app.add_handler(CommandHandler("manual", self.cmd_manual, filters=cmd))
        self.app.add_handler(CommandHandler("today", self.cmd_today, filters=cmd))
        self.app.add_handler(CommandHandler("outreach", self.cmd_outreach, filters=cmd))
        
        # Original commands
        self.app.add_handler(CommandHandler("start", self.cmd_start, filters=cmd))
        self.app.add_handler(CommandHandler("help", self.cmd_help, filters=cmd))
        self.app.add_handler(CommandHandler("jobs", self.cmd_jobs, filters=cmd))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats, filters=cmd))
        self.app.add_handler(CommandHandler("apply", self.cmd_apply, filters=cmd))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause, filters=cmd))
        self.app.add_handler(CommandHandler("resume", self.cmd_resume, filters=cmd))
        self.app.add_handler(CommandHandler("keywords", self.cmd_keywords, filters=cmd))
        self.app.add_handler(CommandHandler("companies", self.cmd_companies, filters=cmd))
        self.app.add_handler(CommandHandler("recent", self.cmd_recent, filters=cmd))
        self.app.add_handler(CommandHandler("status", self.cmd_status, filters=cmd))
        # Priority companies (additive — Feb 2026)
        self.app.add_handler(CommandHandler("priority", self.cmd_priority, filters=cmd))

        # Callback query handler for inline buttons (chat-locked inside handle_callback)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # ADDED: Voice + free-form text (additive — commands unchanged)
        self.app.add_handler(MessageHandler(locked(filters.VOICE), self.handle_voice))
        self.app.add_handler(MessageHandler(locked(filters.TEXT & ~filters.COMMAND), self.handle_freeform_text))
        # ADDED 16 Oct 2026: screenshots (a photo, or an image sent as a file for full resolution)
        self.app.add_handler(MessageHandler(locked(filters.PHOTO | filters.Document.IMAGE), self.handle_photo))
        # ADDED 16 Oct 2026: PDF and Word .docx documents; any other file gets an honest "not read" line instead of
        # silence. After the screenshot handler, so an image sent as a file still goes to handle_photo.
        self.app.add_handler(MessageHandler(
            locked(filters.Document.ALL & ~filters.Document.IMAGE & ~filters.ANIMATION), self.handle_document))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with main menu"""
        await update.message.reply_text(START_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())

    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 NEW MENU COMMANDS (January 2026 Upgrade)
    # ═══════════════════════════════════════════════════════════════════════════

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Interactive main menu with all options"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("📋 /menu command received!")

        try:
            # 16 Oct 2026 (Elena): everything about jobs lives in THIS bot, whichever agent does the work behind it.
            await update.message.reply_text(MENU_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())
            logger.info("📋 /menu response sent successfully!")
        except Exception as e:
            logger.error(f"❌ /menu command error: {e}", exc_info=True)

    async def cmd_workflow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """How the engine really works today"""
        keyboard = [[InlineKeyboardButton("👤 What is mine", callback_data="manual")]]
        await update.message.reply_text(WORKFLOW_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_manual(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show what the user needs to do manually"""
        keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await update.message.reply_text(MANUAL_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def cmd_today(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's complete activity summary"""
        try:
            # Load today's data
            jobs_count = self._count_todays_jobs()
            outreach = self._load_pending_outreach()
            
            now = datetime.utcnow()
            panama_hour = (now.hour - 5) % 24  # UTC-5
            
            message = f"""📊 *TODAY'S ACTIVITY SUMMARY*
📅 {now.strftime('%B %d, %Y')} | {panama_hour}:{now.strftime('%M')} Panama

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🔍 JOB DISCOVERY*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Jobs Found: {jobs_count}
• Sources Checked: 7
• Companies Scanned: 200+

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*🚀 APPLICATIONS*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Auto-Applied: Check /stats
• Materials Generated: ✅
• ATS Forms Filled: ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*📨 YOUR ACTION NEEDED*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• LinkedIn Messages: {len(outreach)} pending
• Use /outreach to see them

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*⏰ NEXT CYCLE*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• In ~{60 - now.minute} minutes
"""
            keyboard = [
                [
                    InlineKeyboardButton("💼 See Jobs", callback_data="jobs"),
                    InlineKeyboardButton("📨 Outreach", callback_data="outreach")
                ],
                [InlineKeyboardButton("🔄 Refresh", callback_data="today")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_outreach(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending LinkedIn/Twitter messages to send manually"""
        try:
            outreach = self._load_pending_outreach()
            
            if not outreach:
                message = """📨 *PENDING OUTREACH*

✅ No pending messages right now!

When the engine finds good opportunities:
• LinkedIn messages will appear here
• You copy-paste and send them
• This is the human touch that wins!

Check back after the next job cycle (~hourly).
"""
            else:
                message = f"""📨 *PENDING OUTREACH*

You have *{len(outreach)}* message(s) to send:

"""
                for i, item in enumerate(outreach[:5], 1):  # Show max 5
                    company = item.get('company', 'Unknown')
                    platform = item.get('platform', 'LinkedIn')
                    contact = item.get('contact', 'Team')
                    url = item.get('url', '#')
                    msg_preview = item.get('message', '')[:100]
                    
                    message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{i}. *{company}* ({platform})
👤 Contact: {contact}
🔗 {url}

📝 Message Preview:
"{msg_preview}..."
"""
                
                message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*HOW TO SEND:*
1. Click the LinkedIn URL above
2. Send connection request
3. Copy the full message from logs
4. Paste as connection note

💡 Tip: Personalize if you can!
"""
            
            keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown', 
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error loading outreach: {str(e)}")
    
    def _load_pending_outreach(self) -> list:
        """Load pending outreach messages from the ACTUAL outreach files"""
        messages = []

        # Source 1: manual_outreach_queue.json (primary — generated by founder_finder)
        try:
            queue_file = "autonomous_data/manual_outreach_queue.json"
            if os.path.exists(queue_file):
                with open(queue_file, 'r') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get('messages', [])
                    for m in items:
                        status = m.get('status', '')
                        if status in ('pending_manual_send', 'pending', ''):
                            messages.append({
                                'company': m.get('company', 'Unknown'),
                                'platform': m.get('platform', 'LinkedIn'),
                                'contact': m.get('contact_name', m.get('contact', 'Founder')),
                                'url': m.get('linkedin_url', m.get('url', '')),
                                'message': m.get('message', m.get('content', '')),
                            })
        except Exception:
            pass

        # Source 2: outreach_log.jsonl (backup — all outreach history)
        if not messages:
            try:
                log_file = "autonomous_data/outreach_log.jsonl"
                if os.path.exists(log_file):
                    pending = []
                    with open(log_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                                if entry.get('status') in ('pending_manual_send', 'pending'):
                                    pending.append({
                                        'company': entry.get('company', 'Unknown'),
                                        'platform': 'LinkedIn',
                                        'contact': entry.get('contact_name', 'Founder'),
                                        'url': entry.get('linkedin_url', ''),
                                        'message': entry.get('message', '')[:300],
                                    })
                            except json.JSONDecodeError:
                                continue
                    # Show most recent 10
                    messages = pending[-10:]
            except Exception:
                pass

        return messages
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed help"""
        await update.message.reply_text(HELP_TEXT, parse_mode='Markdown')

    async def cmd_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show today's top jobs"""
        try:
            # Load today's jobs from cache
            jobs = self._load_recent_jobs()
            
            if not jobs:
                await update.message.reply_text(" No jobs found today yet. Check back in an hour!")
                return
            
            # Sort by match score and take top 5
            top_jobs = sorted(jobs, key=lambda x: x.get('match_score', 0), reverse=True)[:5]
            
            message = f" *Top {len(top_jobs)} Jobs Found Today*\n\n"
            
            for i, job in enumerate(top_jobs, 1):
                company = job.get('company', 'Unknown')
                title = job.get('title', 'Unknown')
                location = job.get('location', 'Remote')
                match_score = job.get('match_score', 0) * 100
                url = job.get('url', '#')
                
                message += f"{i}. *{company}* - {title}\n"
                message += f"    {location} |  {match_score:.0f}% match\n"
                message += f"    [Apply Here]({url})\n\n"
            
            # Add quick action buttons
            keyboard = [
                [
                    InlineKeyboardButton(" Stats", callback_data="stats"),
                    InlineKeyboardButton(" Refresh", callback_data="refresh_jobs")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
        except Exception as e:
            await update.message.reply_text(f" Error loading jobs: {str(e)}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show application statistics"""
        try:
            if not self.db_helper:
                await update.message.reply_text(" Database not connected")
                return
            
            # Get weekly stats
            this_week = self.db_helper.get_weekly_stats(0)
            last_week = self.db_helper.get_weekly_stats(1)
            
            message = " *Your Job Hunting Stats*\n\n"
            message += "*This Week:*\n"
            message += f" Applications: {this_week['applications_sent']}\n"
            message += f" Responses: {this_week['responses_received']}\n"
            message += f" Interviews: {this_week['interviews_scheduled']}\n"
            message += f" Offers: {this_week['offers_received']}\n"
            message += f" Response Rate: {this_week['response_rate']*100:.1f}%\n\n"
            
            message += "*Last Week:*\n"
            message += f" Applications: {last_week['applications_sent']}\n"
            message += f" Responses: {last_week['responses_received']}\n\n"
            
            # Get top companies
            responsive = self.db_helper.get_responsive_companies()[:3]
            if responsive:
                message += "* Most Responsive Companies:*\n"
                for company, rate in responsive:
                    message += f"   {company} ({rate*100:.0f}% response)\n"
            
            # Get ghost companies
            ghosts = self.db_helper.get_ghost_companies()
            if ghosts:
                message += f"\n *Ghost Companies* ({len(ghosts)})\n"
                message += "These companies never respond - avoid them!\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f" Error loading stats: {str(e)}")
    
    async def cmd_apply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate materials for a specific company"""
        if not context.args:
            await update.message.reply_text(
                " Please specify a company name\n"
                "Example: /apply anthropic"
            )
            return
        
        company_name = " ".join(context.args)
        
        await update.message.reply_text(
            f" Generating materials for *{company_name}*...\n"
            "This will take ~30 seconds",
            parse_mode='Markdown'
        )
        
        try:
            # TODO: Call material generation service
            # For now, send placeholder
            message = f" *Materials Ready for {company_name}*\n\n"
            message += " Resume: Tailored for this role\n"
            message += " Cover Letter: Personalized\n"
            message += " Portfolio: Updated links\n\n"
            message += "Next: Apply manually or I can send via email"
            
            keyboard = [
                [
                    InlineKeyboardButton(" Send Email", callback_data=f"send_email_{company_name}"),
                    InlineKeyboardButton(" Save Only", callback_data="save_materials")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Pause autonomous job hunting"""
        self.is_paused = True
        await update.message.reply_text(
            " *Autonomous job hunting PAUSED*\n\n"
            "I'll stop checking for new jobs.\n"
            "Use /resume to restart.",
            parse_mode='Markdown'
        )
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Resume autonomous job hunting"""
        self.is_paused = False
        await update.message.reply_text(
            " *Autonomous job hunting RESUMED*\n\n"
            "I'm back to checking jobs hourly!\n"
            "You'll get alerts for high-match jobs.",
            parse_mode='Markdown'
        )
    
    async def cmd_keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Update job search keywords"""
        if not context.args:
            # Show current keywords
            keywords = self._load_keywords()
            message = " *Current Keywords:*\n" + ", ".join(keywords)
            message += "\n\nTo update: /keywords ML engineer, AI researcher"
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        # Update keywords
        new_keywords = " ".join(context.args).split(",")
        new_keywords = [k.strip() for k in new_keywords]
        
        self._save_keywords(new_keywords)
        
        message = f" *Keywords Updated!*\n\n"
        message += "New keywords:\n" + "\n".join(f"   {k}" for k in new_keywords)
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def cmd_companies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tracked companies"""
        try:
            # Load company list
            companies = self._load_target_companies()
            
            message = " *Tracked Companies*\n\n"
            
            for category, data in companies.items():
                if category == 'filters' or category == 'scraping_config':
                    continue
                
                company_list = data.get('companies', [])
                message += f"*{data.get('description', category)}*\n"
                message += f"  Companies: {len(company_list)}\n\n"
            
            total = sum(len(data.get('companies', [])) for key, data in companies.items() 
                       if key not in ['filters', 'scraping_config'])
            message += f" *Total: {total} companies tracked*"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent applications"""
        try:
            if not self.db_helper:
                await update.message.reply_text(" Database not connected")
                return
            
            # Placeholder - database integration coming soon
            await update.message.reply_text(" No applications tracked yet! Database integration in progress.")
            
        except Exception as e:
            await update.message.reply_text(f" Error: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status"""
        status_emoji = "" if not self.is_paused else ""
        status_text = "RUNNING" if not self.is_paused else "PAUSED"
        
        message = f" *System Status*\n\n"
        message += f"{status_emoji} Mode: *{status_text}*\n"
        message += f" Last Check: {datetime.utcnow().strftime('%H:%M UTC')}\n"
        message += f" Jobs Today: {self._count_todays_jobs()}\n"
        message += f" Next Check: In ~{60 - datetime.utcnow().minute} minutes\n\n"
        
        if self.is_paused:
            message += "Use /resume to restart"
        else:
            message += "Use /pause to stop"
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Priority companies: list, add, remove, sync yc (additive — Feb 2026)"""
        if not self.db_helper:
            await update.message.reply_text("Priority list not available (no database).")
            return
        args = (context.args or []) if context.args else []
        sub = (args[0] or "list").lower() if args else "list"

        try:
            if sub == "list":
                # Sync from export file first (fresh data on manual request)
                path = self._get_priority_export_path()
                if os.path.exists(path):
                    try:
                        self.db_helper.sync_priority_from_yc_file(path)
                    except Exception:
                        pass
                rows = self.db_helper.list_priority_companies()
                total = len(rows)
                ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
                msg = f"🎯 *Priority Companies* ({total})\n\n"
                for r in rows[:30]:
                    msg += f"• {r['company_name']} ({r['source']})\n"
                if total > 30:
                    msg += f"\n... and {total - 30} more"
                msg += f"\n\n_Last updated: {ts}_"
                await update.message.reply_text(msg, parse_mode='Markdown')
            elif sub == "add":
                name = " ".join(args[1:]).strip() if len(args) > 1 else ""
                if not name:
                    await update.message.reply_text("Usage: /priority add <company>")
                    return
                if self.db_helper.add_priority_company(name, "manual"):
                    await update.message.reply_text(f"✅ Added: {name}")
                else:
                    await update.message.reply_text(f"Already in list or invalid: {name}")
            elif sub == "remove":
                name = " ".join(args[1:]).strip() if len(args) > 1 else ""
                if not name:
                    await update.message.reply_text("Usage: /priority remove <company>")
                    return
                if self.db_helper.remove_priority_company(name):
                    await update.message.reply_text(f"✅ Removed: {name}")
                else:
                    await update.message.reply_text(f"Not found or invalid: {name}")
            elif sub == "sync":
                sync_source = (args[1] or "yc").lower() if len(args) > 1 else "yc"
                if sync_source == "yc":
                    path = self._get_priority_export_path()
                    if not os.path.exists(path):
                        await update.message.reply_text(
                            f"📂 Export file not found at {path}. "
                            "Ask OpenClaw for your job shortlist first — it creates the file. Then run /priority sync yc again."
                        )
                        return
                    added, skipped = self.db_helper.sync_priority_from_yc_file(path)
                    await update.message.reply_text(f"✅ Sync YC: {added} added, {skipped} skipped (from {path})")
                else:
                    await update.message.reply_text("Usage: /priority sync yc")
            elif sub == "refresh":
                # Run pipeline + sync for truly fresh data on demand
                await update.message.reply_text("🔄 Refreshing from YC (30–60 sec)...")
                import subprocess
                path = self._get_priority_export_path()
                base = os.path.dirname(path)
                script = os.path.join(base, "run_shortlist.sh")
                if os.path.exists(script):
                    try:
                        subprocess.run(
                            ["bash", script],
                            cwd=base,
                            capture_output=True,
                            timeout=120,
                            env={**os.environ}
                        )
                    except subprocess.TimeoutExpired:
                        await update.message.reply_text("⏱️ Pipeline timed out. Try again.")
                        return
                    except Exception as e:
                        await update.message.reply_text(f"❌ Pipeline error: {str(e)[:100]}")
                        return
                if os.path.exists(path):
                    added, skipped = self.db_helper.sync_priority_from_yc_file(path)
                    rows = self.db_helper.list_priority_companies()
                    total = len(rows)
                    ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
                    msg = f"✅ Refreshed! {added} added, {skipped} skipped.\n\n🎯 *Priority Companies* ({total})\n\n"
                    for r in rows[:30]:
                        msg += f"• {r['company_name']} ({r['source']})\n"
                    if total > 30:
                        msg += f"\n... and {total - 30} more"
                    msg += f"\n\n_Last updated: {ts}_"
                    await update.message.reply_text(msg, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Export file not created. Check job-list-filter path.")
            else:
                await update.message.reply_text(
                    "Usage:\n/priority list\n/priority add <company>\n/priority remove <company>\n/priority sync yc\n/priority refresh"
                )
        except Exception as e:
            logger.exception("cmd_priority error")
            await update.message.reply_text(f"Error: {str(e)[:200]}")

    # ─────────────────────────────────────────────────────────────────────────
    # VOICE + FREE-FORM QUESTIONS (additive)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_language(self, text: str) -> str:
        """
        Very lightweight language detector for voice questions.
        Only distinguishes between EN / ES / RU using simple heuristics.
        """
        if not text:
            return "en"
        # Cyrillic characters → assume Russian
        if any("\u0400" <= ch <= "\u04FF" for ch in text):
            return "ru"
        lower = text.lower()
        # Basic Spanish markers
        spanish_markers = [
            " hola ",
            " buenos dias",
            " buenas tardes",
            " buenas noches",
            " gracias",
            " por favor",
            " que ",
            " porque",
            " para ",
            " contigo",
            " estoy",
            " tengo",
            " quiero",
            " trabajo",
        ]
        if any(m in lower for m in spanish_markers) or any(c in lower for c in ["ñ", "á", "é", "í", "ó", "ú", "ü"]):
            return "es"
        return "en"

    async def _translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translate ES/RU → EN using OpenAI if available.
        Falls back to original text on any error.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not text:
            return text
        # If already English, skip
        if source_lang == "en":
            return text
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                "Translate the following user question into natural English, keeping all job-search-specific details. "
                "Return ONLY the translated English text, no explanations.\n\n"
                f"Original ({source_lang}): {text}"
            )
            # off the event loop: the bot shares it with the hourly job hunt (orchestrator.py create_task)
            resp = await asyncio.to_thread(
                client.chat.completions.create,
                model=os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            translated = resp.choices[0].message.content.strip()
            return translated or text
        except Exception as e:
            logger.warning(f"Translation failed, using original text. Error: {e}")
            return text

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Transcribe voice message with Whisper, then answer from real job data."""
        if not update.message or not update.message.voice:
            return
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            await update.message.reply_text(
                "🎤 Voice works! Add OPENAI_API_KEY to .env for transcription. "
                "Or type your question — I answer job questions from real data."
            )
            return
        try:
            voice = update.message.voice
            tg_file = await context.bot.get_file(voice.file_id)
            tmp_path = None
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp_path = tmp.name
            await tg_file.download_to_drive(tmp_path)

            def _transcribe():
                # verbose_json: Whisper names the language it heard (16 Oct 2026). Sync SDK → run in a thread,
                # because the bot shares one event loop with the hourly job hunt. Client built as before (SDK
                # default timeout and retries), so a long voice note that used to transcribe still does.
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                with open(tmp_path, "rb") as f:
                    return client.audio.transcriptions.create(model="whisper-1", file=f,
                                                              response_format="verbose_json")
            try:
                transcript = await asyncio.to_thread(_transcribe)
                text = transcript.text.strip() if hasattr(transcript, 'text') else str(transcript)
                heard = str(getattr(transcript, "language", "") or "").strip().lower()
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            if not text:
                await update.message.reply_text("Couldn't transcribe the voice message. Try typing your question! / "
                                                "No pude transcribir la nota de voz. ¡Escribe tu pregunta!")
                return
            # Whisper's language first; the old keyword heuristic when Whisper names none, or names a language
            # outside es/en/ru (short Spanish notes come back as "galician", "catalan" or "portuguese").
            lang = _WHISPER_LANG.get(heard) or self._detect_language(text)
            logger.info(f"🎤 Voice transcribed ({lang}): {text[:100]}{'...' if len(text) > 100 else ''}")

            # 16 Oct 2026: Spanish is answered in Spanish (no translation). Russian is still normalised to English,
            # as before (she works in English and Spanish). The echo is plain text: a "_" or "*" in a transcript
            # made Markdown fail and she read "Voice transcription failed" for a formatting error.
            if lang == "ru":
                question = await self._translate_to_english(text, lang)
                echo, q_lang = f"📝 I heard (translated from RU):\n{question}", "en"
            elif lang == "es":
                question, echo, q_lang = text, f"📝 Escuché:\n{text}", "es"
            else:
                question, echo, q_lang = text, f"📝 I heard:\n{text}", ("en" if lang == "en" else None)
            # _reply_plain splits a long transcript under Telegram's 4,096 cap and never raises (it logs).
            if not await self._reply_plain(update, echo):
                logger.warning("Voice echo failed (answering anyway)")

            # Same grounded path as text questions; a voice note in → a voice reply too
            await self._reply_job_question(update, context, question, speak=True, lang=q_lang)
        except Exception as e:
            logger.warning(f"Voice transcription error: {e}")
            await update.message.reply_text(
                f"Voice transcription failed. Try typing: \"What companies did I apply to today?\" / "
                f"No pude transcribir la nota de voz. Escribe, por ejemplo: \"¿A qué empresas apliqué hoy?\""
            )

    async def handle_freeform_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Answer free-form job questions from real data (honest answers)."""
        if not update.message or not update.message.text:
            return
        text = (update.message.text or "").strip()
        if not text:
            return
        await self._reply_job_question(update, context, text)

    async def _reply_job_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str,
                                  speak: Optional[bool] = None, lang: Optional[str] = None):
        """Shared: answer job question and reply.

        16 Oct 2026: the answer is grounded (telegram_qa_helper) and computed in a thread, off the event loop the
        job hunt shares. It goes out as PLAIN text: a model's stray _ or * made Markdown fail and a canned line
        replaced the answer. speak=None applies THE SAME VOICE RULE to the text; handle_voice passes True."""
        try:
            from src.notifications.telegram_qa_helper import answer_job_question
            logger.info(f"📝 QA question: {text[:80]}{'...' if len(text) > 80 else ''}")
            reply = await asyncio.to_thread(answer_job_question, text, lang)
        except Exception as e:
            logger.warning(f"QA reply error: {e}")
            reply = ("Something went wrong answering that. Please ask again in a minute. / "
                     "Algo falló al responder. Vuelve a preguntar en un minuto.")
        sent = await self._reply_plain(update, reply)
        want_voice = _asks_for_voice(text) if speak is None else bool(speak)
        if sent and want_voice:
            await self._speak_reply(update, reply)

    async def _reply_plain(self, update: Update, text: str) -> bool:
        """Send model- or user-written text with NO parse_mode, in pieces under Telegram's 4,096-character cap."""
        try:
            text = text or ""
            for i in range(0, max(len(text), 1), 3900):
                await update.message.reply_text(text[i:i + 3900] or "…")
            return True
        except Exception as e:
            logger.warning(f"Plain reply failed: {e}")
            return False

    async def _speak_reply(self, update: Update, text: str):
        """VJH-4 voice reply: tts-1 / nova / opus — the voice OpenClaw speaks. Called only AFTER the text answer went
        out and fully inside try/except, so a TTS failure never touches the text. Off switch: VJH_SPEAK_REPLIES=0."""
        try:
            if os.getenv("VJH_SPEAK_REPLIES", "1").strip() == "0":
                return
            api_key = os.getenv("OPENAI_API_KEY")
            speech = _for_speech(text)
            if not api_key or not speech:
                return
            from openai import AsyncOpenAI
            # "async with" closes the client's connection pool after each reply (a long-running process).
            async with AsyncOpenAI(api_key=api_key, timeout=30, max_retries=1) as client:
                # The SDK timeout covers the response headers, not the audio body, so the whole call has its own
                # limit.
                resp = await asyncio.wait_for(
                    client.audio.speech.create(model="tts-1", voice="nova", input=speech, response_format="opus"),
                    timeout=45)
                audio = getattr(resp, "content", None)
                if not isinstance(audio, (bytes, bytearray)):
                    audio = await resp.aread()
            if not audio:
                return
            from telegram import InputFile
            await update.message.reply_voice(voice=InputFile(bytes(audio), filename="reply.ogg"))
            logger.info(f"🔊 Voice reply sent ({len(speech)} characters spoken)")
        except Exception as e:
            logger.warning(f"🔊 Voice reply failed (the text answer already went out): {e}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """VJH-3 (16 Oct 2026): a screenshot → its text is read by the vision functions judge_feedback_sync already
        runs in production → the grounded answer (never the keyword router). Never silent: every failure says so."""
        msg = update.message
        if not msg:
            return
        caption = (msg.caption or "").strip()
        try:
            item = msg.photo[-1] if msg.photo else msg.document
            if item is None:
                return
            if (getattr(item, "file_size", 0) or 0) > _SCREENSHOT_MAX_BYTES:
                await msg.reply_text("📸 That image is over 6 MB, too big to read. Please send a smaller screenshot. / "
                                     "La imagen pesa más de 6 MB. Envía una captura más pequeña.")
                return
            tg_file = await context.bot.get_file(item.file_id)
            raw = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.warning(f"📸 Screenshot download failed: {e}")
            await msg.reply_text("📸 I could not download that image. Please send it again. / "
                                 "No pude descargar la imagen. Envíala otra vez.")
            return
        mime = _image_mime(raw)
        if not mime or len(raw) > _SCREENSHOT_MAX_BYTES:
            await msg.reply_text("📸 I can read PNG, JPEG, WebP or GIF screenshots under 6 MB. An iPhone HEIC file: "
                                 "send it as a photo instead. / Leo capturas PNG, JPEG, WebP o GIF de menos de 6 MB; "
                                 "un HEIC de iPhone, envíalo como foto.")
            return
        read = await self._read_screenshot_text(raw, mime)
        if not read:
            await msg.reply_text("📸 I could not read that screenshot just now (the image reader did not answer). "
                                 "Please try again in a minute. / No pude leer la captura ahora; inténtalo en un minuto.")
            return
        kind, extracted, cut = _split_screenshot_read(read)
        logger.info(f"📸 Screenshot read ({kind}, {len(extracted)} chars{', maybe cut' if cut else ''}); "
                    f"caption: {caption[:60]}")
        try:
            from src.notifications.telegram_qa_helper import answer_screenshot
            reply = await asyncio.to_thread(answer_screenshot, caption, kind, extracted, cut)
        except Exception as e:
            logger.warning(f"📸 Screenshot answer error: {e}")
            reply = ("Something went wrong answering that screenshot. Please send it again in a minute. / "
                     "Algo falló al responder la captura. Envíala otra vez en un minuto.")
        # Only when the read is empty, or short AND cut/unlabelled — a short, correctly read interviewer question
        # ("Tell me about yourself") gets no note.
        if msg.photo and (not extracted or (len(extracted) < 80 and (cut or kind == "other"))):
            reply += ("\n\n(📸 Very little text came through. Telegram shrinks photos; send the screenshot as a "
                      "file for full resolution. / Llegó muy poco texto: envía la captura como archivo.)")
        sent = await self._reply_plain(update, reply)
        if sent and _asks_for_voice(caption):
            await self._speak_reply(update, reply)

    async def _read_screenshot_text(self, raw: bytes, mime: str) -> str:
        """OpenAI vision first, Gemini second (judge_feedback_sync._vision_openai / _vision_gemini with this bot's
        prompt). Both are blocking urllib with retries, so each runs in a thread with an overall limit."""
        import base64
        try:
            jfs = _judge_sync_module()
        except Exception as e:
            logger.warning(f"📸 Screenshot reader unavailable: {e}")
            return ""
        b64 = base64.b64encode(raw).decode()
        errs = []
        for name, fn, key in (("openai", jfs._vision_openai, os.getenv("OPENAI_API_KEY", "")),
                              ("gemini", jfs._vision_gemini, os.getenv("GEMINI_API_KEY", ""))):
            if not key:
                errs.append(f"{name}: no key")
                continue
            try:
                txt = await asyncio.wait_for(
                    asyncio.to_thread(fn, key, mime, b64, _SCREENSHOT_PROMPT, 1500), timeout=150)
            except Exception as e:
                errs.append(f"{name}: {str(e)[:100]}")
                continue
            if txt and txt.strip():
                return txt
            errs.append(f"{name}: empty")
        logger.warning(f"📸 Screenshot read failed: {'; '.join(errs)}")
        return ""

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """16 Oct 2026 (Elena: "like Chalán in Pitz"): a PDF or Word .docx → its text layer is read here (PyPDF2 /
        python-docx, in a thread) → the same grounded answer as a screenshot (answer_document). Never silent, never a
        guess: a scan with no text layer, a password, a file over 20 MB or another type (.doc, .xlsx…) each get an
        honest line. An image sent as a file never reaches here: handle_photo is registered first."""
        msg = update.message
        if not msg or not msg.document:
            return
        doc = msg.document
        caption = (msg.caption or "").strip()
        file_name = doc.file_name or ""
        ext = os.path.splitext(file_name)[1].lower()
        name = re.sub(r'[\r\n"]+', " ", file_name).strip()[:80]           # only for showing it
        label, label_es = (f'"{name}"', f'"{name}"') if name else ("that file", "ese archivo")
        gate = _document_gate(file_name, doc.mime_type or "")
        if gate != "read":
            await self._reply_plain(update, _document_problem_reply(gate, label, label_es, ext))
            return
        if (doc.file_size or 0) > _DOC_MAX_BYTES:
            await self._reply_plain(update, _document_problem_reply("too_big", label, label_es, ext))
            return
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            raw = bytes(await tg_file.download_as_bytearray())
        except Exception as e:
            logger.warning(f"📄 Document download failed: {e}")
            await self._reply_plain(update, _document_problem_reply("download", label, label_es, ext))
            return
        try:
            res = await asyncio.wait_for(asyncio.to_thread(_read_document, raw), timeout=90)
        except asyncio.TimeoutError:
            res = {"status": "timeout"}
        except Exception as e:
            logger.warning(f"📄 Document read error: {e}")
            res = {"status": "unreadable"}
        if res.get("status") != "ok":
            logger.info(f"📄 Document not read: {res.get('status')} ({ext or 'no extension'}, {len(raw)} bytes)")
            await self._reply_plain(update, _document_problem_reply(
                res.get("status", ""), label, label_es, ext, res.get("pages", 0), res.get("pages_read", 0)))
            return
        try:
            from src.notifications.telegram_qa_helper import answer_document, _document_kind
            kind = _document_kind(res["text"], file_name)
            what = (f"a PDF, {res['pages']} page{'s' if res['pages'] != 1 else ''}" if res["fmt"] == "pdf"
                    else "a Word .docx") + (f', file name "{name}"' if name else "")
            logger.info(f"📄 Document read ({res['fmt']}, {kind}, {len(res['text'])} chars"
                        f"{', cut' if res['cut'] else ''}); caption: {caption[:60]}")
            reply = await asyncio.to_thread(answer_document, caption, kind, res["text"], res["cut"], what)
        except Exception as e:
            logger.warning(f"📄 Document answer error: {e}")
            reply = ("Something went wrong answering that document. Please send it again in a minute. / "
                     "Algo falló al responder el documento. Envíalo otra vez en un minuto.")
        reply += _document_notes(res, label)
        sent = await self._reply_plain(update, reply)
        if sent and _asks_for_voice(caption):
            await self._speak_reply(update, reply)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug: Print to stdout AND log
        print(f"=== CALLBACK RECEIVED: {update.callback_query.data if update.callback_query else 'None'} ===")
        
        query = update.callback_query
        logger.info(f"🔘 Callback received: {query.data}")
        if not self._chat_allowed(update):
            logger.warning(f"🔒 Callback '{query.data}' from another chat ignored (chat lock)")
            return
        
        try:
            await query.answer()
            chat_id = query.message.chat_id
            logger.info(f"🔘 Processing callback '{query.data}' for chat {chat_id}")
            
            # ═══════════════════════════════════════════════════════════════
            # 🆕 NEW MENU CALLBACKS (January 2026)
            # ═══════════════════════════════════════════════════════════════
            if query.data == "menu":
                await self._send_menu(context, chat_id)
            
            elif query.data == "workflow":
                await self._send_workflow(context, chat_id)
            
            elif query.data == "manual":
                await self._send_manual(context, chat_id)
            
            elif query.data == "today":
                await self._send_today(context, chat_id)
            
            elif query.data == "outreach":
                await self._send_outreach(context, chat_id)
            
            elif query.data == "jobs":
                await self._send_jobs(context, chat_id)
            
            elif query.data == "pause":
                self.is_paused = True
                await context.bot.send_message(chat_id, "⏸️ Job hunting PAUSED. Use /resume to restart.")
            
            elif query.data == "resume_hunting":
                self.is_paused = False
                await context.bot.send_message(chat_id, "▶️ Job hunting RESUMED!")
            
            elif query.data == "status":
                await self._send_status(context, chat_id)
            
            elif query.data == "stats":
                await self._send_stats(context, chat_id)
            
            elif query.data == "priority":
                await self._send_priority_list(context, chat_id)
            
            elif query.data == "priority_sync":
                await self._do_priority_sync(context, chat_id)
            
            elif query.data == "priority_refresh":
                await self._do_priority_refresh(context, chat_id)
            
            # ═══════════════════════════════════════════════════════════════
            # 🚀 CMO AIPA CALLBACKS (LinkedIn + Instagram via Make.com)
            # ═══════════════════════════════════════════════════════════════
            elif query.data == "post_linkedin":
                # Use the actual CMO code instead of direct webhook
                try:
                    from src.notifications.linkedin_cmo_v4 import LinkedInCMO
                    cmo = LinkedInCMO()
                    success = await cmo.post_to_linkedin(post_type="random", language="random")
                    if success:
                        await context.bot.send_message(chat_id, "✅ LinkedIn + Instagram posting triggered via CMO!")
                    else:
                        await context.bot.send_message(chat_id, "❌ CMO posting failed")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"❌ Error: {str(e)}")
            
            elif query.data == "post_instagram":
                import requests
                webhook_url = os.getenv('MAKE_WEBHOOK_URL_LINKEDIN', '')
                if not webhook_url:
                    await context.bot.send_message(chat_id, "❌ MAKE_WEBHOOK_URL_LINKEDIN not set in env")
                    return
                try:
                    response = requests.post(webhook_url, json={
                        "platform": "instagram",
                        "action": "trigger_posting",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    await context.bot.send_message(chat_id, "✅ Instagram posting triggered! Check Make.com scenario.")
                except Exception as e:
                    await context.bot.send_message(chat_id, f"❌ Error: {str(e)}")
            
            elif query.data in ["analytics", "campaign", "generate_image", "header_job", "header_cmo", "header_system"]:
                # Placeholder handlers for CMO features
                await context.bot.send_message(chat_id, f"🚧 Feature '{query.data}' coming soon!")
            
            # ═══════════════════════════════════════════════════════════════
            # ORIGINAL CALLBACKS
            # ═══════════════════════════════════════════════════════════════
            elif query.data == "refresh_jobs":
                await query.edit_message_text("🔄 Refreshing...")
                await self._send_jobs(context, chat_id)
            
            elif query.data.startswith("send_email_"):
                company = query.data.replace("send_email_", "")
                await query.edit_message_text(f"📧 Sending email to {company}...")
            
            elif query.data == "save_materials":
                await query.edit_message_text("💾 Materials saved!")
            
            else:
                logger.warning(f"⚠️ Unknown callback: {query.data}")
                
        except Exception as e:
            logger.error(f"❌ Callback error: {e}", exc_info=True)
            try:
                await context.bot.send_message(query.message.chat_id, f"❌ Error: {str(e)[:100]}")
            except:
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALLBACK HELPER METHODS - Send messages directly via bot
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _send_menu(self, context, chat_id):
        """Send menu via callback — the same screen as /menu"""
        await context.bot.send_message(chat_id, MENU_TEXT, parse_mode='Markdown', reply_markup=_menu_keyboard())

    async def _send_workflow(self, context, chat_id):
        """Send workflow explanation via callback — the same screen as /workflow"""
        keyboard = [[InlineKeyboardButton("👤 What is mine", callback_data="manual")],
                    [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await context.bot.send_message(chat_id, WORKFLOW_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def _send_manual(self, context, chat_id):
        """Send manual tasks via callback — the same screen as /manual"""
        keyboard = [[InlineKeyboardButton("📋 Back to Menu", callback_data="menu")]]
        await context.bot.send_message(chat_id, MANUAL_TEXT, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    async def _send_today(self, context, chat_id):
        """Send today's summary via callback"""
        jobs_count = self._count_todays_jobs()
        outreach = self._load_pending_outreach()
        now = datetime.utcnow()
        panama_hour = (now.hour - 5) % 24
        
        message = f"""📊 *TODAY'S SUMMARY*
📅 {now.strftime('%B %d, %Y')} | {panama_hour}:{now.strftime('%M')} Panama

*🔍 DISCOVERY*
• Jobs Found: {jobs_count}
• Companies: 200+

*📨 YOUR ACTION*
• LinkedIn Messages: {len(outreach)} pending

*⏰ NEXT CYCLE*
• In ~{60 - now.minute} minutes
"""
        keyboard = [
            [InlineKeyboardButton("💼 Jobs", callback_data="jobs"),
             InlineKeyboardButton("📨 Outreach", callback_data="outreach")],
            [InlineKeyboardButton("📋 Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_outreach(self, context, chat_id):
        """Send pending outreach via callback"""
        outreach = self._load_pending_outreach()
        
        if not outreach:
            message = """📨 *PENDING OUTREACH*

✅ No pending messages right now!

The engine generates 1-2 new outreach per day.
Check back after the next job cycle.
"""
        else:
            message = f"""📨 *PENDING OUTREACH*

You have *{len(outreach)}* message(s) to send:

"""
            for i, m in enumerate(outreach[:5], 1):
                company = m.get('company', 'Unknown')
                contact = m.get('contact', 'Founder')
                platform = m.get('platform', 'LinkedIn')
                url = m.get('url', '')
                message += f"{i}. *{company}* → {contact}\n"
                if url:
                    message += f"   🔗 {url}\n"
                message += f"   via {platform}\n\n"

            if len(outreach) > 5:
                message += f"_...and {len(outreach) - 5} more_\n\n"
            message += "Use /outreach for full messages to copy-paste."
        
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_jobs(self, context, chat_id):
        """Send jobs list via callback"""
        jobs = self._load_recent_jobs()
        
        if not jobs:
            message = "💼 No jobs found today yet. Check back in an hour!"
        else:
            top_jobs = sorted(jobs, key=lambda x: x.get('match_score', 0), reverse=True)[:5]
            message = f"💼 *Top {len(top_jobs)} Jobs Today*\n\n"
            
            for i, job in enumerate(top_jobs, 1):
                company = job.get('company', 'Unknown')
                title = job.get('title', 'Unknown')[:30]
                score = job.get('match_score', 0)
                if isinstance(score, float) and score < 1:
                    score = score * 100
                message += f"{i}. *{company}*\n   {title} ({score:.0f}%)\n\n"
        
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_status(self, context, chat_id):
        """Send status via callback"""
        status = "RUNNING ✅" if not self.is_paused else "PAUSED ⏸️"
        now = datetime.utcnow()
        
        message = f"""⚙️ *SYSTEM STATUS*

• Mode: *{status}*
• Time: {now.strftime('%H:%M')} UTC
• Jobs Today: {self._count_todays_jobs()}
• Next Cycle: ~{60 - now.minute} min
"""
        keyboard = [[InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def _send_stats(self, context, chat_id):
        """Send stats via callback — reads real data from local files"""
        jobs_today = self._count_todays_jobs()
        outreach = self._load_pending_outreach()

        # Count total outreach ever sent from log
        total_outreach = 0
        sent_outreach = 0
        try:
            log_file = "autonomous_data/outreach_log.jsonl"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            total_outreach += 1
                            if entry.get('status') not in ('pending_manual_send', 'pending'):
                                sent_outreach += 1
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

        # Count seen jobs (dedup cache)
        seen_jobs = 0
        try:
            seen_file = "autonomous_data/seen_jobs.json"
            if os.path.exists(seen_file):
                with open(seen_file, 'r') as f:
                    data = json.load(f)
                    seen_jobs = len(data) if isinstance(data, (list, dict)) else 0
        except Exception:
            pass

        message = f"""📈 *QUICK STATS*

*🔍 Jobs:*
   Today: {jobs_today}
   Total seen: {seen_jobs}

*📨 Outreach:*
   Pending to send: {len(outreach)}
   Total generated: {total_outreach}
   Completed: {sent_outreach}

_Use /stats for full DB stats (if connected)_
"""
        keyboard = [[InlineKeyboardButton("📊 Today", callback_data="today")],
                    [InlineKeyboardButton("📋 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(chat_id, message, parse_mode='Markdown', reply_markup=reply_markup)
    
    def _get_priority_export_path(self):
        """Resolve path to priority_companies_for_vibejob.json (same logic as sync)."""
        path = os.getenv("PRIORITY_YC_EXPORT_PATH")
        if not path:
            base = os.getenv("OPENCLAW_JOB_LIST_PATH", ".")
            path = os.path.join(base, "priority_companies_for_vibejob.json")
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        if not os.path.exists(path) and os.path.exists("/home/ubuntu/job-list-filter"):
            path = "/home/ubuntu/job-list-filter/priority_companies_for_vibejob.json"
        return path

    async def _send_priority_list(self, context, chat_id):
        """Send priority companies list via menu callback. Syncs from JSON first for fresh data."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        try:
            # Sync from export file first (fresh data on manual click)
            path = self._get_priority_export_path()
            if os.path.exists(path):
                try:
                    self.db_helper.sync_priority_from_yc_file(path)
                except Exception:
                    pass
            rows = self.db_helper.list_priority_companies()
            total = len(rows)
            ts = rows[0]["created_at"].strftime("%Y-%m-%d %H:%M") if rows else "—"
            msg = f"🎯 *Priority Companies* ({total})\n\n"
            for r in rows[:30]:
                msg += f"• {r['company_name']} ({r['source']})\n"
            if total > 30:
                msg += f"\n... and {total - 30} more"
            msg += f"\n\n_Last updated: {ts}_"
            msg += "\n\n_Add/remove:_ /priority add or remove <name>"
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Sync YC", callback_data="priority_sync"),
                    InlineKeyboardButton("🔄 Refresh", callback_data="priority_refresh"),
                ],
                [InlineKeyboardButton("📋 Back to Menu", callback_data="menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception as e:
            logger.exception("_send_priority_list error")
            await context.bot.send_message(chat_id, f"Error: {str(e)[:200]}")
    
    async def _do_priority_sync(self, context, chat_id):
        """Sync from YC export file (callback from button)."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        path = self._get_priority_export_path()
        if not os.path.exists(path):
            await context.bot.send_message(chat_id, f"📂 Export file not found. Ask OpenClaw for job shortlist first, then tap Refresh.")
            return
        try:
            added, skipped = self.db_helper.sync_priority_from_yc_file(path)
            await context.bot.send_message(chat_id, f"✅ Sync YC: {added} added, {skipped} skipped.")
            await self._send_priority_list(context, chat_id)
        except Exception as e:
            logger.exception("_do_priority_sync error")
            await context.bot.send_message(chat_id, f"Error: {str(e)[:150]}")
    
    async def _do_priority_refresh(self, context, chat_id):
        """Run pipeline + sync (callback from button)."""
        if not self.db_helper:
            await context.bot.send_message(chat_id, "Priority list not available (no database).")
            return
        await context.bot.send_message(chat_id, "🔄 Refreshing from YC (30–60 sec)...")
        import subprocess
        path = self._get_priority_export_path()
        base = os.path.dirname(path)
        script = os.path.join(base, "run_shortlist.sh")
        if not os.path.exists(script):
            await context.bot.send_message(chat_id, "❌ run_shortlist.sh not found.")
            return
        try:
            subprocess.run(["bash", script], cwd=base, capture_output=True, timeout=120, env={**os.environ})
        except subprocess.TimeoutExpired:
            await context.bot.send_message(chat_id, "⏱️ Pipeline timed out. Try again.")
            return
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ Pipeline error: {str(e)[:100]}")
            return
        if os.path.exists(path):
            added, skipped = self.db_helper.sync_priority_from_yc_file(path)
            await context.bot.send_message(chat_id, f"✅ Refreshed! {added} added, {skipped} skipped.")
            await self._send_priority_list(context, chat_id)
        else:
            await context.bot.send_message(chat_id, "❌ Export file not created.")
    
    # Helper methods
    
    def _load_recent_jobs(self) -> List[Dict]:
        """Load jobs from recent cache file"""
        cache_dir = "autonomous_data/ats_cache"
        if not os.path.exists(cache_dir):
            return []
        
        # Get most recent cache file
        files = sorted([f for f in os.listdir(cache_dir) if f.endswith('.json')])
        if not files:
            return []
        
        latest_file = os.path.join(cache_dir, files[-1])
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
                return data.get('jobs', [])
        except:
            return []
    
    def _count_todays_jobs(self) -> int:
        """Count jobs found today"""
        jobs = self._load_recent_jobs()
        return len(jobs)
    
    def _load_keywords(self) -> List[str]:
        """Load current search keywords"""
        return ["AI Product Engineer", "Applied LLM Engineer", "Founding Engineer AI", "LLM Engineer", "AI Agent Engineer", "AI Developer Tools Engineer"]
    
    def _save_keywords(self, keywords: List[str]):
        """Save updated keywords"""
        pass
    
    def _load_target_companies(self) -> Dict:
        """Load target companies from JSON"""
        try:
            with open('src/data/target_companies.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    async def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """Send a notification message"""
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            print(f" Failed to send Telegram notification: {e}")
    
    def run(self):
        """Start the bot (blocking)"""
        print(" Starting Enhanced Telegram Bot...")
        self.app.run_polling()
    
    async def start(self):
        """Start the bot asynchronously (non-blocking)"""
        print("🤖 Starting Enhanced Telegram Bot (async mode)...")
        await self.app.initialize()
        await self.app.start()
        # Explicitly include callback_query to ensure button clicks work
        await self.app.updater.start_polling(
            allowed_updates=["message", "callback_query"]
        )
        print("✅ Enhanced Bot polling started (messages + callbacks)")


def create_enhanced_bot(token: str = None, chat_id: str = None, db_helper=None):
    """Create and return bot instance"""
    if token is None:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
    if chat_id is None:
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required")
    
    return EnhancedTelegramBot(token, chat_id, db_helper)


if __name__ == '__main__':
    bot = create_enhanced_bot()
    bot.run()
