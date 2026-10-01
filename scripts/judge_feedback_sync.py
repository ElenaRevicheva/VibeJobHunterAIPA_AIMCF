"""
judge_feedback_sync.py — the weekly "learn from Elena's real behavior" loop (July 9 2026).

Adapts JobCopilot's "delete jobs you don't like — this trains your copilot" idea to VJH,
honestly: pulls [HIRING-*] deal outcomes from HubSpot and writes the titles Elena
demonstrably ACTED ON vs REJECTED into autonomous_data/judge_feedback.json. The LLM judge
(src/core/llm_judge.py) appends those as few-shot taste-calibration examples to its prompt
— so the judge drifts toward her demonstrated behavior without anyone editing code.

Signal honesty (learned July 9 from the outcome report): the bot itself files new
iron-clad fits into qualifiedtobuy ("I Act TODAY"), so that stage does NOT prove Elena
acted. Only stages she moves deals into by hand count:
  POSITIVE  = presentationscheduled ("I Act this week"), contractsent ("They replied"),
              closedwon ("Won")
  NEGATIVE  = closedlost ("No fit / Rejected / ghosted")

Fail-safe by design:
  - If HubSpot is unreachable or returns nothing, the existing judge_feedback.json is
    LEFT UNTOUCHED (atomic tmp+rename write happens only on success).
  - If the file is absent/invalid, the judge prompt is simply unchanged (see
    _feedback_block in llm_judge.py) — identical to pre-feature behavior.

2026-08-14 — the loop now learns her REASONS, not just her verdicts. A rejected
title teaches the judge nothing; "manual coding required" teaches it a rule. Each
negative carries her own note text, and when her note only points at an attached
screenshot ("look at the image") the screenshot itself is read. See _rejection_reason
and _read_screenshot. Screenshot reading needs the `files` scope on the HubSpot
private app — without it that half is silently skipped and text reasons still work.

Runs DAILY via cron on Oracle (ubuntu crontab) — it is a read-only HubSpot pull, and
a week of her manual triage was sitting unlearned between Sunday runs. Stdlib-only —
no venv dependencies.

Usage:  python3 scripts/judge_feedback_sync.py
Key:    HUBSPOT_API_KEY from env, VJH .env, or /home/ubuntu/cto-aipa/.env (in that order).
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "autonomous_data" / "judge_feedback.json"
# 2026-09-27: permanent memory. Every decision she has made, kept once, forever — the sync used
# to read only the 400 most recently MODIFIED deals (8 days in late Sep: 18 of 370 rejections).
LEDGER = REPO / "autonomous_data" / "judge_decisions.json"
RULES_OUT = REPO / "autonomous_data" / "learned_rules.json"
DB_PATH = REPO / "autonomous_data" / "vibejobhunter.db"
LEDGER_VERSION = 1

POSITIVE_STAGES = {"presentationscheduled", "contractsent", "closedwon"}
NEGATIVE_STAGES = {"closedlost"}

# ── ELENA'S OWN APPLICATIONS: the strongest signal there is (added 2026-08-09) ──
# Her "⏳ Sent" stage is `decisionmakerboughtin`, and it was in NEITHER set — so
# every job she personally chose to apply to was invisible to this loop. 18 deals
# of the clearest possible taste data ("I wanted this one enough to apply"),
# ignored, while the loop trained on 1 positive.
#
# It is NOT enough to count the whole stage: the label is "AI or Elena sent
# outreach", so bot-sent outreach lands here too, and training on the bot's own
# decisions would just teach the judge to agree with itself.
#
# The disambiguator is her note. Verified against the real notes on these deals:
#     "i applied manually"      "i applied."      "Applied ⚠️ MANUAL APPLY..."
# The trap: VJH's OWN note reads "⚠️ MANUAL APPLY REQUIRED — VJH found this; you
# submit", which contains "APPLY". Searching naively marks every deal as applied.
# And she sometimes prepends her word to the bot's note, so excluding notes that
# mention the template would miss those. Therefore: strip the bot's template
# first, then look for a past-tense "applied" in whatever SHE wrote.
MANUAL_APPLY_STAGE = "decisionmakerboughtin"
# Whole notes written by cto-aipa's apply kit (hs-fill-apply-kit.cjs + hand-built kits): skipped, never
# stripped-and-kept, because their prose is long enough to pass as a sentence of hers.
# Also the Aug 2026 "🟡 [BORDERLINE] Promoted to I Act TODAY … at Elena request" note an agent wrote when
# promoting a job: found on a real deal 28 Sep, read as "her reason" (0 ledger entries affected).
# 28 Sep 2026: "🔎 COMPANY BRIEF" — cto-aipa's Perplexity research on the company, one note per deal. It is web
# text about the EMPLOYER ("applied AI", "submitted to the SEC"), so it must never read as her words either.
# 29 Sep 2026: "📌 JOB POSTING" — the note an agent writes when it stages a [HIRING-MANUAL] job by hand
# (cto-aipa hs-fill-apply-kit.cjs JOB_MARK). Long agent prose ("Answer the questions with short, specific
# examples…"), so it must never become her reason or her "applied".
_KIT_NOTE = re.compile(r"🛡️\s*TECHNICAL DEFENSE|✅\s*READY TO SEND|🟡\s*\[BORDERLINE\]\s*Promoted to I Act TODAY"
                       r"|🔎\s*COMPANY BRIEF|📌\s*JOB POSTING"
                       # 29 Sep 2026: the cto-aipa kit's role-specific interview prep, first-person prose
                       # ("I haven't done X yet…") that would otherwise read as HER reason on any rejected deal.
                       r"|🎯\s*ROLE DEFENSE"
                       # 1 Oct 2026: the kit's ready-to-paste Comet browser prompt (her details + letter).
                       r"|📋\s*COMET PROMPT")

_BOT_NOTE_TEMPLATE = re.compile(
    r"manual apply required.*?(?:you submit\.?|apply page)"
    r"|vjh found this[^.]*\.?"
    r"|open job\s*/\s*apply page"
    r"|source:\s*\w+"
    # The Telegram-approval note is ALSO a bot template and was not being stripped —
    # verified on "Machine Learning Engineer @ Micro1", whose only note is this.
    r"|needs manual apply"
    r"|approve in telegram:?\s*\S*"
    r"|score:\s*\d+"
    r"|apply(?:\s+at)?:\s*https?://\S+"
    # Leftovers of the template above. Without these the residual of a bot-only
    # note is "⚠️ Apply:", which is 9 characters and therefore sailed through the
    # length check — every negative came back with "her reason: ⚠️ Apply".
    r"|⚠️|⚠"
    r"|\bapply\s*:"
    r"|\bopen job\b"
    r"|---\s*cover\s*/\s*outreach letter.*"
    # 2026-09-16: VJH's CURRENT cover-letter note, which the line above never matched.
    # 10 of the judge's 12 "rejected" examples carried this bot text as "her reason",
    # so the judge was being taught by VJH's own prose. Strip it to the end of the note.
    r"|cover\s+letter\s*[—–-]+\s*drafted against this posting.*"
    # 2026-09-27: the ingest now writes WHY it parked a job ("🚫 [LEARNED …] Parked, not shown
    # in I Act TODAY … VJH learns from that too."). That is VJH's voice — if she moves such a
    # deal to No fit without writing anything, reading it as her reason would make VJH teach
    # itself. Same for the borderline stamp.
    r"|🚫\s*\[.*?VJH learns from that too\."
    # The Google-Jobs ingest (runs on Bright Data; "SerpAPI"/"SERP" is only its legacy name —
    # SerpAPI was cancelled Aug 2026) still writes "VJH SerpAPI found this job" into the note,
    # which neither pattern above matches — so every SERP-LEAD deal she rejected WITHOUT a
    # note taught the judge "her reason: MANUAL APPLY REQUIRED — VJH SerpAPI found this job".
    # Found by the eval. The literal words are matched because they are what the note says.
    r"|manual apply required\s*[—–-]?\s*vjh serpapi found this job.*?(?:serpapi path\.?|$)"
    r"|🟡\s*\[BORDERLINE\].*?Telegram alert sent\.",
    re.IGNORECASE | re.DOTALL,
)

# Elena does not write one fixed word. Verified against the real notes on her own
# deals, the sync used to see only `\bapplied\b` and therefore threw away
# "I have just submitted manually" (AI Automation & Operations @ Rove Concepts) —
# a genuine application, invisible to the loop purely on vocabulary.
_APPLIED_MARK = re.compile(
    r"\b(applied|submitted|aplicad[oa]|apliqu[ée]|postul[ée]|enviad[oa])\b"
    r"|\bsent (?:it|in|my|the)\b",
    re.IGNORECASE,
)


def _elena_said_applied(notes) -> bool:
    """True only if SHE wrote an 'applied' marker, after removing VJH's template."""
    for n in notes:
        if _KIT_NOTE.search(n.get("body") or ""):
            continue    # agent-written kit / research notes are never her words (same rule as _rejection_reason)
        human = _BOT_NOTE_TEMPLATE.sub(" ", re.sub(r"<[^>]+>", " ", n.get("body") or ""))
        if _APPLIED_MARK.search(human):
            return True
    return False


# ── HER REASONS, NOT JUST HER VERDICTS (added 2026-08-14) ────────────────────
# The loop used to learn the TITLE of a rejected job and nothing else, while the
# actual explanation sat unread in the deal note. Cost, verified in one day's log:
# at 14:32 the judge surfaced "Forward Deployed Engineer @ Blink UX" praising it as
# "hands-on, aligning with Elena's ..." — and she killed it minutes later with
# "manual coding required". The judge had her taste exactly inverted on that axis
# and the correction was already written down.
#
# What survives extraction must be HER voice, not a pasted job posting. Two traps
# seen in production: (1) notes that are just the posting re-pasted (Mercor's
# "Enterprise AI Interface Specialist Save Mercor connects ..."), (2) notes that are
# a bare source URL. Both are stripped or dropped below.
_REASON_MAX = 160
_NAV_NOISE = re.compile(
    r"torre (?:leads? |lead |redirected )?(?:to |here)?\s*(?:linkedin(?: post)?)?"
    r"|look at the image|look -|seems like it is",
    re.IGNORECASE,
)
_POSTING_PASTE = re.compile(
    r"employee count|salary:|per hour|stay tuned|save\b.{0,40}connects",
    re.IGNORECASE,
)


_HIRING_BANNER = re.compile(r"^[^A-Za-z]*(we[''`]?re hiring|now hiring|hiring)\s*[|:–—-]*\s*",
                            re.IGNORECASE)


def _rejection_reason(notes, title: str) -> str:
    """Why a job was a No-fit, already labelled with whose words these are.

    Returns "her reason: ..." when Elena wrote it, or "the posting says: ..." when
    the note is the job description she pasted in. The distinction matters: a pasted
    requirement is still useful evidence, but presenting it as her voice would put
    words in her mouth and teach the judge a preference she never expressed.
    Returns '' when there is nothing usable.
    """
    for n in notes:
        # Notes the cto-aipa apply kit writes are never her voice: the READY letter note and, since
        # 28 Sep 2026, the technical-defense note on every new ACT-TODAY deal. Without this, a defense
        # note read as "the posting says: 🛡️ TECHNICAL DEFENSE …" and MASKED her real reason, and a
        # READY note read as "her reason: ✅ READY TO SEND" (tested on the real templates; 0 ledger
        # entries were affected before the fix).
        if _KIT_NOTE.search(n.get("body") or ""):
            continue
        human = re.sub(r"<[^>]+>", " ", n.get("body") or "")
        human = _BOT_NOTE_TEMPLATE.sub(" ", human)
        human = re.sub(r"https?://\S+", " ", human)          # source links carry no taste
        human = re.sub(r"&[a-z]+;", " ", human)              # &amp; etc from HubSpot HTML
        human = _NAV_NOISE.sub(" ", human)
        human = re.sub(r"\s+", " ", human).strip(" -–—.,:;/|")
        # A length check is not enough — it is what let "⚠️ Apply" through. A real
        # reason is a sentence, so demand at least three actual words.
        if len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", human)) < 3:
            continue
        human = _HIRING_BANNER.sub("", human)       # "🚀 We're Hiring | <title> ..."
        if _POSTING_PASTE.search(human[:120]):
            continue
        # The job's own title inside the opening words means she pasted the posting
        # rather than writing a verdict — keep the requirement, drop the false byline.
        pasted = bool(title) and title[:24].lower() in human[:90].lower()
        label = "the posting says" if pasted else "her reason"
        return f"{label}: {human[:_REASON_MAX].strip()}"
    return ""


# ── THE SCREENSHOT SHE ATTACHES (added 2026-08-14) ───────────────────────────
# When Elena rejects a job she often writes a pointer, not the reason itself —
# "Require experienced engineering - look at the image", "Not a fit. Look at
# requirements" — and attaches a screenshot of the posting's requirements. The
# reason is in the PIXELS. Verified live: 3 of this week's No-fit notes carry an
# attachment (WWT, AlphaLife Sciences, LevelUp Labs).
#
# ⚠️ DORMANT UNTIL A SCOPE IS GRANTED. The private-app token (pat-na1-ccf57) is
# refused by every file endpoint:
#     403 requiredGranularScopes: ["files", "files.read", "files.ui_hidden.read"]
# Until Elena ticks `files` on the private app, _read_screenshot returns "" and
# the loop behaves exactly as if the feature did not exist. Nothing breaks; the
# text reason is used instead. The moment the scope exists this lights up on its
# own with no code change.
#
# Cost control: vision is billed per image, and the same screenshot would be
# re-read on every run forever. Results are cached by HubSpot file id, so each
# screenshot is paid for exactly once.
SHOT_CACHE = REPO / "autonomous_data" / "screenshot_reasons.json"
_VISION_MODEL = "gpt-4o-mini"
# EXTRACT, don't judge. The first version asked which requirement "would disqualify
# her" and allowed NONE — so the WWT screenshot came back empty even though it plainly
# demanded deep computer-vision/robotics experience: the model just didn't frame that
# as a disqualifier. Pulling the requirements out and letting the judge weigh them
# against her criteria is both more reliable and the correct division of labour.
_VISION_PROMPT = (
    "This screenshot shows a job posting. In ONE sentence (max 45 words) state, as written: "
    "WHERE candidates may live or work (countries, regions, citizenship, eligibility, time "
    "zone); whether the post says it is CLOSED or no longer accepting applications; any "
    "stated PAY; and what the role DEMANDS (experience, degree, stack or skills, seniority). "
    "Facts only — no commentary, no preamble. Answer exactly NONE only if this is not a job "
    "posting at all (a chat window, an error page, a photo)."
)
# Bumped whenever _VISION_PROMPT changes, so cached answers from the old prompt are
# discarded instead of silently outliving it.
#   v2 -> v3: "answer NONE if no requirements" made the model bail on postings whose
#   demands are qualitative ("deep experience in computer vision") — WWT and AlphaLife
#   both came back empty. NONE is now about the IMAGE not being a posting at all.
#   v3 -> v4 (2026-09-27): v3 asked only for DEMANDS, so the reason she actually rejected for
#   was dropped: micro1's "Location: Remote (US, CA, UK, IE, AU, NZ)" came back as "no prior AI
#   experience required", and Byldd's "This job post is closed." is not a demand at all.
_VISION_PROMPT_VERSION = 4
_SHOT_MAX = 240
_scope_warned = []


def _load_shot_cache() -> dict:
    try:
        cache = json.loads(SHOT_CACHE.read_text(encoding="utf-8"))
        if cache.get("_prompt_version") != _VISION_PROMPT_VERSION:
            return {"_prompt_version": _VISION_PROMPT_VERSION}   # prompt changed → re-read
        return cache
    except Exception:
        return {"_prompt_version": _VISION_PROMPT_VERSION}


def _save_shot_cache(cache: dict) -> None:
    try:
        SHOT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SHOT_CACHE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(SHOT_CACHE)
    except Exception:
        pass


def _files_key(default_key: str) -> str:
    """Token used for file reads.

    Normally the same token as everything else, and that is the expected setup.

    The credential is NOT a private app — it is a HubSpot **Service Key** named
    `Aideazz_Marketing_Engine` (id 39045903), and its scopes ARE editable at
    Settings → Integrations → Service Keys. Adding `files.read` there is all the
    screenshot reader needs. (Do not go looking under Private Apps or Legacy Apps:
    this account has neither, which is why both pages are empty dead ends.)

    HUBSPOT_FILES_TOKEN therefore exists only as an optional escape hatch — if a
    separate files-only credential is ever preferred, file reads use it and
    everything else keeps the main key. Unset, behaviour is unchanged.
    """
    return (os.environ.get("HUBSPOT_FILES_TOKEN", "").strip()
            or _read_env_file(REPO / ".env", "HUBSPOT_FILES_TOKEN")
            or default_key)


def _file_bytes(key: str, file_id: str):
    """(bytes, mime) for a HubSpot note attachment, or (None, '') if unavailable.

    A 403 here is the missing `files` scope, not a bug — say it once, then stay quiet.
    """
    key = _files_key(key)
    try:
        req = urllib.request.Request(
            f"https://api.hubapi.com/files/v3/files/{file_id}",
            headers={"Authorization": "Bearer " + key},
        )
        meta = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        if "403" in str(e) and not _scope_warned:
            _scope_warned.append(1)
            print("  screenshots SKIPPED — no token with the `files` scope. The original "
                  "private app can no longer be edited (HubSpot migration orphaned it). "
                  "Create a files-read-only private app and put its token in VJH .env as "
                  "HUBSPOT_FILES_TOKEN — nothing else needs to change.")
        return None, ""
    ext = (meta.get("extension") or "").lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        return None, ""
    # NOT meta["url"] — for these attachments that is
    #   api-na1.hubspot.com/filemanager/.../signed-url-redirect
    # which needs the auth header; fetched plain it returns an HTML error page,
    # and base64-ing HTML got OpenAI's "unsupported image" 400. The signed-url
    # endpoint hands back a real CDN link that serves the actual bytes.
    try:
        sreq = urllib.request.Request(
            f"https://api.hubapi.com/files/v3/files/{file_id}/signed-url",
            headers={"Authorization": "Bearer " + key},
        )
        url = json.loads(urllib.request.urlopen(sreq, timeout=20).read()).get("url")
        if not url:
            return None, ""
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
    except Exception:
        return None, ""
    if not raw[:4].startswith((b"\xff\xd8", b"\x89PNG", b"RIFF", b"GIF8")):
        return None, ""      # whatever came back, it is not an image
    if len(raw) > 6_000_000:          # don't post a huge upload to the vision API
        return None, ""
    return raw, "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


def _vision_openai(ok: str, mime: str, b64: str) -> str:
    """One OpenAI vision read. Retries a 429 — 18 reads were lost to 'Too Many Requests'
    before 27 Sep, and a failed read is never cached, so Byldd's screenshot was simply
    never read."""
    payload = json.dumps({
        "model": _VISION_MODEL, "max_tokens": 110, "temperature": 0,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": _VISION_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    }).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=payload, method="POST",
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + ok})
            out = json.loads(urllib.request.urlopen(req, timeout=60).read())
            return (out["choices"][0]["message"]["content"] or "").strip()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(8 * (attempt + 1))
                continue
            raise


def _vision_gemini(gk: str, mime: str, b64: str) -> str:
    """Fallback reader, so one provider's quota cannot blind the loop."""
    model = os.environ.get("GEMINI_JUDGE_MODEL", "").strip() or "gemini-3.5-flash-lite"
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [
            {"text": _VISION_PROMPT}, {"inline_data": {"mime_type": mime, "data": b64}}]}],
        "generationConfig": {"maxOutputTokens": 160, "temperature": 0},
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gk}",
        data=payload, method="POST", headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read())
    parts = ((out.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [{}]
    return (parts[0].get("text") or "").strip()


def _read_screenshot(key: str, file_ids, cache: dict) -> str:
    """What the attached screenshot says (location, closed, pay, demands). '' when unavailable."""
    import base64
    ok = _read_env_file(REPO / ".env", "OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    gk = _read_env_file(REPO / ".env", "GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    for fid in file_ids[:2]:
        if fid in cache:                       # already paid for — never re-read
            if cache[fid]:
                return cache[fid]
            continue
        if not ok and not gk:
            return ""
        raw, mime = _file_bytes(key, fid)
        if not raw:
            continue                           # e.g. the CV PDF on the same note — try the next file
        b64 = base64.b64encode(raw).decode()
        txt, errs = "", []
        for name, fn, k in (("openai", _vision_openai, ok), ("gemini", _vision_gemini, gk)):
            if not k:
                continue
            try:
                txt = fn(k, mime, b64)
                if txt:
                    break
            except Exception as e:
                errs.append(f"{name}: {str(e)[:70]}")
        if not txt:
            print(f"  screenshot {fid}: vision call failed ({'; '.join(errs)[:160]})")
            return ""
        txt = "" if txt.upper().startswith("NONE") else txt[:_SHOT_MAX]
        cache[fid] = txt
        if txt:
            return txt
    return ""


# 6 was starving the judge: 13 deals all-time carry a confirmed applied-by-Elena
# note and 68 sit in No-fit, so five sixths of her demonstrated taste never
# reached the prompt. The prompt is small (~2.8 KB) — there is room.
MAX_EXAMPLES = 12
NOISE = re.compile(r"smoke|delete me|\btest\b", re.IGNORECASE)

# ── TITLE QUALITY FILTERS (added 2026-07-30) ─────────────────────────────────
# Verified defect: the "contractsent" (They replied) stage is fed by the response
# detector, whose deal names are EMAIL SUBJECTS, not job titles. So the judge was
# being taught that these are roles Elena wants:
#     "Invitación actualizada: Meeting mar 20 de ene de 2026 10am"
#     "Action Required: Step 2 of your 10x Application @ 10x-hire"
#     "[AIdeazz] Inquiry — Velena Adam @ Aideazz"
# Few-shot examples like that are pure noise. Two filters now apply to BOTH lists:
#   1. drop anything shaped like an email subject / calendar invite
#   2. keep only titles containing an actual ROLE noun
EMAIL_SUBJECT = re.compile(
    r"^(re|fwd|fw)\b|invitation|invitaci|updated invite|meeting|calendar|"
    r"next steps?|step \d|action required|additional info|your application|"
    r"application (for|received|update)|you'?re invited|thank you for|"
    r"complete your|reminder|follow[- ]?up|zoom|interview with|inquiry",
    re.IGNORECASE,
)
# `coder` and `residence` were added 2026-08-14: "Vibe Coder in Residence — Full
# Time @ Zagged" carried her own "Applied manually" note and was still discarded
# here, purely because no word in this list appeared in the title.
ROLE_NOUN = re.compile(
    # `engineering` needs its own entry: \bengineer\b does NOT match it, so
    # "Forward Deployed Staff (Engineering) @ LevelUp Labs" was silently discarded.
    r"\b(engineer|engineering|developer|architect|specialist|scientist|analyst|designer|"
    r"manager|lead|head|director|consultant|builder|strategist|marketer|"
    r"operations|ops|automation|技術|programmer|administrator|coordinator|"
    r"technician|advisor|officer|founder|cto|pm|product owner|"
    r"coder|residence|generalist|technologist)\b",
    re.IGNORECASE,
)


# A POSITIVE example must not contradict the hard filter. The response detector
# names deals after email subjects, so surviving titles included "1st Interview –
# Full Stack Python Developer" and "Event Confirmation For Senior Full-Stack
# Engineer" — both are titles fit_gate EXCLUDES as heavy hand-coding. Feeding them
# to the judge as "roles she wants" would actively erode the filter it enforces.
# Mirrors src/core/fit_gate.py (kept as a literal list because this script is
# stdlib-only and must run under system python3 with no repo imports).
OFF_LANE_TITLE = re.compile(
    r"full[- ]?stack|backend engineer|front[- ]?end engineer|senior software engineer|"
    r"staff engineer|staff software|principal engineer|"
    r"qa automation|automation qa|test automation|sdet|quality assurance|"
    r"it automation|infrastructure automation|network automation|"
    r"industrial automation|rpa developer|marketing automation|sales automation",
    re.IGNORECASE,
)


def _is_usable_title(title: str, positive: bool = False) -> bool:
    """A few-shot example is only useful if it reads like a real job title.

    `positive=True` additionally requires the title to be on-lane — a bad positive
    is far more damaging than a missing one, since it teaches the judge to approve
    what the gate is built to reject.
    """
    if not title or NOISE.search(title):
        return False
    if EMAIL_SUBJECT.search(title):
        return False
    if not ROLE_NOUN.search(title):
        return False
    if positive and OFF_LANE_TITLE.search(title):
        return False
    return True


def _read_env_file(path: Path, name: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _hubspot_key() -> str:
    return (
        os.environ.get("HUBSPOT_API_KEY", "").strip()
        or _read_env_file(REPO / ".env", "HUBSPOT_API_KEY")
        or _read_env_file(Path("/home/ubuntu/cto-aipa/.env"), "HUBSPOT_API_KEY")
    )


# ── HubSpot I/O ───────────────────────────────────────────────────────────────
DECIDED_STAGES = sorted(POSITIVE_STAGES | NEGATIVE_STAGES | {MANUAL_APPLY_STAGE})


def _hs(key: str, path: str, body=None, timeout: int = 30):
    """One HubSpot call with a 429 retry. A refused call must not read as 'no data'."""
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(5):
        req = urllib.request.Request(
            "https://api.hubapi.com" + path, data=data, method="POST" if body is not None else "GET",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 4:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def _search_deals(key: str) -> list:
    """EVERY decided HIRING deal — by stage, not by recency.

    Until 2026-09-27 this read the 400 most recently MODIFIED deals and stopped. With ~150 new
    deals a week plus note and attachment writes, that window reached back 8 days: 18 of her
    370 rejections were visible, the rest silently forgotten.
    """
    deals, after = [], None
    while True:
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "dealname", "operator": "CONTAINS_TOKEN", "value": "HIRING"},
                {"propertyName": "dealstage", "operator": "IN", "values": DECIDED_STAGES},
            ]}],
            "sorts": [{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            # description carries "Job URL: ..." — the key that links a decision to the posting.
            # closed_lost_reason carries the AUTO-SWEEP label (see _is_auto_swept).
            "properties": ["dealname", "dealstage", "hs_lastmodifieddate", "description", "closed_lost_reason"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        data = _hs(key, "/crm/v3/objects/deals/search", body)
        deals.extend(data.get("results", []))
        after = (data.get("paging") or {}).get("next", {}).get("after")
        if not after or len(deals) >= 9900:      # the search API's own ceiling is 10,000
            break
    return deals


def _fetch_notes_batch(key: str, deal_ids: list) -> dict:
    """{deal_id: [{"body", "attachments"}]} for many deals in a handful of calls."""
    out = {d: [] for d in deal_ids}
    note_of = {}
    for i in range(0, len(deal_ids), 100):
        chunk = deal_ids[i:i + 100]
        try:
            res = _hs(key, "/crm/v4/associations/deals/notes/batch/read",
                      {"inputs": [{"id": d} for d in chunk]}).get("results", [])
        except Exception as e:
            print(f"  note associations unavailable for {len(chunk)} deals ({str(e)[:80]})")
            continue
        for r in res:
            for t in (r.get("to") or [])[:8]:
                note_of.setdefault(str(t.get("toObjectId")), []).append(str(r["from"]["id"]))
    nids = list(note_of)
    for i in range(0, len(nids), 100):
        try:
            res = _hs(key, "/crm/v3/objects/notes/batch/read", {
                "properties": ["hs_note_body", "hs_attachment_ids"],
                "inputs": [{"id": n} for n in nids[i:i + 100]]}).get("results", [])
        except Exception as e:
            print(f"  notes unavailable ({str(e)[:80]})")
            continue
        for n in res:
            props = n.get("properties") or {}
            body = props.get("hs_note_body") or ""
            atts = [a.strip() for a in (props.get("hs_attachment_ids") or "").split(";") if a.strip()]
            if body or atts:
                for d in note_of.get(str(n.get("id")), []):
                    out[d].append({"body": body, "attachments": atts})
    return out


def _fetch_notes(key: str, deal_id: str) -> list:
    """Single-deal form, kept for callers outside this script."""
    return _fetch_notes_batch(key, [deal_id]).get(deal_id, [])


def _clean_title(dealname: str) -> str:
    t = re.sub(r"^\[[A-Za-z0-9_-]+\]\s*", "", dealname or "")  # strip [PREFIX]
    return t.strip()[:90]


def _prefix(dealname: str) -> str:
    m = re.match(r"^\[([A-Za-z0-9_-]+)\]", dealname or "")
    return m.group(1) if m else ""


def _company(dealname: str) -> str:
    t = _clean_title(dealname)
    return t.rsplit(" @ ", 1)[1].strip()[:60] if " @ " in t else ""


def _norm_company(name: str) -> str:
    # Mirrors src/core/learned_rules.norm_company (this script must not import repo code).
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower().replace("%20", " ")).strip()


# ── the ledger: permanent memory of her decisions ─────────────────────────────
def _load_ledger() -> dict:
    try:
        data = json.loads(LEDGER.read_text(encoding="utf-8"))
        return data.get("deals", {}) if data.get("version") == LEDGER_VERSION else {}
    except Exception:
        return {}


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # atomic — a reader never sees a half-written file


_JOB_URL = re.compile(r"Job URL:\s*(\S+)")


def _job_url(description) -> str:
    """The posting URL cto-aipa writes into every hiring deal's description ("Job URL: ...")."""
    m = _JOB_URL.search(description or "")
    return m.group(1).strip() if m else ""


# A clean-up is not her choice (same principle as the June bulk move and the 1 Aug sweep above).
# scripts/sweep_i_act_today.py labels every deal it moves: Closed Lost Reason = "AUTO-SWEEP <date>: …".
# Those never enter the ledger, so a posting that CLOSED cannot mute its company, fill a "she
# rejected" example slot, or lower the weekly precision. Everything she decided is untouched.
_AUTO_SWEEP = "AUTO-SWEEP"


def _is_auto_swept(props: dict) -> bool:
    return props.get("dealstage") in NEGATIVE_STAGES \
        and str(props.get("closed_lost_reason") or "").startswith(_AUTO_SWEEP)


def _update_ledger(key: str, deals: list, old: dict, shot_cache: dict) -> tuple:
    """Refresh the ledger, fetching notes ONLY for deals that are new or changed."""
    now = datetime.now(timezone.utc).isoformat()
    ledger, todo = {}, []
    for d in deals:
        p, did = d.get("properties", {}), str(d.get("id"))
        if _is_auto_swept(p):
            continue                                   # the sweep's decision, not hers
        stage, mod = p.get("dealstage", ""), p.get("hs_lastmodifieddate", "")
        e = old.get(did)
        url = _job_url(p.get("description"))
        if e and e.get("modified") == mod and e.get("stage") == stage:
            ledger[did] = {**e, "url": url or e.get("url")}      # links old entries, no extra call
            continue
        if e and e.get("stage") == stage:
            first = e.get("first_decided") or mod
        else:
            first = mod if not e else now     # first sight: HubSpot's date; a stage change: now
        ledger[did] = {"title": _clean_title(p.get("dealname", "")), "company": _company(p.get("dealname", "")),
                       "prefix": _prefix(p.get("dealname", "")), "stage": stage, "modified": mod,
                       "first_decided": first, "why": "", "applied": None, "url": url}
        if stage in NEGATIVE_STAGES or stage == MANUAL_APPLY_STAGE:
            todo.append(did)
    notes = _fetch_notes_batch(key, todo) if todo else {}
    shots_read = 0
    for did in todo:
        e, ns = ledger[did], notes.get(did, [])
        if e["stage"] == MANUAL_APPLY_STAGE:
            e["applied"] = _elena_said_applied(ns)
            continue
        why = _rejection_reason(ns, e["title"])
        shots = [f for n in ns for f in n.get("attachments", [])]
        if shots:
            shot = _read_screenshot(key, shots, shot_cache)
            if shot:
                shots_read += 1
                why = f"{why}; her screenshot shows: {shot}" if why else f"her screenshot shows: {shot}"
        e["why"] = why
    return ledger, len(todo), shots_read


# ── from her reasons to lessons and rules ─────────────────────────────────────
_LESSON_KINDS = (
    # Wording matters: "Location or eligibility she cannot meet" made the judge reject a job she
    # APPLIED to (Rove Concepts) because its listing was SILENT on location — 2/2 runs. Silence is
    # not a restriction (criterion 2); hard location vetoes live in fit_gate + learned_rules.
    ("location", "A STATED location or eligibility restriction that excludes Panama "
                 "(a listing silent on location is NOT restricted)",
     r"\blocat|\bonly (?:in )?[a-z]+\b|born in|citizen|\busc\b|green card|\bw-?2\b|country|countries|"
     r"india|philippines|colombia|timezone|time zone|region"),
    # 2026-09-28: the label is what the judge READS. "Hand-coding ... required" made it reject the
    # AI Automation / Applied AI roles she applied to as "hands-on coding, not her expertise" —
    # her words were "manual coding required" and "standard CS": coding with AI switched off.
    ("coding", "Manual coding WITHOUT AI, a required CS degree, or a standard software-engineering "
               "seat (coding THROUGH her AI environment is her work — never this lesson)",
     r"coding|coder|experienced engineering|backend|back-end|\bcs\b|computer science|degree|"
     r"standard cs|software engineer|python engineer|developer"),
    ("tool", "Centred on a tool or specialty she does not have",
     r"not an expert in|do not have|don't have|dont have|never used|no experience (?:with|in)"),
    ("closed", "The posting was closed", r"no longer open|job post is closed|closed|expired|no longer available"),
    ("unreliable", "Unreliable listing (a relay that leads to LinkedIn or another site)",
     r"scam|suspicious|leads? (?:to )?linkedin|redirected|torre lead"),
    ("pay", "Pay below her floor", r"salary|\bpay\b|too low|per hour|\$\d"),
)
_CLOSED_EVIDENCE = re.compile(r"no longer open|job post is closed|this job is closed|position is closed|"
                              r"no longer accepting|job has expired|posting has expired|\bpost is closed\b", re.I)
# "the post does NOT state it is closed" (micro1's screenshot) must never teach "closed".
_NEGATED = re.compile(r"\b(?:not|never|no)\b[^.;]{0,25}$", re.I)


def _says_closed(text: str) -> bool:
    for m in _CLOSED_EVIDENCE.finditer(text or ""):
        if not _NEGATED.search(text[max(0, m.start() - 30):m.start()]):
            return True
    return False
_ELIG_EVIDENCE = {
    "born_in": re.compile(r"\bborn in\b", re.I),
    "citizenship": re.compile(r"\busc\b|u\.?s\.? citizen|green card|\bgc\b|citizens? only", re.I),
    "w2_only": re.compile(r"\bw-?2\b", re.I),
}
# "(US, CA, UK)" or "in the US, CA, UK, IE" — two-letter COUNTRY codes only ("(AI, ML)" is not a roster).
_CC_EVIDENCE = r"(?:US|CA|UK|GB|IE|AU|NZ|DE|FR|ES|PT|NL|PL|IN|PH|BR|MX|AR|CO|IL|SG)"
_CODE_LIST_EVIDENCE = re.compile(r"\b" + _CC_EVIDENCE + r"(?:\s*[,/]\s*" + _CC_EVIDENCE + r"){1,}\b")
_TOOL_STATEMENT = re.compile(
    r"(?:not an expert in|do not have|don't have|dont have|never used|no experience (?:with|in))\s+"
    r"([a-z0-9.+\- ]{2,40}?)(?=\s+plus\b|[,;:]|\.\s|\.$|$)", re.I)
_TOOL_STOP = {"this", "it", "that", "these", "them", "experience", "the", "a", "an", "such", "any"}
_OUT_OF_FIELD = re.compile(r"not an expert in this|not my field|not my area|not relevant to me", re.I)
PROTECTED_COMPANIES = {
    "", "name", "company", "confidential", "stealth", "unknown", "linkedin", "torre", "torre ai",
    "micro1", "micro1is", "micro1 io", "toptal", "turing", "mercor", "remotive", "upwork", "getonbrd",
    "get on board", "indeed", "wellfound", "dice", "remoteok", "weworkremotely", "himalayas",
}
MIN_COMPANY_REJECTIONS = 3
# Only her RECENT triage counts toward muting a company: 255 of the 370 rejections are a June bulk
# move with no reasons (possibly a clean-up, not her choice), and "Hiring manager @ — outreach"
# junk deals would otherwise parse as a company called "outreach".
COMPANY_WINDOW_DAYS = 90


def _clean_quote(her: str) -> str:
    """Her own sentence for the prompt — never a job posting she pasted after it."""
    q = re.split(r"\s(?:About the Role|Required Qualifications|What we are looking for)|🚀|we.re hiring",
                 her, maxsplit=1, flags=re.I)[0].strip(" -–—|:;,")
    return q[:80] if len(re.findall(r"[A-Za-z]{2,}", q)) >= 3 else ""


def _split_why(why: str) -> tuple:
    """(her words, what her screenshot shows)."""
    her, _, shot = (why or "").partition("her screenshot shows:")
    her = re.sub(r"^(?:her reason|the posting says):\s*", "", her.strip().rstrip(";")).strip()
    return her, shot.strip()


def _lane_titles_text() -> str:
    """Her declared target titles, read as TEXT (no repo import — system python3)."""
    try:
        return (REPO / "src" / "core" / "target_lanes.py").read_text(encoding="utf-8").lower()
    except Exception:
        return ""


def _build_lessons_and_rules(ledger: dict) -> tuple:
    negs = [e for e in ledger.values() if e["stage"] in NEGATIVE_STAGES]
    pos_companies = {_norm_company(e["company"]) for e in ledger.values()
                     if e["stage"] in POSITIVE_STAGES or e.get("applied")}
    kinds = {k: {"label": lbl, "count": 0, "quotes": [], "taught_by": []} for k, lbl, _ in _LESSON_KINDS}
    rules = {}
    closed, elig, codes_taught, tools, out_field, comp = [], {}, [], {}, [], {}
    lanes_text = _lane_titles_text()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=COMPANY_WINDOW_DAYS)).strftime("%Y-%m-%dT%H:%M:%S")
    with_reason = 0
    for e in sorted(negs, key=lambda x: x.get("modified", ""), reverse=True):
        her, shot = _split_why(e.get("why", ""))
        c = _norm_company(e["company"])
        recent = e.get("first_decided", "") >= cutoff
        if c and recent and not e["company"].startswith(("—", "-")) \
                and not e["title"].lower().startswith("hiring manager"):
            comp.setdefault(c, []).append(e["title"])
        if not her and not shot:
            continue
        with_reason += 1
        label = e["title"][:60]
        for k, _lbl, rx in _LESSON_KINDS:
            if re.search(rx, her, re.I):
                kinds[k]["count"] += 1
                kinds[k]["taught_by"].append(label)
                q = _clean_quote(her)
                if len(kinds[k]["quotes"]) < 2 and q:
                    kinds[k]["quotes"].append(q)
        if _says_closed(her) or _says_closed(shot):
            closed.append(label)
        for code, rx in _ELIG_EVIDENCE.items():
            if rx.search(her) or rx.search(shot):
                elig.setdefault(code, []).append(label)
        if re.search(r"\blocat", her, re.I) and _CODE_LIST_EVIDENCE.search(shot):
            codes_taught.append(label)
        for m in _TOOL_STATEMENT.finditer(her):
            for t in re.split(r"\s+and\s+|/|,", m.group(1).lower()):
                t = t.strip(" .")
                # A tool named in her OWN target titles (Zapier in "Automation Architect
                # (n8n / Make / Zapier)") is never learned as one she does not use.
                if t and t not in _TOOL_STOP and len(t) >= 3 and t not in lanes_text:
                    tools.setdefault(t, []).append(label)
        if _OUT_OF_FIELD.search(her):
            out_field.append(e["title"].split(" @ ")[0])
    if closed:
        rules["closed_posting"] = {"enabled": True, "taught_by": closed}
    if elig:
        rules["eligibility"] = {"patterns": sorted(elig),
                                "taught_by": [t for v in elig.values() for t in v]}
    if codes_taught:
        rules["country_code_list"] = {"enabled": True, "taught_by": codes_taught}
    if tools:
        rules["tools_not_hers"] = {"enabled": True, "tools": sorted(tools),
                                   "taught_by": [t for v in tools.values() for t in v]}
    bad_co = {c: len(v) for c, v in comp.items()
              if len(v) >= MIN_COMPANY_REJECTIONS and c not in PROTECTED_COMPANIES and c not in pos_companies}
    if bad_co:
        rules["rejected_companies"] = {"enabled": True, "companies": sorted(bad_co), "counts": bad_co,
                                       "taught_by": [f"{v[0][:50]} x{len(v)}" for c, v in comp.items() if c in bad_co]}
    if out_field:
        rules["out_of_field_titles"] = {"enabled": True, "titles": out_field, "taught_by": out_field}
    lessons = {"total_rejections": len(negs), "with_reason": with_reason,
               "kinds": {k: v for k, v in kinds.items() if v["count"]}}
    return lessons, rules


def _lessons_text(lessons: dict, rules: dict) -> str:
    """The compact, prompt-ready summary of EVERYTHING she has taught — not 12 examples."""
    lines = [f"From ALL {lessons['total_rejections']} of her rejections "
             f"({lessons['with_reason']} with her stated reason):"]
    for k in sorted(lessons["kinds"], key=lambda x: -lessons["kinds"][x]["count"]):
        v = lessons["kinds"][k]
        q = "; ".join('"' + s + '"' for s in v["quotes"])
        lines.append(f"  - {v['label']} — {v['count']}x" + (f", e.g. {q}" if q else ""))
    if rules.get("tools_not_hers"):
        lines.append("  - Tools she does not use: " + ", ".join(rules["tools_not_hers"]["tools"]))
    if rules.get("rejected_companies"):
        lines.append("  - Companies she has repeatedly rejected: " + ", ".join(rules["rejected_companies"]["companies"]))
    return "\n".join(lines)


# ── the proof it is working: precision of what VJH put in front of her ────────
def _weekly_metrics(ledger: dict) -> list:
    weeks = {}
    for e in ledger.values():
        if not e.get("prefix", "").startswith("HIRING-VJH"):
            continue                                   # only what VJH itself found
        try:
            d = datetime.fromisoformat(e["first_decided"].replace("Z", "+00:00")).date()
        except Exception:
            continue
        wk = (d - timedelta(days=d.weekday())).isoformat()
        w = weeks.setdefault(wk, {"week_start": wk, "applied": 0, "rejected": 0, "replied": 0})
        if e["stage"] in NEGATIVE_STAGES:
            w["rejected"] += 1
        elif e.get("applied") or e["stage"] in ("presentationscheduled", "closedwon"):
            w["applied"] += 1
        elif e["stage"] == "contractsent":
            w["replied"] += 1
    out = sorted(weeks.values(), key=lambda w: w["week_start"])
    for w in out:
        n = w["applied"] + w["rejected"]
        w["precision"] = round(w["applied"] / n, 3) if n else None
    return out


def _write_learning_metrics(weeks: list, rules: dict) -> None:
    """The learning_metrics table existed since Dec 2025 and was written by no code (0 rows)."""
    if not DB_PATH.exists():
        return
    try:
        con = sqlite3.connect(str(DB_PATH))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for w in weeks[-8:]:
            con.execute(
                "INSERT OR REPLACE INTO learning_metrics (id, metric_date, week_start, applications_sent, "
                "responses_received, interviews_scheduled, offers_received, response_rate, top_companies, "
                "ai_insights, recommendations) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"week-{w['week_start']}", now, w["week_start"] + " 00:00:00", w["applied"], w["replied"],
                 0, 0, w["precision"],
                 json.dumps((rules.get("rejected_companies") or {}).get("companies", [])),
                 f"precision {w['precision']} = applied {w['applied']} / (applied + rejected {w['rejected']})",
                 json.dumps(sorted(rules))))
        con.commit()
        con.close()
    except Exception as e:
        print(f"  learning_metrics not written ({str(e)[:80]})")


def _pick_examples(ledger: dict) -> tuple:
    """The 12 + 12 most recent examples, as before — but a rejection WITH her reason is
    preferred over one without (5 reason-less Jerry.ai deals used to take 5 of the 12 slots)."""
    rows = sorted(ledger.values(), key=lambda e: e.get("modified", ""), reverse=True)
    positives, negatives, seen = [], [], set()
    for e in rows:                                   # her own applications first
        if len(positives) >= MAX_EXAMPLES:
            break
        if e["stage"] == MANUAL_APPLY_STAGE and e.get("applied") and _is_usable_title(e["title"], positive=True) \
                and e["title"].lower() not in seen:
            positives.append(e["title"])
            seen.add(e["title"].lower())
    for e in rows:
        if len(positives) >= MAX_EXAMPLES:
            break
        if e["stage"] in POSITIVE_STAGES and _is_usable_title(e["title"], positive=True) and e["title"].lower() not in seen:
            positives.append(e["title"])
            seen.add(e["title"].lower())
    for want_reason in (True, False):
        for e in rows:
            if len(negatives) >= MAX_EXAMPLES:
                break
            if e["stage"] not in NEGATIVE_STAGES or bool(e.get("why")) != want_reason:
                continue
            if not _is_usable_title(e["title"]) or e["title"].lower() in seen:
                continue
            negatives.append(f"{e['title']} — {e['why']}" if e.get("why") else e["title"])
            seen.add(e["title"].lower())
    return positives, negatives


def main() -> int:
    key = _hubspot_key()
    if not key:
        print("no HUBSPOT_API_KEY found — leaving existing feedback file untouched")
        return 1

    deals = _search_deals(key)
    if not deals:
        print("no decided deals returned — existing files untouched")
        return 0
    shot_cache = _load_shot_cache()
    ledger, refreshed, shots_read = _update_ledger(key, deals, _load_ledger(), shot_cache)
    _save_shot_cache(shot_cache)
    _write_json(LEDGER, {"version": LEDGER_VERSION, "updated": datetime.now(timezone.utc).isoformat(),
                         "deals": ledger})
    # Each decision gets the posting it was made on (job_listings), so the judge replay measures
    # the judge on real text. Additive and fail-safe: a failure here changes nothing above.
    try:
        from link_evidence import link_evidence
        ev = link_evidence(ledger)
        print(f"  evidence: {ev['with_url']} decisions carry a URL · {ev['had_evidence'] + ev['linked_now']} "
              f"have the posting ({ev['linked_now']} linked now) · {ev['no_evidence']} without")
    except Exception as ex:
        print(f"  evidence not linked ({str(ex)[:80]})")
    # RAG memory: embed each decided posting once, so the judge can retrieve her verdicts on the
    # postings most like a new one (src/core/decision_memory.py). Fail-safe like the step above.
    try:
        sys.path.insert(0, str(REPO))
        from src.core.decision_memory import index_decisions
        ix = index_decisions(ledger)
        print(f"  memory: {ix['decided_with_posting']} decided postings · {ix['already']} embedded before · "
              f"{ix['embedded_now']} embedded now · {ix['failed']} failed")
    except Exception as ex:
        print(f"  memory not indexed ({str(ex)[:80]})")

    positives, negatives = _pick_examples(ledger)
    lessons, rules = _build_lessons_and_rules(ledger)
    weeks = _weekly_metrics(ledger)

    _write_json(RULES_OUT, {"updated": datetime.now(timezone.utc).isoformat(),
                            "source": "scripts/judge_feedback_sync.py — learned from her own rejections",
                            "rules": rules})
    _write_learning_metrics(weeks, rules)
    _write_json(OUT, {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "judge_feedback_sync.py (hourly cron)",
        "positives": positives,
        "negatives": negatives,
        "lessons": lessons,
        "lessons_text": _lessons_text(lessons, rules),
        "metrics": weeks[-6:],
    })

    n_neg = sum(1 for e in ledger.values() if e["stage"] in NEGATIVE_STAGES)
    print(f"ledger {len(ledger)} decided deals ({n_neg} rejections, {lessons['with_reason']} with her reason) · "
          f"refreshed {refreshed} · screenshots read {shots_read} · rules {sorted(rules)} · "
          f"examples {len(positives)}+/{len(negatives)}-")
    if weeks:
        print("precision by week (applied / applied+rejected, VJH-found only): " +
              " · ".join(f"{w['week_start']} {w['precision']}" for w in weeks[-4:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
