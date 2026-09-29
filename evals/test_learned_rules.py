"""
Eval: rules learned from Elena's rejections (src/core/learned_rules.py) and the sync that
writes them (scripts/judge_feedback_sync.py). Added 2026-09-27.

Offline and deterministic — no network, no LLM, $0. Each case is a real rejection of hers
(HubSpot, Sep 2026) or the false positive it must never produce.
"""
import importlib.util
from pathlib import Path

from src.core.learned_rules import learned_veto, load_rules, norm_company

ROOT = Path(__file__).resolve().parents[1]

RULES = {
    "closed_posting": {"enabled": True, "taught_by": ["Solutions Architect (AI-First) @ Byldd"]},
    "eligibility": {"patterns": ["born_in", "citizenship", "w2_only"],
                    "taught_by": ["Remote AI Engineer @ HireLATAM"]},
    "country_code_list": {"enabled": True, "taught_by": ["AI Evaluation Specialist @ Micro1is"]},
    "tools_not_hers": {"enabled": True, "tools": ["airtable", "monday.com"],
                       "taught_by": ["Monday.com Solutions Architect @ Coconut VA"]},
    "rejected_companies": {"enabled": True, "companies": ["jerry ai"], "counts": {"jerry ai": 5},
                           "taught_by": ["Manager, AI Agents and Platform x5"]},
    "out_of_field_titles": {"enabled": True, "titles": ["Growth Marketing & Paid Media Specialist"],
                            "taught_by": ["Growth Marketing & Paid Media Specialist"]},
}


def _load_sync():
    spec = importlib.util.spec_from_file_location("judge_feedback_sync_lr", ROOT / "scripts" / "judge_feedback_sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── fail-safe ────────────────────────────────────────────────────────────────
def test_no_rules_never_vetoes():
    assert learned_veto("Monday.com Solutions Architect", "Jerry.ai", "This job post is closed.", rules={}) == (False, "")


def test_missing_or_broken_file_means_no_rules(tmp_path):
    assert load_rules(tmp_path / "absent.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_rules(bad) == {}


# ── each rule catches what taught it ─────────────────────────────────────────
def test_closed_posting():
    ok, why = learned_veto("Solutions Architect (AI-First)", "Byldd", "Brief\nThis job post is closed.", rules=RULES)
    assert ok and "closed_posting" in why and "Byldd" in why


def test_born_in_is_about_people_not_companies():
    assert learned_veto("Remote AI Engineer", "HireLATAM", "We only hire specialists born in LATAM.", rules=RULES)[0]
    assert not learned_veto("AI Automation Lead", "Acme", "Our company was born in Berlin in 2019.", rules=RULES)[0]


def test_citizenship_and_w2():
    assert learned_veto("AI Architect", "X", "Only USC or GC, EAD or H1 transfer.", rules=RULES)[0]
    assert learned_veto("AI Architect", "X", "This is W2 employment.", rules=RULES)[0]
    assert not learned_veto("AI Architect", "X", "Contract, W2 or 1099, open worldwide.", rules=RULES)[0]


def test_country_code_list_excludes_panama():
    ok, why = learned_veto("AI Evaluation Specialist", "micro1",
                           "Location: Remote (US, CA, UK, IE, AU, NZ)", rules=RULES)
    assert ok and "US" in why
    assert not learned_veto("AI Evaluation Specialist", "micro1", "Remote (US, PA, MX)", rules=RULES)[0]
    assert not learned_veto("AI Evaluation Specialist", "micro1", "Remote (US, CA) or anywhere in LATAM", rules=RULES)[0]


def test_two_letter_words_that_are_not_countries_are_not_a_roster():
    # "(AI, ML)" is a skills list, not a residency list — it must never park a job.
    assert not learned_veto("AI Automation Lead", "X", "Experience with (AI, ML) tooling.", rules=RULES)[0]


def test_tool_she_does_not_use_only_in_title():
    assert learned_veto("Monday.com Solutions Architect", "Coconut VA", "", rules=RULES)[0]
    assert not learned_veto("AI Solutions Architect", "Coconut VA", "We use Monday.com internally.", rules=RULES)[0]


def test_company_she_rejected_repeatedly():
    assert norm_company("Jerry.ai") == "jerry ai"
    assert learned_veto("Senior PM, Agentic AI", "Jerry.ai", "", rules=RULES)[0]
    assert not learned_veto("Senior PM, Agentic AI", "Jerry", "", rules=RULES)[0]


def test_same_kind_of_role_as_an_out_of_field_rejection():
    assert learned_veto("Paid Media & Growth Marketing Manager", "Y", "", rules=RULES)[0]
    assert not learned_veto("AI Product Manager", "Y", "", rules=RULES)[0]


# ── a location veto that contradicts criterion 2 is overruled (28 Sep 2026) ──
def test_latam_open_listing_overrules_a_location_veto():
    from src.core.llm_judge import latam_veto_is_wrong
    assert latam_veto_is_wrong("Senior Solutions Engineer- LATAM", "", "")             # Fin, seen in production
    assert latam_veto_is_wrong("AI Automation Lead", "Remote - Latin America", "")
    assert not latam_veto_is_wrong("AI Solutions Architect", "Remote LATAM", "Colombia only.")
    assert not latam_veto_is_wrong("AI Automation Lead", "LATAM (Brazil, Mexico)", "")
    assert not latam_veto_is_wrong("AI Automation Lead", "Remote", "")                  # nothing says LATAM
    assert not latam_veto_is_wrong("AI Lead", "Remote - LATAM", "Candidates must reside in Brazil or Argentina.")
    # Replay on REAL postings, 28 Sep: the overrule released these three correct vetoes.
    assert not latam_veto_is_wrong("AI Solutions Architect", "Remote",
                                   "Americas team. Candidates may live or work in the U.S. only (USC or GC).")
    assert not latam_veto_is_wrong("AI/GenAI Engineer", "Remote - Americas",
                                   "Remote (specific timezone, GMT-08:00 to GMT-06:00).")
    assert not latam_veto_is_wrong("AI Architect", "Remote LATAM", "Hours: UTC-3 to UTC+1 only for the EMEA desk.")
    # ...and a range that DOES include Panama still overrules.
    assert latam_veto_is_wrong("AI Automation Lead", "Remote - LATAM", "Core hours GMT-6 to GMT-3.")


def test_a_location_our_adapter_wrote_is_not_the_employer_promising_latam():
    from src.core.llm_judge import latam_veto_is_wrong
    from src.core.fit_gate import is_source_default_location, SOURCE_DEFAULT_MARK
    old, new = "Remote — LATAM / Americas", f"Remote — LATAM / Americas (Torre default: {SOURCE_DEFAULT_MARK})"
    assert is_source_default_location(old) and is_source_default_location(new)
    assert not is_source_default_location("Remote - LATAM")                       # an employer's own words
    # Plain Concepts, 28 Sep: Torre gave no countries, the employer page said Portugal/Brazil.
    ctx = "Remote positions available for Senior AI Golang Software Engineer (Brazil, Portugal)."
    assert not latam_veto_is_wrong("Senior AI Software Engineer", old, ctx)
    assert not latam_veto_is_wrong("Senior AI Software Engineer", new, ctx)
    # When the POSTING itself states LATAM, the overrule still works through the default label.
    assert latam_veto_is_wrong("AI Automation Lead", new, "Open to candidates anywhere in Latin America.")


def test_torre_default_label_changes_no_gate_decision():
    from src.autonomous.job_monitor import JobMonitor
    from src.core.fit_gate import iron_clad_fit
    new = JobMonitor._torre_location_string([])
    assert "latam" in new.lower() and "employer stated no location" in new
    desc = "Fully remote. You will build AI automation and agent workflows with Claude and Cursor."
    for title in ("AI Automation Lead", "AI Product Manager", "Senior Software Engineer (Java)"):
        assert iron_clad_fit(title, new, desc) == iron_clad_fit(title, "Remote — LATAM / Americas", desc), title


def test_location_excludes_her_reads_what_the_posting_states():
    from src.core.fit_gate import location_excludes_her
    assert location_excludes_her("x", "Remote", "Candidates may work in the U.S. only.")
    assert location_excludes_her("x", "Remote", "Remote (GMT-08:00 to GMT-06:00)")
    assert location_excludes_her("x", "Brazil", "")
    assert location_excludes_her("x", "LATAM (Brazil, Mexico)", "")
    assert not location_excludes_her("x", "Remote - Worldwide", "")
    assert not location_excludes_her("x", "Remote", "")                                  # silence ≠ exclusion
    assert not location_excludes_her("x", "Remote - LATAM", "Core hours GMT-6 to GMT-3.")


def test_pay_veto_without_stated_pay_is_overruled():
    from src.core.llm_judge import pay_veto_is_wrong, _CRIT6_REASON
    # Seen on the live judge 28 Sep: no pay anywhere, rejected as "6 Pay below her floor".
    assert _CRIT6_REASON.search("6 Pay below her floor.")
    assert _CRIT6_REASON.search("Criterion 6: pay is below her floor")
    assert not _CRIT6_REASON.search("3 The role is not in one of her target lanes.")
    assert pay_veto_is_wrong("Fully remote, open to LATAM. Please write your application answers yourself.")
    # Any stated pay keeps the veto — the judge may be right about it.
    for stated in ("Salary: $1,200 per month.", "USD 15/hour", "Compensation 18k a year",
                   "Pay: 900 USD monthly", "€2.000 per month", "$20/hr"):
        assert not pay_veto_is_wrong("Remote. " + stated), stated
    # Seen on the live judge: "6 Pay below her floor; the assessment disqualifies the use of AI
    # tools". Right verdict, wrong label — a stated AI ban is never overruled.
    assert not pay_veto_is_wrong("Remote, LATAM. The take-home must be completed without the use of AI tools.")


def test_apply_kit_notes_are_never_her_reason():
    s = _load_sync()
    defense = ('<strong>🛡️ TECHNICAL DEFENSE — AI Engineer @ Acme</strong><p>📎 <strong>Tailored CV attached to this '
               'note — use this one:</strong> CV_x.pdf</p><p><strong>Q: Who writes the code?</strong><br>Specialized AI '
               'agents do much of the implementation. I own what gets built, what gets accepted.</p>')
    ready = ('<strong>✅ READY TO SEND — cover letter — drafted against this posting (openai, direct). Read it, then '
             'paste. ---</strong><p>I am applying for the AI Engineer role at Acme. I operate an AI-native environment.</p>')
    hers = "Not a fit: requires 8 years of Java and relocation to Berlin."
    # 28 Sep 2026: before the fix the defense note MASKED her reason and the READY note became one.
    assert s._rejection_reason([{"body": defense}, {"body": hers}], "AI Engineer") == f"her reason: {hers.rstrip('.')}" \
        or s._rejection_reason([{"body": defense}, {"body": hers}], "AI Engineer").startswith("her reason: Not a fit")
    assert s._rejection_reason([{"body": ready}], "AI Engineer") == ""
    assert s._rejection_reason([{"body": defense}], "AI Engineer") == ""
    assert not s._elena_said_applied([{"body": defense}])
    # Found on the real Glean deal the same day: an agent's August promotion note, not her words.
    promoted = ("🟡 [BORDERLINE] Promoted to I Act TODAY on 2026-08-14 at Elena request. Iron-clad gate said NOT a "
                "fit. AI judge said FIT: The role is fully remote and in her lanes.")
    assert s._rejection_reason([{"body": promoted}, {"body": hers}], "Resident Solutions Architect").startswith("her reason: Not a fit")
    # 28 Sep: the Perplexity company brief is web text about the employer — "applied AI" in it is not her applying.
    brief = ('<strong>🔎 COMPANY BRIEF — Acme</strong><p>Acme builds applied AI for insurers and submitted its '
             'S-1 in 2025.</p><p><em>Cited from: acme.com/about</em></p>')
    assert not s._elena_said_applied([{"body": brief}])
    assert s._rejection_reason([{"body": brief}], "AI Engineer") == ""
    assert s._rejection_reason([{"body": brief}, {"body": hers}], "AI Engineer").startswith("her reason: Not a fit")
    # 29 Sep: a hand-staged job's "📌 JOB POSTING" note is agent prose — never her reason, never her "applied".
    staged = ('📌 JOB POSTING: https://www.getonbrd.com/jobs/ops/applied-ai-revops-lead | No cover letter. '
              'Answer the questions with short, specific examples YOU did. Company actively replying; 39 applicants.')
    assert s._rejection_reason([{"body": staged}], "RevOps Lead") == ""
    assert not s._elena_said_applied([{"body": staged}])
    assert s._rejection_reason([{"body": staged}, {"body": hers}], "RevOps Lead").startswith("her reason: Not a fit")
    # Her own word still counts next to any kit note.
    assert s._elena_said_applied([{"body": brief}, {"body": "i applied manually"}])
    assert s._elena_said_applied([{"body": "I applied on GetOnBoard, 28 Sep 2026."}])


def test_auto_sweep_is_never_her_decision():
    """28 Sep: the daily sweep moves CLOSED postings to closedlost. Without the label they would mute
    the company (3 in 90 days), take "she rejected" example slots and lower precision."""
    s = _load_sync()
    swept = {"id": "1", "properties": {"dealname": "[HIRING-VJH-LEAD] AI Program Manager @ Acme", "dealstage": "closedlost",
                                       "hs_lastmodifieddate": "2026-09-29T13:00:00Z",
                                       "closed_lost_reason": "AUTO-SWEEP 2026-09-29: DEAD (posting closed: the page says so)"}}
    ledger, fetched, _ = s._update_ledger("no-key", [swept], {}, {})
    assert ledger == {} and fetched == 0          # never recorded, and no note fetch for it
    # Her own rejection — any other reason, or none — is recorded exactly as before.
    hers = {"id": "2", "properties": {**swept["properties"], "closed_lost_reason": "not a fit"}}
    assert s._is_auto_swept(swept["properties"]) and not s._is_auto_swept(hers["properties"])
    # A deal she moved BACK to I Act TODAY keeps the label but is not a rejection at all.
    back = {**swept["properties"], "dealstage": "qualifiedtobuy"}
    assert not s._is_auto_swept(back)


# ── the sync learns rules from her words, not from VJH's ─────────────────────
def test_sync_builds_rules_from_her_reasons():
    s = _load_sync()
    L = lambda t, stage, why="", applied=None: {"title": t, "company": t.rsplit(" @ ", 1)[-1], "prefix": "HIRING-VJH-LEAD",
                                                "stage": stage, "modified": "2026-09-25T10:00:00Z",
                                                "first_decided": "2026-09-25T10:00:00Z", "why": why, "applied": applied}
    ledger = {
        "1": L("Monday.com Solutions Architect @ Coconut VA", "closedlost", "her reason: I am not an expert in monday.com"),
        "2": L("Airtable/Zapier Automation Consultant @ Q", "closedlost", "her reason: i do not have zapier and airtable"),
        "3": L("Remote AI Engineer @ HireLATAM", "closedlost", "her reason: Hirelatam only hires specialists born in LATAM"),
        "4": L("Solutions Architect (AI-First) @ Byldd", "closedlost",
               "her reason: Look at screenshot; her screenshot shows: Remote; This job post is closed."),
        "5": L("PM, AI Agents @ Jerry.ai", "closedlost"),
        "6": L("Manager, AI Agents @ Jerry.ai", "closedlost"),
        "7": L("Senior PM, AI @ Jerry.ai", "closedlost"),
        "8": L("AI trainer @ micro1", "closedlost"), "9": L("AI x @ micro1", "closedlost"), "10": L("AI y @ micro1", "closedlost"),
        "11": L("Growth Marketing & Paid Media Specialist @ Agent", "closedlost",
                "her reason: I am not an expert in this plus a salary is too low"),
        "12": L("AI Product Manager @ Addi", "decisionmakerboughtin", applied=True),
        "13": L("AI Evaluation Specialist @ Micro1is", "closedlost",
                "her reason: Look at location - then to micro 1; her screenshot shows: Candidates may live or work "
                "remotely in the US, CA, UK, IE, AU, NZ; the post does not state it is closed; pay is not mentioned."),
        "14": L("Hiring manager @ — outreach", "closedlost"), "15": L("Hiring manager @ — outreach", "closedlost"),
        "16": L("Hiring manager @ — outreach", "closedlost"),
        "17": dict(L("Data Role @ Databricks", "closedlost"), first_decided="2026-06-05T00:00:00Z"),
        "18": dict(L("Data Role 2 @ Databricks", "closedlost"), first_decided="2026-06-05T00:00:00Z"),
        "19": dict(L("Data Role 3 @ Databricks", "closedlost"), first_decided="2026-06-05T00:00:00Z"),
    }
    lessons, rules = s._build_lessons_and_rules(ledger)
    assert "monday.com" in rules["tools_not_hers"]["tools"] and "airtable" in rules["tools_not_hers"]["tools"]
    # Zapier is in her OWN target titles ("Automation Architect (n8n / Make / Zapier)") — never learned as not-hers.
    assert "zapier" not in rules["tools_not_hers"]["tools"]
    assert "born_in" in rules["eligibility"]["patterns"]
    assert rules["closed_posting"]["enabled"]
    # "the post does NOT state it is closed" must not count as a closed-posting lesson.
    assert not any("Micro1is" in t for t in rules["closed_posting"]["taught_by"])
    # micro1's screenshot ("US, CA, UK, IE, AU, NZ" with no brackets) teaches the country-code rule.
    assert rules["country_code_list"]["enabled"]
    # micro1 is protected (her income path); "— outreach" junk and a June bulk (Databricks) are ignored.
    assert rules["rejected_companies"]["companies"] == ["jerry ai"]
    assert rules["out_of_field_titles"]["titles"] == ["Growth Marketing & Paid Media Specialist"]
    assert lessons["total_rejections"] == 18
    text = s._lessons_text(lessons, rules)
    assert "From ALL 18" in text and "monday.com" in text and "About the Role" not in text


def test_sync_strips_vjh_own_park_note():
    s = _load_sync()
    note = [{"body": "🚫 [LEARNED closed_posting: the posting says it is closed — taught by X]\n"
                     "Parked, not shown in I Act TODAY. If this is wrong, move the deal: VJH learns from that too.\n\n"
                     "⚠️ MANUAL APPLY REQUIRED — VJH SerpAPI found this job.", "attachments": []}]
    assert s._rejection_reason(note, "AI Automation Lead") == ""


def test_examples_prefer_rejections_with_a_reason():
    s = _load_sync()
    base = {"company": "c", "prefix": "HIRING-VJH-LEAD", "stage": "closedlost", "first_decided": "2026-09-25T00:00:00Z", "applied": None}
    ledger = {str(i): dict(base, title=f"AI Automation Manager {i}", modified=f"2026-09-{27 - i:02d}T00:00:00Z", why="")
              for i in range(12)}
    ledger["old"] = dict(base, title="AI Solutions Consultant Old", modified="2026-08-01T00:00:00Z",
                         why="her reason: Location only Colombia")
    _, negatives = s._pick_examples(ledger)
    assert negatives[0].startswith("AI Solutions Consultant Old — her reason: Location only Colombia")
