#!/usr/bin/env python3
"""The 7:00 digest and the Telegram Clean / Keep buttons must name a thread the same way.

18 Oct 2026: Elena cleaned an intro thread on 13 Oct; the digest kept
showing it every morning (it looked up only its own subject key) and the buttons posted
no keyboard (they saw their own Clean row). This test runs the digest's OWN printed lines
through the buttons' OWN parser (cto-aipa dist/radar-cleanup.js, via node) and checks the
names match, then checks what the digest hides and what it must not hide.

    python3 scripts/test_followup_radar_ts_keys.py      (CTO_AIPA_PATH to point at cto-aipa)
"""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("followup_radar", os.path.join(HERE, "followup_radar.py"))
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)

passed = failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


now = datetime.now(timezone.utc)
boardy = {"who": "intro@example.com", "subject": "Intro: Elena + A Contact"}
py_key = fr.norm_subject(boardy["subject"])
row = {"at": now.isoformat(), "until": None, "kind": "dismissed", "who": "intro@example.com"}

print("\nFollow-up radar: digest honours the buttons' Clean / Keep\n")
check("button_key = the buttons' name for the Boardy thread",
      fr.button_key(boardy) == "intro@example.com|intro: elena + a contact", fr.button_key(boardy))
check("a Clean written by the buttons now hides the thread in the digest",
      fr.is_hidden(fr.button_key(boardy), {"intro@example.com|intro: elena + a contact": row}, now))
check("the digest's own subject key still hides it (unchanged)", fr.is_hidden(py_key, {py_key: row}, now))
bare = {"intro@example.com": row}
check("a bare-sender row does NOT hide a thread (a new reply from that sender must still show)",
      not fr.is_hidden(py_key, bare, now) and not fr.is_hidden(fr.button_key(boardy), bare, now))
kept = {fr.button_key(boardy): {**row, "kind": "kept"}}
check("a Keep from the buttons is honoured as kept, not hidden",
      fr.is_kept(fr.button_key(boardy), kept, now) and not fr.is_hidden(fr.button_key(boardy), kept, now))
snoozed = {fr.button_key(boardy): {**row, "until": (now - timedelta(days=1)).isoformat()}}
check("an expired snooze from the buttons no longer hides", not fr.is_hidden(fr.button_key(boardy), snoozed, now))

cleaned_at = datetime(2026, 10, 13, 13, 21, tzinfo=timezone.utc)
crow = {"intro@example.com|intro: elena + a contact": {**row, "at": "2026-10-13T13:21:58.726Z"}}
check("a Clean still hides the thread when no mail came after it (Boardy, 18 Oct)",
      fr.is_hidden(fr.button_key(boardy), crow, now, cleaned_at - timedelta(hours=2)))
check("new mail after the Clean makes the thread live again (fresh stuff stays on the radar)",
      not fr.is_hidden(fr.button_key(boardy), crow, now, cleaned_at + timedelta(days=2)))

# A folded Subject header ("...\r\n continued") must become ONE card line.
inbox = [{"subject": "Interview next steps for the Senior AI Automation Architect\r\n role at Acme",
          "from": "Recruiter <hr@example.com>", "date": now - timedelta(days=3)}]
sent = [{"subject": "Re: Interview next steps for the Senior AI Automation Architect role at Acme",
         "date": now - timedelta(days=5)}]
folded = list(fr.build(inbox, sent, set()).values())[0]
check("a folded subject is stored on one line", "\n" not in folded["subject"] and "\r" not in folded["subject"],
      repr(folded["subject"][:80]))

# ── cross-language contract: the digest's printed lines through the buttons' real parser ──
threads = [
    boardy,
    {"who": "Recruiter@Example.com", "subject": "Re:   Interview   Invitation + Next Steps"},
    {"who": "<talent@example.com>", "subject": '"Quoted subject"'},
    {"who": "ops@example.org", "subject": "A very long subject line that keeps going well past the seventy character cut the digest prints"},
    {"who": "hola@example.net", "subject": "Propuesta: diseño y automatización — próxima reunión"},
]
lines = ["📡 Follow-up radar", "", "🔴 THEY WROTE LAST — your move"]
for i, t in enumerate(threads):
    lines.append(f"  {i + 3}d  {t['who']}\n       {t['subject'][:70]}")   # exactly the digest's own print format
digest = "\n".join(lines)

cto = next((p for p in [os.environ.get("CTO_AIPA_PATH", ""), "/home/ubuntu/cto-aipa", "D:/aideazz/ai-cofounders/cto-aipa"]
            if p and os.path.exists(os.path.join(p, "dist", "radar-cleanup.js"))), None)
if not cto:
    check("cto-aipa dist/radar-cleanup.js found for the cross-language check", False, "set CTO_AIPA_PATH")
else:
    js = ("const r=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d)"
          ".on('end',()=>console.log(JSON.stringify(r.parseRadarDigest(s).map(i=>[i.who,i.key]))))")
    out = subprocess.run(["node", "-e", js, os.path.join(cto, "dist", "radar-cleanup.js")],
                         input=digest, capture_output=True, text=True, encoding="utf-8", timeout=30)
    parsed = json.loads(out.stdout or "[]")
    check("the buttons' parser reads every thread the digest prints", len(parsed) == len(threads),
          f"{len(parsed)} of {len(threads)} {out.stderr[:200]}")
    for t, (who, key) in zip(threads, parsed):
        check(f"same name both sides: {t['who'][:24]} / {t['subject'][:28]}", fr.button_key(t) == key,
              f"digest {fr.button_key(t)!r} vs buttons {key!r}")

# ── the 7:00 card's own buttons: button n must clear the n-th printed thread, through the bot's real lookup ──
def mk(who, subj, age_in, age_out):
    return {"who": who, "subject": subj, "in": now - timedelta(days=age_in), "out": now - timedelta(days=age_out)}

them = [(40, mk("old@example.org", "Partnership follow-up", 40, 50), "partnership follow-up"),
        (5, mk("intro@example.com", "Intro: Elena + A Contact", 5, 9), "intro: elena + a contact"),
        (3, mk("hr@example.com", "Interview next steps", 3, 6), "interview next steps")]
you = [(35, mk("ops@example.net", "Quick question", 40, 35), "quick question"),
       (4, mk("hola@example.net", "Propuesta: diseño", 9, 4), "propuesta: diseño")]
pid = "202610180000"
rows, kb = fr.radar_rows_and_keyboard(them, you, {}, now, pid)
card = ["📡 Follow-up radar", "", "🔴 THEY WROTE LAST — your move"]
card += [f"  {a}d  {t['who']}\n       {t['subject'][:70]}" for a, t, _ in them]
card += ["", "🟡 YOU WROTE LAST — gone quiet, a nudge is free"]
card += [f"  {a}d  {t['who']}\n       {t['subject'][:70]}" for a, t, _ in you]
card_text = "\n".join(card)
buttons = [b for r in kb["inline_keyboard"] for b in r if b["callback_data"].startswith("rdrone:")]
check("every printed thread has its own button (fresh ones too)", len(buttons) == len(them) + len(you), str(len(buttons)))
check("rows are in card order, not re-sorted by age", [r["who"] for r in rows] == [t["who"] for _, t, _ in them + you])

if cto:
    import tempfile
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "radar-proposal.json"), "w", encoding="utf-8") as fh:
        json.dump({"id": pid, "created": now.isoformat(), "items": rows}, fh)
    # what the bot does on a tap: resolveRadarProposal(card text, dir) then proposal.items[n]
    js = ("const r=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{"
          "const p=r.resolveRadarProposal({digestText:s,dir:process.argv[2]});"
          "console.log(JSON.stringify({id:p.proposal.id,items:p.proposal.items.map(i=>[i.who,i.key])}))})")
    out = subprocess.run(["node", "-e", js, os.path.join(cto, "dist", "radar-cleanup.js"), d],
                         input=card_text, capture_output=True, text=True, encoding="utf-8", timeout=30)
    res = json.loads(out.stdout or '{"id":"","items":[]}')
    check("the bot accepts the card's proposal id", res["id"] == pid, out.stderr[:200])
    wrong = []
    for b in buttons:
        n = int(b["callback_data"].split(":")[2])
        label_who = b["text"].split()[-1].split("@")[0]
        got = res["items"][n] if n < len(res["items"]) else ["", ""]
        if got[1] != rows[n]["key"] or not got[0].startswith(label_who):
            wrong.append(f"button {n} '{b['text']}' -> {got}")
    check("every button clears exactly the thread its label names", not wrong, "; ".join(wrong))
    # the Clean the bot writes for button 1 (Boardy) hides that thread — and only it — in tomorrow's digest
    js2 = ("const r=require(process.argv[1]);const it=JSON.parse(process.argv[2]);const L={};"
           "r.dismissRadarItems([it],L,{at:new Date().toISOString(),until:null,kind:'dismissed',who:it.who});"
           "console.log(JSON.stringify(L))")
    led = json.loads(subprocess.run(["node", "-e", js2, os.path.join(cto, "dist", "radar-cleanup.js"), json.dumps(rows[1])],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30).stdout or "{}")
    hidden = [t["who"] for _, t, k in them + you
              if fr.is_hidden(k, led, now, now - timedelta(days=1)) or fr.is_hidden(fr.button_key(t), led, now, now - timedelta(days=1))]
    check("tapping the intro thread hides it and nothing else", hidden == ["intro@example.com"], str(hidden))

print(f"\n{passed} passed, {failed} failed\n")
sys.exit(1 if failed else 0)
