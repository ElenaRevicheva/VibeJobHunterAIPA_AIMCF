"""A hot employer/client mail always reaches Elena's phone (27 Oct 2026). Offline.

30 days of logs: the "no-reply" blocklist pattern silently dropped mails the classifier scored hot from real
hiring systems (14 Valce Talent + 2 Sumsub + 2 ioet via Teamtailor, 4 CI&T). And the detector records "alerted"
BEFORE the Telegram send, so a failed send would have lost the alert for good.
"""
import asyncio
import json
import os
import tempfile
from pathlib import Path

import src.autonomous.response_detector as rd
from src.autonomous.orchestrator import AutonomousOrchestrator


def test_ats_relays_are_blocked_only_generically():
    for s in ("no-reply@" "valcetalentsolutions.na.teamtailor-mail.com", "noreplyhiring@" "ciandt.com",
              "no-reply@" "ioet.na.teamtailor-mail.com"):
        assert rd._sender_is_blocked(s) and not rd._blocked_by_name(s), s


def test_named_noise_stays_blocked_by_name():
    for s in ("boardy@" "boardy.ai", "help@" "torre.ai", "aipa@" "aideazz.xyz", "notifications@" "github.com",
              "x@" "substack.com"):
        assert rd._blocked_by_name(s), s


class FlakyTelegram:
    def __init__(self, fail_times):
        self.fail_times, self.sent = fail_times, []

    async def send_message(self, text, parse_mode="HTML"):
        if self.fail_times > 0:
            self.fail_times -= 1
            return False
        self.sent.append((text, parse_mode))
        return True


def _orch(tg, tmp):
    o = AutonomousOrchestrator.__new__(AutonomousOrchestrator)
    o.telegram = tg
    o._PENDING_ALERTS = Path(tmp) / "pending_alerts.json"
    return o


def test_a_failed_alert_is_queued_then_delivered(monkeypatch):
    async def no_sleep(*_):
        return None
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    with tempfile.TemporaryDirectory() as tmp:
        tg = FlakyTelegram(fail_times=4)              # 3 HTML tries + plain-text try all fail
        o = _orch(tg, tmp)
        assert asyncio.run(o._deliver_alert("🔥 <b>INTERVIEW</b> from Acme")) is False
        assert json.loads(o._PENDING_ALERTS.read_text(encoding="utf-8"))[0]["text"].endswith("Acme")
        asyncio.run(o._flush_pending_alerts())        # next cycle: Telegram is back
        assert tg.sent and "INTERVIEW" in tg.sent[0][0] and "delayed" in tg.sent[0][0]
        assert not o._PENDING_ALERTS.exists()


def test_html_rejection_falls_back_to_plain_text(monkeypatch):
    async def no_sleep(*_):
        return None
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    with tempfile.TemporaryDirectory() as tmp:
        tg = FlakyTelegram(fail_times=3)
        o = _orch(tg, tmp)
        assert asyncio.run(o._deliver_alert("❓ <b>Question</b> &lt;a@b&gt;")) is True
        assert tg.sent[0] == ("❓ Question <a@b>", None)
