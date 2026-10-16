"""The bilingual Q&A's conscience (telegram_qa_helper._grounded_prompt / _shared_deals_block). Added 2026-10-16.

What this pins — every one a claim the bot made to Elena that the data did not support:
  - a2ecb38: an English question was answered in Spanish (half the shared facts are Spanish). The language reminder
    must sit AFTER "=== HER MESSAGE ===", right before the answer, and a screenshot's own LANGUAGE rule replaces it.
  - "appointmentscheduled" is the AI's untriaged inbox (🤖 AI working). A model reads the raw id as an interview.
  - The deals sheet held the 60 NEWEST deals — 6 of her 14 "🔥 I act today" — and the prompt called its lists
    "complete, counted from the rows below". A count now comes from HubSpot's total in the sheet header; an older
    header without totals still parses, and then every count says it counts rows only.
  - cto-aipa's totals count every deal NAMED HIRING; its "listed:" part counts job deals. A HIRING-named deal that is
    not a job posting must not inflate the 🔥 count, a gap is never given a made-up cause ("did not fit"), and an
    "every 🔥 job deal" the rows cannot back is not believed. OpenClaw's own rule lines are never read as totals.

No model calls, no network, $0: the sheets are fixtures in tmp_path; the one answer_screenshot test replaces
llm_judge._call_llm with a function that records the prompt.
"""
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.notifications import telegram_qa_helper as q

NOW = datetime(2026, 10, 16, 17, 0, tzinfo=timezone.utc)
STAMP = "2026-10-16T16:30:30.275Z"
OLD_LABEL = "complete lists, counted from the rows below"

FIRE = ["Upgrade — AI Experience Engineer", "Niuro — Senior Forward Deployed Engineer", "Pitz — Developer Mid",
        "Niuro — AI Operations", "Tango — AI Builder", "Kinetic — Solutions Architect"]       # 6 🔥 rows
ROWS = ([f"### {r} (qualifiedtobuy)\ndoes: builds things.\nneeds: Python • LLM agents" for r in FIRE]
        + ["### SPACE44 — AI Solutions Architect (decisionmakerboughtin)",
           "### Pitz — Re: Boardy Intro (contractsent)",
           "### WITHIN — AI Creative Specialist (appointmentscheduled)",
           "### Speak — Product Manager (appointmentscheduled)"])
RULES = ["# take the role and requirements from HERE. Never invent a role.",
         "# Ask ONE mock question per message (🎙️ Q<n>/<total>) — never list the whole series."]

OLD_HEADER = f"# {STAMP} · 60 live job deals. Use this for the mock interview: when Elena names a company,"
NEW_HEADERS = {
    # the shape the plan asks for: "<ISO>Z · N live job deals" kept together, totals after it
    "labels on line 2": (f"# {STAMP} · 10 live job deals · HubSpot totals: 🔥 I act today 14 · ⏳ Sent 72 · "
                         "💬 They replied 118 · 🤖 AI working 2,266. Use this for the mock interview:", []),
    # cto-aipa scripts/hs-deal-prep.cjs digest() template (16 Oct), in its partial-🔥 form; "🔥 I act this week" shares
    # the 🔥. The template's complete form is pinned word for word by CTO_DRY_RUN_LINE2 below.
    "hs-deal-prep 16 Oct": (f"# {STAMP} · 10 live job deals listed below · HubSpot totals (deal name contains HIRING): "
                            "🔥 I act today 14 · 🔥 I act this week 0 · ⏳ Sent 72 · 💬 They replied 118 · 🤖 AI working 2266"
                            " — listed: 🔥 I act today 6 of 14, 🔥 I act this week 0 of 0, all 2 ⏳/💬 job deals that "
                            "entered that stage in the last 14 days, the 2 newest 🤖. For a count use these totals, never "
                            "the rows; a deal not listed can still be live: run the --company command below. Use this for "
                            "the mock interview: when Elena names a company,", []),
    "stage ids on their own line": (OLD_HEADER.replace("60", "10"),
                                    ["# HubSpot totals: qualifiedtobuy=14, decisionmakerboughtin=72, "
                                     "contractsent=118, appointmentscheduled=2266"]),
}


CTO_DRY_RUN_LINE2 = (    # line 2 of cto-aipa's real dry run, 16 Oct 17:04 UTC (scratch TOOLS.new.md; it names no deal)
    "# 2026-10-16T17:04:13.109Z · 36 live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act "
    "today 14 · 🔥 I act this week 0 · ⏳ Sent 72 · 💬 They replied 118 · 🤖 AI working 1421 — listed: every 🔥 job deal, "
    "all 20 ⏳/💬 job deals that entered that stage in the last 14 days, the 2 newest 🤖; besides these, 1 🔥 or recent "
    "⏳/💬 deal(s) are named HIRING but are not job postings (not listed). For a count use these totals, never the rows; "
    "a deal not listed can still be live: run the --company command below. Use this for the mock interview: when Elena "
    "names a company,")
CTO_DRY_RUN_ROWS = [f"### Company {s[:3]}{i} — Role {i} ({s})" for s, n in
                    (("qualifiedtobuy", 14), ("decisionmakerboughtin", 14), ("contractsent", 6),
                     ("appointmentscheduled", 2)) for i in range(n)]       # its 36 rows, deal names replaced


def _fire_rows(n: int):
    return [f"### Company {i} — Role {i} (qualifiedtobuy)" for i in range(n)]


def _sheet(tmp_path: Path, line2: str, extra_head=(), rows=None) -> Path:
    ws = tmp_path / "ws"
    (ws / "deals").mkdir(parents=True)
    text = "\n".join(["# LIVE JOB DEALS (HubSpot) — read-only snapshot", line2, *extra_head, *RULES, ""]
                     + [r + "\n" for r in (ROWS if rows is None else rows)])
    (ws / "deals" / "TOOLS.md").write_text(text, encoding="utf-8")
    return ws


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Her shared memory as fixtures: the new-format deals sheet + a facts sheet; ledger and lessons absent."""
    line2, extra = NEW_HEADERS["labels on line 2"]
    w = _sheet(tmp_path, line2, extra)
    (w / "proof").mkdir()
    (w / "proof" / "TOOLS.md").write_text("# rule line\nSU TRAYECTORIA: fundó AIdeazz.\nHER CAREER: founded AIdeazz.\n",
                                          encoding="utf-8")
    monkeypatch.setattr(q, "_OPENCLAW_WS", w)
    monkeypatch.setattr(q, "_LEDGER_PATH", tmp_path / "missing_ledger.json")
    monkeypatch.setattr(q, "_FEEDBACK_PATH", tmp_path / "missing_feedback.json")
    return w


def _line(block: str, label: str) -> str:
    hits = [ln for ln in block.splitlines() if ln.strip().startswith(label)]
    assert len(hits) == 1, (label, hits)
    return hits[0]


# ── (a) the language reminder sits after HER MESSAGE (a2ecb38) ─────────────────────────────────────────────

REMINDERS = {None: "Answer in the language HER MESSAGE is written in",
             "es": "She wrote or spoke Spanish: answer in Spanish.",
             "en": "She wrote or spoke English: answer in English."}


@pytest.mark.parametrize("lang", [None, "es", "en"])
def test_language_reminder_comes_after_her_message(ws, lang):
    question = "How many deals do I act on today?"
    prompt, grounded = q._grounded_prompt(question, lang=lang)
    assert grounded is True
    msg = prompt.index("=== HER MESSAGE ===")
    reminder = prompt.find(REMINDERS[lang])
    assert reminder > prompt.index(question, msg) > msg                  # after her words, not up in the rules
    assert reminder < prompt.index("Your answer (plain text):")
    assert prompt.count(REMINDERS[lang]) == 1
    assert prompt.index("=== DATA ===") < msg                            # the half-Spanish DATA comes before it


def test_a_screenshot_language_rule_replaces_the_reminder(ws, monkeypatch):
    rules = "LANGUAGE for this message (overrides rule 1): she wrote no caption, so answer in the language of the text."
    for lang in (None, "es", "en"):
        prompt, _ = q._grounded_prompt("Elena sent a screenshot.", extra_rules=rules, lang=lang)
        tail = prompt[prompt.index("=== HER MESSAGE ==="):]
        assert not any(r in tail for r in REMINDERS.values()), lang
        assert "LANGUAGE for this message" in prompt[:prompt.index("=== DATA ===")]

    import src.core.llm_judge as judge                                  # the real screenshot path, no model call
    seen = []
    monkeypatch.setattr(judge, "_call_llm", lambda prompt, max_tokens=0: (seen.append(prompt) or "ok", []))
    assert q.answer_screenshot("", "job posting", "Senior AI Engineer — remote, LATAM") == "ok"
    tail = seen[0][seen[0].index("=== HER MESSAGE ==="):]
    assert not any(r in tail for r in REMINDERS.values())
    assert "LANGUAGE for this message (overrides rule 1)" in seen[0]


# ── (b) 🤖 AI working / appointmentscheduled is NOT an interview ────────────────────────────────────────────

def test_ai_working_is_never_an_interview(ws):
    assert "NOT an interview" in q._STAGE_LABELS["appointmentscheduled"]
    assert re.search(r'"🤖 AI working" are NOT interviews', q._GROUNDED_RULES)
    assert "Never call them interviews" in q._GROUNDED_RULES
    prompt, _ = q._grounded_prompt("Do I have interviews?", lang="en")
    assert "appointmentscheduled" not in prompt                          # the raw id never reaches the model
    assert "WITHIN — AI Creative Specialist — stage: 🤖 AI working (not triaged — NOT an interview)" in prompt


# ── (c) a header with HubSpot totals: the count is HubSpot's, the list is not called complete ──────────────

@pytest.mark.parametrize("shape", sorted(NEW_HEADERS))
def test_header_totals_are_the_counts_and_no_list_claims_completeness(tmp_path, monkeypatch, shape):
    line2, extra = NEW_HEADERS[shape]
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2, extra))
    block = q._shared_deals_block(now=NOW)
    assert OLD_LABEL not in block
    assert f"Snapshot taken {STAMP} (UTC)." in block                    # the line-2 regex still matches
    assert "HubSpot totals by stage" in block and "🔥 I act today: 14" in block
    fire = _line(block, "🔥 I act today:")
    assert "HubSpot total 14 — only 6 listed here, NOT the full list" in fire
    assert "all 6 listed" not in fire and "(6)" not in fire
    assert all(name in fire for name in FIRE)
    assert "🔥 I act today deals first (not all of them are listed here)" in block  # never "every 🔥" with 8 missing
    assert "not all of them fit" not in block                           # no cause is given for the gap
    assert "HubSpot total 2266 — only 2 listed here" in _line(block, "🤖 AI working")
    assert "HubSpot total 72 — only 1 listed here" in _line(block, "⏳ Sent:")
    assert "all " not in block.split("Deals in this snapshot")[1].split("\n•")[0]


def test_all_listed_only_when_the_total_equals_the_rows(tmp_path, monkeypatch):
    line2 = f"# {STAMP} · 10 live job deals · HubSpot totals: 🔥 I act today 6 · ⏳ Sent 1 · 🤖 AI working 2266."
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2))
    block = q._shared_deals_block(now=NOW)
    assert "HubSpot total 6 — all 6 listed" in _line(block, "🔥 I act today:")
    assert "every 🔥 I act today deal" in block
    assert "HubSpot total 1 — all 1 listed" in _line(block, "⏳ Sent:")
    # a stage the header gives no total for says it counts rows only
    assert "1 in this snapshot (rows only, not a HubSpot total)" in _line(block, "💬 They replied")


def test_this_week_shares_the_fire_emoji_and_keeps_its_own_total(tmp_path, monkeypatch):
    line2 = (f"# {STAMP} · 10 live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act today 14"
             " · 🔥 I act this week 3 · ⏳ Sent 72 · 💬 They replied 118 · 🤖 AI working 2266 — listed: 🔥 I act today 6 of"
             " 14, 🔥 I act this week 0 of 3, all 2 ⏳/💬 that entered that stage in the last 14 days, the 2 newest 🤖.")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2))
    block = q._shared_deals_block(now=NOW)
    assert "🔥 I act today: 14 · I act this week: 3 · ⏳ Sent: 72" in block
    assert "HubSpot total 3 — none listed here" in _line(block, "I act this week:")
    assert "HubSpot total 14 — only 6 listed here" in _line(block, "🔥 I act today:")


def test_the_listed_part_of_the_header_is_never_read_as_a_total(tmp_path, monkeypatch):
    line2 = (f"# {STAMP} · 10 live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act today ?"
             " · ⏳ Sent 72 — listed: 🔥 I act today 6 of 14, all 2 ⏳/💬 that entered that stage in the last 14 days.")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2))
    block = q._shared_deals_block(now=NOW)
    assert "6 in this snapshot (rows only, not a HubSpot total)" in _line(block, "🔥 I act today:")
    assert "all 6 listed" not in block


def test_a_deal_not_in_the_rows_is_never_called_missing_from_hubspot(tmp_path, monkeypatch):
    for line2 in (OLD_HEADER, NEW_HEADERS["hs-deal-prep 16 Oct"][0]):
        monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path / str(len(line2)), line2))
        assert "never that she has no such deal" in q._shared_deals_block(now=NOW)


def test_the_whole_prompt_carries_the_total(ws):
    prompt, _ = q._grounded_prompt("¿Cuántos tengo en 🔥 I act today?", lang="es")
    assert "HubSpot total 14" in prompt and OLD_LABEL not in prompt


def test_cto_aipa_real_dry_run_header_reads_back_as_14(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, CTO_DRY_RUN_LINE2, rows=CTO_DRY_RUN_ROWS))
    block = q._shared_deals_block(now=datetime(2026, 10, 16, 17, 30, tzinfo=timezone.utc))
    assert "Snapshot taken 2026-10-16T17:04:13.109Z (UTC)." in block and "WARNING" not in block
    assert "🔥 I act today: 14 · I act this week: 0 · ⏳ Sent: 72" in block
    assert "HubSpot counts every deal named HIRING, so a few may not be job postings" in block
    assert "HubSpot total 14 — all 14 listed" in _line(block, "🔥 I act today:")
    assert "job deals only" not in block                                # 14 named HIRING = 14 job deals
    assert "The 36 rows below are a SELECTION, not every open deal: every 🔥 I act today deal" in block
    assert "entered that stage in the last 14 days" in block            # the window comes from the header
    assert "HubSpot total 72 — only 14 listed here, NOT the full list" in _line(block, "⏳ Sent:")
    assert "HubSpot total 1421 — only 2 listed here" in _line(block, "🤖 AI working")


# cto-aipa's totals count every deal NAMED HIRING; its "listed:" part counts job deals. A HIRING-named deal that is not
# a job posting must neither inflate her 🔥 count nor be explained as "did not fit".
MOCK_LINE2 = (f"# {STAMP} · {{rows}} live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act "
              "today 15 · 🔥 I act this week 0 · ⏳ Sent 16 · 💬 They replied 3 · 🤖 AI working 200 — listed: {listed}, "
              "all 13 ⏳/💬 job deals that entered that stage in the last 14 days, no 🤖 rows (their count is in the "
              "totals); besides these, 2 🔥 or recent ⏳/💬 deal(s) are named HIRING but are not job postings (not "
              "listed). For a count use these totals, never the rows. Use this for the mock interview:")


def test_a_hiring_named_non_job_never_inflates_the_fire_count(tmp_path, monkeypatch):
    line2 = MOCK_LINE2.format(rows=14, listed="every 🔥 job deal")     # cto-aipa mock-14 dry run: 15 named, 14 jobs
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2, rows=_fire_rows(14)))
    block = q._shared_deals_block(now=NOW)
    assert "🔥 I act today: 14 job deals (15 named HIRING)" in block
    fire = _line(block, "🔥 I act today:")
    assert ("HubSpot total 14 — all 14 listed (job deals only: HubSpot has 15 deals named HIRING here, 1 of them not "
            "a job posting)") in fire
    assert "every 🔥 I act today deal" in block
    assert "not all of them" not in block and "total 15" not in block


def test_a_partial_fire_list_uses_the_job_count_and_gives_no_cause(tmp_path, monkeypatch):
    line2 = MOCK_LINE2.format(rows=6, listed="🔥 I act today 6 of 14, 🔥 I act this week 0 of 0")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2, rows=_fire_rows(6)))
    block = q._shared_deals_block(now=NOW)
    assert "HubSpot total 14 — only 6 listed here, NOT the full list (job deals only" in _line(block, "🔥 I act today:")
    assert "🔥 I act today deals first (not all of them are listed here)" in block
    assert "not all of them fit" not in block


def test_an_every_claim_the_rows_cannot_back_is_not_believed(tmp_path, monkeypatch):
    # header says "every 🔥 job deal" with 14 named HIRING and no non-job deals, but the file holds 6 🔥 rows
    line2 = (f"# {STAMP} · 6 live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act today 14 · "
             "⏳ Sent 72 — listed: every 🔥 job deal, all 0 ⏳/💬 job deals that entered that stage in the last 14 days.")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2, rows=_fire_rows(6)))
    block = q._shared_deals_block(now=NOW)
    assert "HubSpot total 14 — only 6 listed here, NOT the full list" in _line(block, "🔥 I act today:")
    assert "every 🔥 I act today deal" not in block and "job deals only" not in block


def test_no_fire_total_means_no_claim_about_the_fire_list(tmp_path, monkeypatch):
    # cto-aipa prints "undefined" when a search returns no total; the other stages still carry one
    line2 = (f"# {STAMP} · 6 live job deals listed below · HubSpot totals (deal name contains HIRING): 🔥 I act today "
             "undefined · ⏳ Sent 72 — listed: 🔥 I act today 6 of NaN, all 0 ⏳/💬 job deals that entered that stage in "
             "the last 14 days.")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, line2, rows=_fire_rows(6)))
    block = q._shared_deals_block(now=NOW)
    assert "6 in this snapshot (rows only, not a HubSpot total)" in _line(block, "🔥 I act today:")
    assert "SELECTION, not every open deal: 🔥 I act today deals first, then" in block
    assert "every 🔥" not in block and "not all of them" not in block


def test_openclaw_rule_lines_are_never_read_as_totals(tmp_path, monkeypatch):
    rules = ["# Ask Q1/5 in total, ⏳ Sent 3 times max, 🔥 I act today 9 in total"]
    for line2, sent in ((OLD_HEADER, None), (NEW_HEADERS["labels on line 2"][0], 72)):
        monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path / str(sent), line2, rules))
        block = q._shared_deals_block(now=NOW)
        assert "⏳ Sent: 3" not in block and "HubSpot total 3" not in block and "HubSpot total 9" not in block
        if sent is None:
            assert "HubSpot totals by stage" not in block and not re.search(r"HubSpot total \d", block)
        else:
            assert f"⏳ Sent: {sent}" in block and "🔥 I act today: 14" in block


def test_the_window_is_the_headers_never_a_hardcoded_14(tmp_path, monkeypatch):
    seven = NEW_HEADERS["hs-deal-prep 16 Oct"][0].replace("last 14 days", "last 7 days")
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path / "7", seven))
    assert "entered that stage in the last 7 days" in q._shared_deals_block(now=NOW)
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path / "none", NEW_HEADERS["labels on line 2"][0]))
    block = q._shared_deals_block(now=NOW)
    assert "then recent ⏳ Sent and 💬 They replied deals" in block and "14 days" not in block


def test_stage_totals_never_answer_a_dated_question(ws):
    block = q._shared_deals_block(now=NOW)
    assert "how many deals a stage has now" in block and "rule 5 and the HISTORY block still apply" in block
    assert 'for any "how many"' not in block


# ── (d) the old header without totals still parses, and says it counts rows only ──────────────────────────

def test_old_header_without_totals_still_parses(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, OLD_HEADER))
    block = q._shared_deals_block(now=NOW)
    assert f"Snapshot taken {STAMP} (UTC)." in block and "WARNING" not in block
    assert OLD_LABEL not in block and not re.search(r"HubSpot total \d", block)
    assert "HubSpot totals by stage" not in block
    assert "this sheet carries no HubSpot totals" in block and "never call a list complete" in block
    fire = _line(block, "🔥 I act today:")
    assert "6 in this snapshot (rows only, not a HubSpot total)" in fire
    assert all(name in fire for name in FIRE)
    assert sum(ln.startswith("• ") for ln in block.splitlines()) == len(ROWS)
    late = q._shared_deals_block(now=datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc))
    assert "WARNING: this snapshot is 3 hours old" in late


def test_a_header_line_2_the_regex_does_not_know_keeps_the_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "_OPENCLAW_WS", _sheet(tmp_path, "# some other header"))
    block = q._shared_deals_block(now=NOW)
    assert "Snapshot taken" not in block and not re.search(r"HubSpot total \d", block)
    assert sum(ln.startswith("• ") for ln in block.splitlines()) == len(ROWS)


# ── the live sheet on this machine (Oracle), when there is one ─────────────────────────────────────────────

def test_the_live_sheet_on_this_machine_never_overclaims():
    """Smoke test against the real sheet (Oracle). HubSpot's totals are re-read here from line 2 with the producer's
    own labels, independently of the parser: a stage may say "all N listed" only when N is its row count and does not
    exceed HubSpot's total (below it only with the job-deals note the header backs); a header without totals may
    produce no HubSpot total at all."""
    path = Path.home() / ".openclaw" / "workspace" / "deals" / "TOOLS.md"
    if not path.exists():
        pytest.skip("no OpenClaw deals sheet on this machine")
    block = q._shared_deals_block()
    if not block:
        pytest.skip("the deals sheet has no rows")
    assert OLD_LABEL not in block
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = {}
    for ln in lines:
        m = re.match(r"### .*\(([a-z]+)\)\s*$", ln)
        if m:
            rows[m.group(1)] = rows.get(m.group(1), 0) + 1
    line2 = lines[1].partition("listed:")[0] if len(lines) > 1 else ""
    producer = {"qualifiedtobuy": "🔥 I act today", "presentationscheduled": "🔥 I act this week",
                "decisionmakerboughtin": "⏳ Sent", "contractsent": "💬 They replied",
                "appointmentscheduled": "🤖 AI working"}                  # cto-aipa hs-deal-prep.cjs LBL
    raw = {}
    for stage, lbl in producer.items():
        m = re.search(rf"{re.escape(lbl)} (\d+)", line2)
        if m:
            raw[stage] = int(m.group(1))
    if not raw:
        assert not re.search(r"HubSpot total \d", block), "a header without totals produced a HubSpot total"
    for stage, label in q._STAGE_LABELS.items():
        for ln in block.splitlines():
            m = re.match(rf"\s+{re.escape(label)}: HubSpot total (\d+) — all (\d+) listed", ln)
            if m:
                assert int(m.group(1)) == int(m.group(2)) == rows.get(stage, 0), ln
                assert stage in raw and int(m.group(1)) <= raw[stage], ln
                if int(m.group(1)) < raw[stage]:                   # fewer than named HIRING: the header says why
                    n = m.group(1)
                    assert "job deals only" in ln, ln
                    assert "every 🔥 job deal" in lines[1] or f"{n} of {n}" in lines[1].partition("listed:")[2], ln
