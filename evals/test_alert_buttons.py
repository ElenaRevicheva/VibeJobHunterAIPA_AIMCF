"""One-tap job-alert buttons: "⏳ I applied" / "❌ Not a fit". Added 2026-10-18 (Elena).

The path, end to end:
  notify_node sends the "📋 Apply yourself" / "⚠️ UNVERIFIED" alert exactly as before, pushes the deal to cto-aipa
  (crm_hub.push_application_to_crm, now able to hand back the answer), and when cto-aipa names an undecided deal,
  TelegramNotifier.add_alert_buttons sets the alert's reply markup. The text is never edited.
  The VJH bot (telegram_bot_enhanced) takes the tap: ⏳ writes "Applied (via VJH alert button, <date>)" and moves
  the deal to ⏳ Sent; ❌ asks for one line and writes HER words as the note, then ❌ No fit. HubSpot is reached
  through judge_feedback_sync's own _hubspot_key/_hs (the hourly learner's key and call).

What this pins:
  - a button carries the deal id only and fits Telegram's 64-byte callback_data; no deal id = no buttons;
  - crm_hub called WITHOUT `answer` sends the same request and reads nothing (existing callers unchanged);
  - the alert text is byte-identical to the 17 Oct code; a timeout, a refused push or a decided deal = no buttons;
  - the stage is read from HubSpot at tap time and moved only out of an open column: a second tap writes nothing;
  - the ❌ note is exactly her words, read back by the REAL judge_feedback_sync as "her reason: …", and the ⏳ note
    is read as her application — neither matches _KIT_NOTE or is eaten by _BOT_NOTE_TEMPLATE;
  - only her chat can tap, and an ordinary message still goes to the Q&A;
  - review fixes: the ⏳ stamp never becomes "her reason" once that deal goes to ❌ No fit (rejected or ghosted
    after she applied) and never hides a reason she writes later, yet still counts as her application on ⏳ Sent;
    ⏳ withdraws an open ❌ question; ❌ on two alerts keeps both questions; a plain message with two fresh
    questions saves nothing; a swipe-reply to the alert counts; the ❌ question promises "VJH learns from it"
    only while the deal is under the learner's per-deal note cap.

No network, no HubSpot writes, no Telegram sends, no model calls, $0: HubSpot is an in-memory fake behind
telegram_bot_enhanced._alert_hs, Telegram is a recording fake, cto-aipa is a fake urlopen.
"""
import asyncio
import importlib.util
import json
import re
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAT = 4242
OTHER_CHAT = 9999
DEAL = "41234567890"                      # an 11-digit HubSpot deal id, the shape real ids have
NAME = "[HIRING-VJH-LEAD] AI Experience Engineer @ Upgrade"
TITLE = "AI Experience Engineer @ Upgrade"


def _jfs():
    """The REAL learner, loaded the way the bot loads it."""
    spec = importlib.util.spec_from_file_location("jfs_alert_buttons", ROOT / "scripts" / "judge_feedback_sync.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ═══════════════════════════════════════════════════════════════════════════
# 1. The buttons themselves
# ═══════════════════════════════════════════════════════════════════════════
def test_buttons_carry_only_the_deal_id_and_fit_64_bytes():
    from src.notifications.telegram_notifier import alert_button_rows, ALERT_CB_APPLIED, ALERT_CB_NOFIT
    rows = alert_button_rows(DEAL)
    assert rows == [[("⏳ I applied", "vjh_ap:" + DEAL), ("❌ Not a fit", "vjh_nf:" + DEAL)]]
    for _label, data in rows[0]:
        assert len(data.encode("utf-8")) <= 64
    assert (ALERT_CB_APPLIED, ALERT_CB_NOFIT) == ("vjh_ap:", "vjh_nf:")


@pytest.mark.parametrize("bad", ["", None, "abc", "123abc", "١٢٣", "4" * 60, "12 34"])
def test_no_usable_deal_id_means_no_buttons(bad):
    from src.notifications.telegram_notifier import alert_button_rows
    assert alert_button_rows(bad) == []


def test_the_bot_dispatches_the_same_prefixes_the_notifier_writes():
    from src.notifications.telegram_notifier import ALERT_CB_APPLIED, ALERT_CB_NOFIT
    src = (ROOT / "src" / "notifications" / "telegram_bot_enhanced.py").read_text(encoding="utf-8")
    assert f'query.data.startswith(("{ALERT_CB_APPLIED}", "{ALERT_CB_NOFIT}"))' in src


# ═══════════════════════════════════════════════════════════════════════════
# 2. crm_hub hands back cto-aipa's answer only when asked
# ═══════════════════════════════════════════════════════════════════════════
class _Resp:
    def __init__(self, body: bytes, status: int = 200):
        self.status, self._body, self.reads = status, body, 0

    def read(self):
        self.reads += 1
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _crm(monkeypatch, body: bytes, status: int = 200):
    import src.langgraph_pipeline.crm_hub as crm_hub
    monkeypatch.setenv("OUTREACH_SECRET", "test-secret")
    sent = []

    def fake_urlopen(req, timeout=None):
        r = _Resp(body, status)
        sent.append({"url": req.full_url, "data": req.data, "headers": dict(req.header_items()),
                     "timeout": timeout, "resp": r})
        return r
    monkeypatch.setattr(crm_hub, "urlopen", fake_urlopen)
    return crm_hub, sent


ANSWER_NEW = {"ok": True, "pipeline": "hiring", "hubspot": {"contactId": None, "companyId": "7", "dealId": DEAL},
              "duplicate": False, "dealId": DEAL}
KW = dict(job_title="AI Experience Engineer", company="Upgrade", job_url="https://example.com/job/1",
          stage="applied", source="vjh_review", notes="⚠️ NEEDS MANUAL APPLY", source_prefix="HIRING-VJH-LEAD")


def test_crm_without_answer_sends_the_same_request_and_reads_nothing(monkeypatch):
    crm_hub, sent = _crm(monkeypatch, json.dumps(ANSWER_NEW).encode())
    assert crm_hub.push_application_to_crm(**KW) is True
    assert sent[0]["resp"].reads == 0                      # the old code never read the body; neither does this
    box = {}
    assert crm_hub.push_application_to_crm(**KW, answer=box) is True
    assert sent[1]["resp"].reads == 1
    assert box == ANSWER_NEW
    a, b = sent
    assert (a["url"], a["data"], a["headers"], a["timeout"]) == (b["url"], b["data"], b["headers"], b["timeout"])


def test_crm_unreadable_answer_leaves_the_box_empty_and_still_reports_success(monkeypatch):
    crm_hub, _ = _crm(monkeypatch, b"<html>proxy page</html>")
    box = {}
    assert crm_hub.push_application_to_crm(**KW, answer=box) is True
    assert box == {}


def test_crm_refused_push_fills_nothing(monkeypatch):
    crm_hub, _ = _crm(monkeypatch, json.dumps({"error": "x"}).encode(), status=500)
    box = {}
    assert crm_hub.push_application_to_crm(**KW, answer=box) is False
    assert box == {}


@pytest.mark.parametrize("answer,want", [
    (ANSWER_NEW, DEAL),
    ({"ok": True, "hubspot": {"dealId": DEAL}, "duplicate": True, "decided": False, "stage": "qualifiedtobuy",
      "dealId": DEAL}, DEAL),                                                   # an open repeat: buttons
    ({"ok": True, "hubspot": {"dealId": DEAL}, "duplicate": True, "decided": True, "stage": "closedlost",
      "dealId": DEAL}, ""),                                                     # she already decided: none
    ({"ok": True, "pipeline": "hiring", "hubspot": None}, ""),                  # HubSpot wrote no deal
    ({"hubspot": {"dealId": DEAL}}, ""),                                        # no ok:true
    ({"ok": True, "dealId": "not-a-number"}, ""),
    ({}, ""),                                                                   # timeout: the box stayed empty
    (None, ""),
])
def test_deal_id_from_the_crm_answer(answer, want):
    from src.langgraph_pipeline.nodes import _alert_deal_id
    assert _alert_deal_id(answer) == want


# ═══════════════════════════════════════════════════════════════════════════
# 3. notify_node: the alert text is untouched, the buttons follow the deal id
# ═══════════════════════════════════════════════════════════════════════════
URL = "https://example.com/job/1"
# Copied from notify_node at d51fe5f (what Oracle runs on 18 Oct). Byte-for-byte: the buttons must not change it.
APPLY_YOURSELF = (
    "<b>📋 Apply yourself</b>: Upgrade\n"
    "Role: AI Experience Engineer | Score: 91\n"
    "Fits your filter (remote · LATAM · AI-augmented). Open it and apply.\n"
    f"<a href='{URL}'>Open posting</a>\n"
    "<i>Now in your HubSpot “I Act TODAY”.</i>"
)
UNVERIFIED = (
    "<b>⚠️ UNVERIFIED — worth 30 seconds</b>: Upgrade\n"
    "Role: AI Experience Engineer\n"
    "I could NOT read this posting (the page returned too little text), "
    "so remote/LATAM/pay are UNCHECKED. The title is in your lane, "
    "so you decide.\n"
    f"<a href='{URL}'>Open posting</a>\n"
    "<i>In HubSpot “I Act TODAY”, flagged unverified.</i>"
)


class _FakeNotifier:
    sent, buttons, send_ok = [], [], True

    def __init__(self, *a, **k):
        self.last_message_id = None

    async def send_message(self, msg, *a, **k):
        _FakeNotifier.sent.append(msg)
        if _FakeNotifier.send_ok:
            self.last_message_id = 777
            return True
        return False

    async def add_alert_buttons(self, message_id, deal_id):
        _FakeNotifier.buttons.append((message_id, deal_id))
        return True


def _notify(monkeypatch, state, answer):
    import src.notifications as notifications
    import src.langgraph_pipeline.crm_hub as crm_hub
    from src.langgraph_pipeline.nodes import notify_node
    _FakeNotifier.sent, _FakeNotifier.buttons = [], []
    calls = []

    def fake_push(**kw):
        calls.append(kw)
        if answer is not None and kw.get("answer") is not None:
            kw["answer"].update(answer)
        return answer is not None
    monkeypatch.setattr(notifications, "TelegramNotifier", _FakeNotifier)
    monkeypatch.setattr(crm_hub, "push_application_to_crm", fake_push)
    out = asyncio.run(notify_node(dict(state)))
    return out, calls


STATE = {"status": "human_pending", "company": "Upgrade", "title": "AI Experience Engineer", "score": 90.9,
         "url": URL, "job_id": "vjh_wwr_1", "gate_reason": "passed"}


def test_apply_yourself_alert_text_is_byte_identical_and_gets_buttons(monkeypatch):
    out, calls = _notify(monkeypatch, STATE, ANSWER_NEW)
    assert _FakeNotifier.sent == [APPLY_YOURSELF]
    assert _FakeNotifier.buttons == [(777, DEAL)]
    assert out == {"telegram_sent": True, "status": "human_pending"}
    assert calls[0]["source_prefix"] == "HIRING-VJH-LEAD" and calls[0]["stage"] == "applied"


def test_unverified_alert_text_is_byte_identical_and_gets_buttons(monkeypatch):
    out, calls = _notify(monkeypatch, {**STATE, "unverified": True}, ANSWER_NEW)
    assert _FakeNotifier.sent == [UNVERIFIED]
    assert _FakeNotifier.buttons == [(777, DEAL)]
    assert calls[0]["source_prefix"] == "HIRING-VJH-UNVERIFIED"


@pytest.mark.parametrize("answer", [
    None,                                                          # cto-aipa timed out (3 of 18 since 1 Aug)
    {"ok": True, "pipeline": "hiring", "hubspot": None},           # HubSpot wrote no deal
    {"ok": True, "hubspot": {"dealId": DEAL}, "duplicate": True, "decided": True, "dealId": DEAL},
])
def test_no_deal_id_no_buttons_and_the_alert_is_unchanged(monkeypatch, answer):
    _notify(monkeypatch, STATE, answer)
    assert _FakeNotifier.sent == [APPLY_YOURSELF]
    assert _FakeNotifier.buttons == []


def test_a_failed_telegram_send_gets_no_buttons(monkeypatch):
    monkeypatch.setattr(_FakeNotifier, "send_ok", False)
    _notify(monkeypatch, STATE, ANSWER_NEW)
    assert _FakeNotifier.buttons == []


def test_other_statuses_never_get_buttons(monkeypatch):
    _notify(monkeypatch, {**STATE, "status": "applied", "apply_method": "x", "confirmation_id": "c"}, ANSWER_NEW)
    assert _FakeNotifier.buttons == []


class _FakeBot:
    def __init__(self):
        self.sent, self.edits = [], []

    async def send_message(self, **kw):
        self.sent.append(kw)
        return SimpleNamespace(message_id=555)

    async def edit_message_reply_markup(self, **kw):
        self.edits.append(kw)
        return True


def _real_notifier():
    from src.notifications.telegram_notifier import TelegramNotifier
    n = TelegramNotifier.__new__(TelegramNotifier)
    n.enabled, n.chat_id, n.bot, n.sent_today = True, str(CHAT), _FakeBot(), 0
    return n


def test_notifier_keeps_the_message_id_and_returns_true_as_before():
    n = _real_notifier()
    assert asyncio.run(n.send_message(APPLY_YOURSELF)) is True
    assert n.last_message_id == 555
    assert n.bot.sent == [{"chat_id": str(CHAT), "text": APPLY_YOURSELF, "parse_mode": "HTML"}]


def test_notifier_sets_only_the_reply_markup():
    n = _real_notifier()
    assert asyncio.run(n.add_alert_buttons(555, DEAL)) is True
    (edit,) = n.bot.edits
    assert set(edit) == {"chat_id", "message_id", "reply_markup"}           # no text: the alert is not rewritten
    assert edit["message_id"] == 555
    buttons = [(b.text, b.callback_data) for row in edit["reply_markup"].inline_keyboard for b in row]
    assert buttons == [("⏳ I applied", "vjh_ap:" + DEAL), ("❌ Not a fit", "vjh_nf:" + DEAL)]
    assert asyncio.run(n.add_alert_buttons(555, "")) is False
    assert asyncio.run(n.add_alert_buttons(None, DEAL)) is False
    assert len(n.bot.edits) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 4. The bot: taps, her reason, idempotency, chat lock
# ═══════════════════════════════════════════════════════════════════════════
class _FakeHubSpot:
    """Deals and notes in memory; every call recorded in order. Nothing leaves the process."""

    def __init__(self, stage="qualifiedtobuy", fail=None):
        self.deals = {DEAL: {"dealstage": stage, "dealname": NAME}}
        self.notes, self.calls, self.fail = [], [], fail or {}
        self.note_count, self.paths = {}, []

    def __call__(self, path, body=None):
        kind = ("read" if body is None else "note" if path == "/crm/v3/objects/notes"
                else "move" if path.endswith("/deals/batch/update") else "other")
        self.calls.append(kind)
        self.paths.append(path)
        if kind in self.fail:
            raise self.fail[kind]
        if kind == "read":
            deal = re.search(r"/deals/(\d+)\?", path).group(1)
            if deal not in self.deals:
                raise _HTTP404()
            out = {"id": deal, "properties": dict(self.deals[deal])}
            n = self.note_count.get(deal)
            if n is not None and "associations=notes" in path:
                # v3 lists one row per association type, so a note can appear twice: the bot counts unique ids
                rows = [{"id": str(i), "type": "deal_to_note"} for i in range(n)]
                out["associations"] = {"notes": {"results": rows + rows[:1]}}
            return out
        if kind == "note":
            (assoc,) = body["associations"]
            assert assoc["types"] == [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}]
            self.notes.append((assoc["to"]["id"], body["properties"]["hs_note_body"]))
            return {"id": "n1"}
        if kind == "move":
            (inp,) = body["inputs"]
            self.deals[inp["id"]]["dealstage"] = inp["properties"]["dealstage"]
            return {"results": []}
        raise AssertionError(path)


class _HTTP404(Exception):
    code = 404


class _TgBot:
    def __init__(self):
        self.sent, self.edits, self._next = [], [], 900

    async def send_message(self, chat_id, text, **kw):
        self._next += 1
        self.sent.append({"chat_id": chat_id, "text": text, **kw})
        return SimpleNamespace(message_id=self._next)

    async def edit_message_reply_markup(self, **kw):
        self.edits.append(kw)
        return True


def _bot(monkeypatch, hs):
    import src.notifications.telegram_bot_enhanced as tbe
    monkeypatch.setattr(tbe, "_alert_hs", hs)
    b = tbe.EnhancedTelegramBot.__new__(tbe.EnhancedTelegramBot)
    b.chat_id, b._allowed_chat_id, b.is_paused = str(CHAT), CHAT, False
    b.qa = []

    async def fake_qa(update, context, text, speak=None, lang=None):
        b.qa.append(text)
    b._reply_job_question = fake_qa
    replies = []

    async def fake_plain(update, text):
        replies.append(text)
        return True
    b._reply_plain = fake_plain
    b.replies = replies
    return b, SimpleNamespace(bot=_TgBot())


def _tap(b, ctx, data, chat=CHAT, alert_id=321):
    async def answer():
        return True
    query = SimpleNamespace(data=data, answer=answer, message=SimpleNamespace(chat_id=chat, message_id=alert_id))
    update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(id=chat))
    asyncio.run(b.handle_callback(update, ctx))


def _say(b, ctx, text, chat=CHAT, reply_to=None):
    msg = SimpleNamespace(text=text, reply_to_message=reply_to)
    update = SimpleNamespace(message=msg, effective_chat=SimpleNamespace(id=chat))
    asyncio.run(b.handle_freeform_text(update, ctx))


def test_applied_tap_writes_the_note_then_moves_to_sent_and_drops_the_buttons(monkeypatch):
    import src.notifications.telegram_bot_enhanced as tbe
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert hs.calls == ["read", "note", "move"]                 # her words first, then the stage
    assert hs.notes == [(DEAL, f"Applied (via VJH alert button, {tbe._panama_today()})")]
    assert hs.deals[DEAL]["dealstage"] == "decisionmakerboughtin"
    assert [m["text"] for m in ctx.bot.sent] == [f"⏳ moved to Sent: {TITLE}"]
    assert ctx.bot.edits == [{"chat_id": CHAT, "message_id": 321, "reply_markup": None}]


def test_second_applied_tap_writes_nothing(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert hs.calls == ["read", "note", "move", "read"]
    assert len(hs.notes) == 1
    assert ctx.bot.sent[-1]["text"] == f"⏳ Already in Sent. Nothing changed: {TITLE}"


@pytest.mark.parametrize("stage", ["closedlost", "contractsent", "closedwon"])
def test_applied_tap_never_drags_a_decided_deal_back(monkeypatch, stage):
    hs = _FakeHubSpot(stage=stage)
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert hs.calls == ["read"] and hs.deals[DEAL]["dealstage"] == stage
    assert ctx.bot.sent[-1]["text"].startswith(f"Left as it is: {TITLE} is in ")
    assert ctx.bot.edits == []


def test_not_a_fit_asks_then_saves_her_words_exactly(monkeypatch):
    from telegram import ForceReply
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    assert hs.calls == ["read"] and hs.notes == []                       # nothing written before her reason
    ask = ctx.bot.sent[-1]
    assert isinstance(ask.get("reply_markup"), ForceReply)
    assert ask["text"].startswith(f"❌ Not a fit: {TITLE}\nWhy?")
    reason = "Offices in US, Canada and Europe only, no LATAM; also 5+ years hands-on coding"
    _say(b, ctx, reason)
    assert b.qa == []                                                    # the reason never reaches the Q&A
    assert hs.calls == ["read", "read", "note", "move"]
    assert hs.notes == [(DEAL, reason)]                                  # her words, nothing added
    assert hs.deals[DEAL]["dealstage"] == "closedlost"
    assert b.replies == [f"❌ saved: {reason}\nMoved to No fit: {TITLE}"]
    assert ctx.bot.edits == [{"chat_id": CHAT, "message_id": 321, "reply_markup": None}]
    _say(b, ctx, "how many jobs are in I act today?")                    # the question is answered again
    assert b.qa == ["how many jobs are in I act today?"]


def test_the_learner_reads_both_notes_as_hers():
    """The REAL judge_feedback_sync, on the exact note bodies the buttons write — also behind cto-aipa's own note."""
    import src.notifications.telegram_bot_enhanced as tbe
    jfs = _jfs()
    reason = "Offices in US, Canada and Europe only, no LATAM; also 5+ years hands-on coding"
    applied = f"Applied (via VJH alert button, {tbe._panama_today()})"
    for body in (reason, applied):
        assert not jfs._KIT_NOTE.search(body)
    assert jfs._BOT_NOTE_TEMPLATE.sub(" ", reason) == reason
    assert jfs._rejection_reason([{"body": reason}], TITLE) == f"her reason: {reason}"
    assert jfs._elena_said_applied([{"body": applied}]) is True
    # cto-aipa's note on every VJH deal (hubspot-client.ts manual-apply package), ahead of hers:
    cto_note = ("<strong>⚠️ MANUAL APPLY REQUIRED</strong> — VJH found this; you submit.<br>"
                "<strong>Apply:</strong> <a href='https://example.com/job/1'>Open job / apply page</a><br>"
                "<strong>Score:</strong> 91/100<br><strong>Source:</strong> vjh_review<br><br>"
                "<strong>--- COVER LETTER — drafted against this posting (openai). Read it, then paste. ---</strong>"
                "<br><pre>Dear team, I am writing to apply for the role…</pre>")
    assert jfs._rejection_reason([{"body": cto_note}, {"body": reason}], TITLE) == f"her reason: {reason}"
    assert jfs._elena_said_applied([{"body": cto_note}]) is False        # the bot's own words never count
    assert jfs._elena_said_applied([{"body": cto_note}, {"body": applied}]) is True


def test_reason_html_is_escaped_in_the_note_and_shown_plain_to_her(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "R&D role <requires> on-site work in Austin")
    assert hs.notes == [(DEAL, "R&amp;D role &lt;requires&gt; on-site work in Austin")]
    assert b.replies[0].startswith("❌ saved: R&D role <requires> on-site work in Austin")


def test_cancel_keeps_the_job_open(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "Cancel")
    assert hs.notes == [] and hs.deals[DEAL]["dealstage"] == "qualifiedtobuy"
    assert b.replies == [f"Kept open. Nothing changed: {TITLE}"]
    assert ctx.bot.edits == []


def test_second_not_a_fit_tap_asks_nothing_and_writes_nothing(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "Only open to candidates in Colombia and Peru")
    n_sent = len(ctx.bot.sent)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    assert len(hs.notes) == 1
    assert len(ctx.bot.sent) == n_sent + 1
    assert ctx.bot.sent[-1]["text"] == f"❌ Already in No fit. Nothing changed: {TITLE}"
    assert "reply_markup" not in ctx.bot.sent[-1]


def test_a_too_short_reason_is_saved_and_she_is_told_the_learner_skips_it(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "US only")
    assert hs.notes == [(DEAL, "US only")] and hs.deals[DEAL]["dealstage"] == "closedlost"
    assert b.replies[0].startswith("❌ saved: US only\nMoved to No fit: ")
    assert "learner will skip this one" in b.replies[0]


def test_reply_to_the_question_counts_for_a_day_a_plain_message_for_15_minutes(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    ask_id = ctx.bot._next
    b._nofit_waiting()[CHAT][DEAL]["at"] -= 16 * 60                 # 16 minutes later
    _say(b, ctx, "what is in my queue today?")
    assert b.qa == ["what is in my queue today?"] and hs.notes == []
    _say(b, ctx, "Hybrid three days a week in Bogota", reply_to=SimpleNamespace(message_id=ask_id))
    assert hs.notes == [(DEAL, "Hybrid three days a week in Bogota")]


def test_a_reply_to_some_other_message_is_not_the_reason(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "translate this one please", reply_to=SimpleNamespace(message_id=12345))
    assert b.qa == ["translate this one please"] and hs.notes == []


def test_a_question_older_than_a_day_is_forgotten(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    ask_id = ctx.bot._next
    b._nofit_waiting()[CHAT][DEAL]["at"] = time.monotonic() - 25 * 3600
    _say(b, ctx, "Hybrid in Bogota", reply_to=SimpleNamespace(message_id=ask_id))
    assert hs.notes == [] and b.qa == ["Hybrid in Bogota"]
    assert not b._nofit_waiting().get(CHAT)


def test_only_her_chat_can_tap_or_answer(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL, chat=OTHER_CHAT)
    _tap(b, ctx, "vjh_nf:" + DEAL, chat=OTHER_CHAT)
    assert hs.calls == [] and ctx.bot.sent == []
    _tap(b, ctx, "vjh_nf:" + DEAL)                                   # her own tap
    took = asyncio.run(b._take_nofit_reason(
        SimpleNamespace(message=SimpleNamespace(text="x y z", reply_to_message=None),
                        effective_chat=SimpleNamespace(id=OTHER_CHAT)), ctx, "Some other chat writes this"))
    assert took is False and hs.notes == []


def test_a_forged_button_writes_nothing(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:12;DROP")
    assert hs.calls == []
    assert ctx.bot.sent[-1]["text"] == "This button carries no deal id. Nothing changed."


def test_hubspot_down_or_deal_gone_changes_nothing_and_says_so(monkeypatch):
    hs = _FakeHubSpot(fail={"read": TimeoutError("timed out")})
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert hs.notes == [] and "could not be reached" in ctx.bot.sent[-1]["text"]
    hs2 = _FakeHubSpot()
    hs2.deals = {}
    b2, ctx2 = _bot(monkeypatch, hs2)
    _tap(b2, ctx2, "vjh_nf:" + DEAL)
    assert ctx2.bot.sent[-1]["text"] == "⚠️ This deal is no longer in HubSpot. Nothing changed."


def test_note_saved_but_stage_refused_is_reported_not_hidden(monkeypatch):
    hs = _FakeHubSpot(fail={"move": RuntimeError("HTTP Error 403")})
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert len(hs.notes) == 1 and hs.deals[DEAL]["dealstage"] == "qualifiedtobuy"
    assert ctx.bot.sent[-1]["text"].startswith("⚠️ Note saved, but HubSpot did not move the deal.")
    assert ctx.bot.edits == []                                       # buttons stay: she can try again


def test_a_207_multi_status_with_errors_is_a_refused_move(monkeypatch):
    hs = _FakeHubSpot()
    real = hs.__call__

    def partial(path, body=None):
        if path.endswith("/deals/batch/update"):
            hs.calls.append("move")
            return {"status": "COMPLETE", "results": [], "errors": [{"status": "error", "category": "VALIDATION"}]}
        return real(path, body)
    b, ctx = _bot(monkeypatch, partial)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _say(b, ctx, "Requires relocation to Toronto within three months")
    assert hs.deals[DEAL]["dealstage"] == "qualifiedtobuy"
    assert b.replies[0].startswith("❌ saved: Requires relocation to Toronto within three months\n⚠️ HubSpot did not "
                                   "move the deal.")


def test_reason_kept_when_hubspot_fails_so_she_can_resend(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    hs.fail = {"note": TimeoutError("timed out")}
    _say(b, ctx, "Requires a CS degree and Java backend work")
    assert hs.notes == [] and "Nothing saved." in b.replies[-1]
    hs.fail = {}
    _say(b, ctx, "Requires a CS degree and Java backend work")
    assert hs.notes == [(DEAL, "Requires a CS degree and Java backend work")]
    assert hs.deals[DEAL]["dealstage"] == "closedlost"


def test_the_existing_menu_buttons_still_dispatch(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    seen = []

    async def fake_menu(context, chat_id):
        seen.append(chat_id)
    b._send_menu = fake_menu
    _tap(b, ctx, "menu")
    assert seen == [CHAT] and hs.calls == []


# ═══════════════════════════════════════════════════════════════════════════
# 5. Review fixes (18 Oct 2026)
# ═══════════════════════════════════════════════════════════════════════════
# cto-aipa's note on every VJH deal (hubspot-client.ts manual-apply package), the same body as above.
CTO_NOTE = ("<strong>⚠️ MANUAL APPLY REQUIRED</strong> — VJH found this; you submit.<br>"
            "<strong>Apply:</strong> <a href='https://example.com/job/1'>Open job / apply page</a><br>"
            "<strong>Score:</strong> 91/100<br><strong>Source:</strong> vjh_review<br><br>"
            "<strong>--- COVER LETTER — drafted against this posting (openai). Read it, then paste. ---</strong>"
            "<br><pre>Dear team, I am writing to apply for the role…</pre>")
DEAL2 = "41234567891"
NAME2 = "[HIRING-VJH-LEAD] Solutions Architect @ Acme"
TITLE2 = "Solutions Architect @ Acme"


def test_the_applied_stamp_is_never_her_reason_on_a_lost_deal():
    """She applies (⏳), then is rejected or ghosted: the deal lands in ❌ No fit by design. The stamp is the oldest
    note she has on it, so before the fix it won "her reason" and hid whatever she wrote afterwards."""
    import src.notifications.telegram_bot_enhanced as tbe
    jfs = _jfs()
    stamp = f"Applied (via VJH alert button, {tbe._panama_today()})"          # the exact body the bot writes
    later = "Employer rejected, wanted 7 years Java"
    assert jfs._rejection_reason([{"body": CTO_NOTE}, {"body": stamp}], TITLE) == ""
    assert jfs._rejection_reason([{"body": CTO_NOTE}, {"body": stamp}, {"body": later}], TITLE) \
        == f"her reason: {later}"
    assert jfs._rejection_reason([{"body": f"<p>{stamp}</p>"}, {"body": later}], TITLE) == f"her reason: {later}"
    # still HER application on a ⏳ Sent deal, and still not an agent note
    assert jfs._elena_said_applied([{"body": CTO_NOTE}, {"body": stamp}]) is True
    assert not jfs._KIT_NOTE.search(stamp)
    # only the whole stamp is skipped: a sentence of hers that merely starts the same way is still hers
    own = "Applied (via VJH alert button, 2026-10-18) but they want on-site in Austin"
    assert jfs._rejection_reason([{"body": own}], TITLE) == f"her reason: {own}"


def _two_deals():
    hs = _FakeHubSpot()
    hs.deals[DEAL2] = {"dealstage": "qualifiedtobuy", "dealname": NAME2}
    return hs


def test_applied_after_not_a_fit_withdraws_the_question(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    _tap(b, ctx, "vjh_ap:" + DEAL)
    assert hs.deals[DEAL]["dealstage"] == "decisionmakerboughtin"
    _say(b, ctx, "how many jobs did I apply to this week?")
    assert b.qa == ["how many jobs did I apply to this week?"]       # not swallowed by "Left as it is"
    assert b.replies == [] and len(hs.notes) == 1                     # only the ⏳ stamp


def test_applied_on_another_job_keeps_the_open_question(monkeypatch):
    hs = _two_deals()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL, alert_id=321)
    _tap(b, ctx, "vjh_ap:" + DEAL2, alert_id=322)
    _say(b, ctx, "Requires a security clearance in the US")
    assert hs.notes[-1] == (DEAL, "Requires a security clearance in the US")
    assert hs.deals[DEAL]["dealstage"] == "closedlost"
    assert hs.deals[DEAL2]["dealstage"] == "decisionmakerboughtin"


def test_not_a_fit_on_two_alerts_keeps_both_questions(monkeypatch):
    hs = _two_deals()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL, alert_id=321)
    ask1 = ctx.bot._next
    _tap(b, ctx, "vjh_nf:" + DEAL2, alert_id=322)
    ask2 = ctx.bot._next
    _say(b, ctx, "Needs five years of Java backend work", reply_to=SimpleNamespace(message_id=ask1))
    _say(b, ctx, "Office in Berlin three days a week", reply_to=SimpleNamespace(message_id=ask2))
    assert hs.notes == [(DEAL, "Needs five years of Java backend work"),
                        (DEAL2, "Office in Berlin three days a week")]
    assert hs.deals[DEAL]["dealstage"] == hs.deals[DEAL2]["dealstage"] == "closedlost"
    assert b.qa == []


def test_a_plain_message_with_two_fresh_questions_saves_nothing_and_asks_which(monkeypatch):
    hs = _two_deals()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL, alert_id=321)
    _tap(b, ctx, "vjh_nf:" + DEAL2, alert_id=322)
    _say(b, ctx, "Needs five years of Java backend work")
    assert hs.notes == [] and b.qa == []
    assert b.replies[-1].startswith("Two or more jobs are waiting for a reason:")
    assert TITLE in b.replies[-1] and TITLE2 in b.replies[-1] and b.replies[-1].endswith("Nothing saved.")
    assert set(b._nofit_waiting()[CHAT]) == {DEAL, DEAL2}
    b._nofit_waiting()[CHAT][DEAL]["at"] -= 16 * 60                  # only DEAL2's question is fresh now
    _say(b, ctx, "Office in Berlin three days a week")
    assert hs.notes == [(DEAL2, "Office in Berlin three days a week")]
    assert set(b._nofit_waiting()[CHAT]) == {DEAL}                    # DEAL's still answers a reply for a day


def test_a_swipe_reply_to_the_alert_itself_is_the_reason(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL, alert_id=321)
    _say(b, ctx, "Needs a US work permit, no sponsorship", reply_to=SimpleNamespace(message_id=321))
    assert hs.notes == [(DEAL, "Needs a US work permit, no sponsorship")]
    assert b.qa == []


def test_a_reply_to_the_alert_after_15_minutes_goes_to_the_qa(monkeypatch):
    hs = _FakeHubSpot()
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL, alert_id=321)
    b._nofit_waiting()[CHAT][DEAL]["at"] -= 16 * 60
    _say(b, ctx, "what does this one pay?", reply_to=SimpleNamespace(message_id=321))
    assert hs.notes == [] and b.qa == ["what does this one pay?"]


@pytest.mark.parametrize("n,learns", [(None, True), (7, True), (8, False), (11, False)])
def test_the_question_promises_learning_only_under_the_learners_note_cap(monkeypatch, n, learns):
    hs = _FakeHubSpot()
    if n is not None:
        hs.note_count[DEAL] = n
    b, ctx = _bot(monkeypatch, hs)
    _tap(b, ctx, "vjh_nf:" + DEAL)
    assert hs.calls == ["read"] and "associations=notes" in hs.paths[0]     # the same single GET as before
    text = ctx.bot.sent[-1]["text"]
    assert ("VJH learns from it" in text) is learns
    if not learns:
        assert f"already has {n} notes" in text and "may not see this one" in text


def test_the_note_cap_matches_the_learner():
    import src.notifications.telegram_bot_enhanced as tbe
    src = (ROOT / "scripts" / "judge_feedback_sync.py").read_text(encoding="utf-8")
    assert f'(r.get("to") or [])[:{tbe._LEARNER_NOTE_CAP}]' in src
