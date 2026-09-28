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
