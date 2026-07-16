#!/usr/bin/env python3
"""
One-off backfill: push the historical `detected_responses` rows (real employer/recruiter
replies that were classified but never surfaced to HubSpot or Telegram beyond the moment
they scrolled by) into HubSpot, then send Elena ONE Telegram digest.

Found July 16 2026: the live orchestrator path (_check_for_responses) saved hot leads to
SQLite and alerted Telegram, but never called push_response_to_hubspot() — and had no
blocked-sender filter, so ~90 Torre.ai bot pings buried real signal (a July 15 Truelogic
interview invite, two Oracle Startup Program meeting invites, a Foundever interview invite).
That gap is now closed going forward in orchestrator.py. This script backfills the past.

Read-only against SQLite (no writes to the DB). Run ONCE — re-running will move the same
HubSpot deals to recruiter_responded again (harmless but noisy), so this is not a cron job.

Usage (on Oracle, where autonomous_data/vibejobhunter.db has the real 189 rows):
    cd /home/ubuntu/VibeJobHunterAIPA_AIMCF
    python3 scripts/backfill_detected_responses.py            # dry-run, prints what would push
    python3 scripts/backfill_detected_responses.py --apply    # actually pushes + sends digest
"""
import os
import sys
import sqlite3
import argparse
import urllib.request
import urllib.error
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.autonomous.response_detector import _sender_is_blocked  # noqa: E402

DB_PATH = "autonomous_data/vibejobhunter.db"


def load_env():
    """VJH doesn't export .env to os.environ automatically — read it directly (mirrors
    the pattern in response_detector.push_response_to_hubspot / llm_judge._key)."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_candidates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, email_id, from_email, from_name, subject, body_preview, received_at,
               response_type, confidence, company_name, ai_analysis, suggested_action
        FROM detected_responses
        WHERE response_type IN ('positive', 'question')
        ORDER BY received_at ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    kept, blocked = [], []
    for r in rows:
        if _sender_is_blocked(r["from_email"]):
            blocked.append(r)
        else:
            kept.append(r)
    return kept, blocked


def push_row_to_hubspot(row, secret, base):
    payload = {
        "source": "response_detector_backfill",
        "type": "application",
        "pipeline": "hiring",
        "sourcePrefix": "HIRING-VJH-LEAD",
        "stage": "recruiter_responded",
        "jobTitle": (row["subject"] or "Recruiter response")[:120],
        "company": row["company_name"] or "Unknown",
        "recruiterEmail": row["from_email"] or "",
        "recruiterName": row["from_name"] or "",
        "notes": (
            "RECRUITER RESPONSE DETECTED (backfill) - " + (row["response_type"] or "") + "\n"
            "Confidence: " + str(round(row["confidence"] or 0, 2)) + "\n"
            "Received: " + str(row["received_at"] or "") + "\n"
            "Subject: " + (row["subject"] or "") + "\n"
            "AI summary: " + (row["ai_analysis"] or "")[:300]
        ),
        "urgency": 5 if row["response_type"] == "positive" else 3,
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/api/crm-event",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, r.read().decode()[:200]


def send_telegram_digest(kept, pushed_ok, pushed_fail):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[digest] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set — skipping Telegram digest")
        return

    highlights = [r for r in kept if any(
        k in (r["subject"] or "").lower() or k in (r["company_name"] or "").lower()
        for k in ("truelogic", "oracle", "foundever")
    )][:5]

    lines = [
        "🗂 <b>Backfill: buried recruiter responses surfaced</b>",
        f"{len(kept)} real responses pushed to HubSpot (stage: recruiter_responded) — {pushed_ok} ok, {pushed_fail} failed.",
        "These were sitting in SQLite with no HubSpot/Telegram trail until today.",
        "",
    ]
    if highlights:
        lines.append("<b>Check these first:</b>")
        for r in highlights:
            lines.append(f"• {r['company_name'] or 'Unknown'} — {r['subject']} ({r['received_at']})")
        lines.append("")
    lines.append("Full list in HubSpot: filter deals by stage \"💬 They replied — I act\".")
    text = "\n".join(lines)

    body = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print("[digest] Telegram sent:", r.status)
    except Exception as e:
        print("[digest] Telegram send failed:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually push to HubSpot + send digest")
    args = ap.parse_args()

    load_env()
    kept, blocked = fetch_candidates()

    print(f"Candidates: {len(kept)} real (positive/question, non-blocked-sender)")
    print(f"Filtered out as bot/newsletter noise: {len(blocked)}")
    for r in kept:
        print(f"  [{r['response_type']}] {r['company_name']!r} — {r['subject']!r} ({r['received_at']})")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to push to HubSpot + send Telegram digest.")
        return

    secret = os.getenv("OUTREACH_SECRET", "").strip()
    base = os.getenv("CTO_AIPA_WEBHOOK_URL", "https://webhook.aideazz.xyz/cto").strip()
    if not secret:
        print("OUTREACH_SECRET not set — cannot push to HubSpot")
        return

    ok, fail = 0, 0
    for r in kept:
        try:
            status, body = push_row_to_hubspot(r, secret, base)
            print(f"  pushed: {r['company_name']!r} -> HTTP {status} {body}")
            ok += 1
        except urllib.error.HTTPError as e:
            print(f"  FAILED: {r['company_name']!r} -> HTTP {e.code} {e.read().decode()[:200]}")
            fail += 1
        except Exception as e:
            print(f"  FAILED: {r['company_name']!r} -> {e}")
            fail += 1

    send_telegram_digest(kept, ok, fail)
    print(f"\nDone. {ok} pushed, {fail} failed.")


if __name__ == "__main__":
    main()
