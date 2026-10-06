"""
Elena's target lanes — the ONE list every screening layer is checked against.

Why this file exists (2026-09-16). The lanes were written out separately in seven
places: two search lists, the career gate, the fit gate, the keyword scorer, the
AI scoring prompt and the LLM judge. Every lane change edited the files in view
and missed others. "AI Product Manager" was opened on 2026-08-05 in the gates and
the searches but never reached the judge — so those jobs passed every gate, scored
85-100, and were vetoed at the last step for four straight days of zero leads.

Now:
  * the LLM judge and the AI scoring prompt RENDER their lane text from here, so
    those two can never disagree with each other again;
  * evals/test_target_lanes.py fails if the career gate, the fit gate, or the
    unverified-posting title check rejects ANY title listed below.

Adding a lane = add it here, run `pytest evals/test_target_lanes.py`, and fix
whichever layer the test names. A lane is only open when that test is green.

Stdlib only: this is imported by the judge, which the SerpAPI ingest process also
loads, and that process runs under system python3.
"""

HOME_TEXT = "Panama (Latin America), UTC-5 all year"
MIN_PAY_TEXT = "$3,000 USD per month"

# 2026-10-06 Professional Outlook p.7 ("Where I fit") and p.8 — her own published words, copied
# as written (p.8's sentence minus its "I'm looking for" opener). The judge renders them, so what
# VJH counts as "her job" is what she tells employers it is. Braces forbidden, same as the lanes:
# the judge prompt goes through str.format().
OUTLOOK_LOOKING_FOR = ("a team that wants someone to own the path from an ambiguous problem to a "
                       "deployed, measurable AI system")
OUTLOOK_GOOD_FIT = ("business problem → process → system design → AI & tools → implementation → "
                    "deployment → people → metrics → iteration")
OUTLOOK_NOT_MY_FIT = ("Roles whose core value is unaided coding, algorithm drills or live coding — "
                      "or proving the work can be done without AI.")

# Each title is a REAL posting shape. Titles are what the tests push through the
# gates, so keep them as employers actually write them.
LANES = (
    {
        "name": "AI PRODUCT & PROGRAM MANAGEMENT",
        # 2026-10-06: "prototyping" added — the Outlook's AI Prototyping Lead is this lane.
        "work": ("owning AI products, agents or automation platforms end to end — "
                 "discovery, prototyping, roadmap, specs, shipping and adoption. No hand-coding "
                 "required."),
        "titles": (
            "AI Product Manager",
            "Senior AI Product Manager",
            "Technical Product Manager, AI",
            "Product Manager, Generative AI",
            "Product Manager, AI Automation",
            "AI Product Owner",
            "AI Product Lead",
            "Head of AI Product",
            "AI Platform Product Manager",
            "AI Program Manager",
            "AI Project Manager",
            "AI Delivery Manager",
            "AI Implementation Manager",
            "AI Product Operations Manager",
            # 2026-10-06 Professional Outlook p.7 ("AI product & transformation") — titles she
            # publishes as hers that VJH had never listed.
            "AI Product & Automation Lead",
            "Generative AI Product Lead",
            "AI Prototyping Lead",
        ),
    },
    {
        "name": "AI SOLUTIONS ARCHITECTURE & CONSULTING",
        "work": ("designing AI and automation solutions for clients or products, advising "
                 "what to build, and leading the implementation."),
        "titles": (
            "AI Solutions Architect",
            "AI Architect",
            "AI Solutions Consultant",
            "AI Systems Consultant",
            "AI Consultant",
            "AI Strategy Consultant",
            "AI Automation Consultant",
            "AI Implementation Specialist",
            "AI Integration Architect",
            "Automation Architect (n8n / Make / Zapier)",
            "Solutions Engineer, AI Platform",
            "Technical Solutions Manager",
            "Technical Account Manager, AI Automation Platform",
            "AI Customer Engineer",
            "Fractional AI Consultant",
            "Forward Deployed AI Strategist",
            # 2026-09-20: added to replace the volume cut from the engineer lane. Each one is
            # traceable to a role she herself marked positive, not invented to pad the list.
            "Technical Account Manager",          # Sr. Technical Account Manager @ Zapier
            "AI Enablement Lead",
        ),
    },
    {
        "name": "AI LEADERSHIP & TRANSFORMATION",
        # 2026-10-06: "innovation" added — the Outlook's AI Innovation Lead is this lane.
        "work": ("setting AI strategy and leading AI adoption, innovation, transformation and "
                 "teams at startups, scale-ups or as a fractional leader. Seniority is NOT a "
                 "reason to reject in this lane — seven years as Deputy CEO is exactly the fit."),
        "titles": (
            "Chief AI Officer",
            "Fractional Chief AI Officer",
            "Head of AI",
            "VP of AI",
            "Director of AI",
            "AI Lead",
            "Head of AI Automation",
            "Head of AI Operations",
            "AI Transformation Lead",
            "AI Transformation Director",
            "AI Adoption Lead",
            "AI Enablement Manager",
            "AI Strategy Lead",
            "AI Governance Lead",
            "Fractional CTO, AI",
            "Founding AI Lead",
            "AI Innovation Lead",                 # 2026-10-06 Professional Outlook p.7
        ),
    },
    {
        "name": "AI AUTOMATION & OPERATIONS",
        # 2026-10-06: reworded to the Outlook's "AI operations & implementation" lane — designing
        # and implementing the workflow is the job, not only running it.
        "work": ("designing, implementing and running AI workflows, automations and agents with "
                 "no-code / low-code tools (n8n, Make, Zapier, Clay) and LLMs, and operating AI "
                 "systems in production."),
        "titles": (
            "AI Automation Specialist",
            "AI Automation Manager",
            "AI Automation Lead",
            "AI Workflow Automation Manager",
            "Workflow Automation Specialist",
            "AI Operations Manager",
            "AI Operations Specialist",
            "AI Agent Operations Manager",
            "AgentOps Lead",
            "GTM Engineer",
            "Go-To-Market Engineer, AI Automation",
            "Conversational AI Designer",
            "Chatbot Designer",
            "AI Process Improvement Lead",
            "AI Process Engineer",        # 2026-09-28: she applied (CivicPlus); the judge called it off-lane
            # 2026-09-20: same replacement intake, same rule — each traceable to a positive.
            "Business Operations Lead, AI",       # Business Ops & Growth Lead @ Niuro
            "AI Solutions Specialist",
            # 2026-10-06 Professional Outlook p.7 ("AI operations & implementation") — titles she
            # publishes as hers that VJH had never listed.
            "AI Operations Lead",
            "AI Implementation Lead",
            "AI Workflow Architect",
            "AI Systems Operator",
            "Agentic Workflow Designer",
        ),
    },
    {
        "name": "AI-AUGMENTED BUILDER / INTEGRATION",
        # 2026-09-20: the generic engineer titles are GONE, on her instruction and on her own
        # labelling data. They were 62% of the ACT-TODAY queue (22 of 35) but 58% of her
        # rejections (7 of 12) and only 17% of her positives (2 of 12). Her recorded reasons are
        # all the same shape: "5-8 years of experience, strong Python and backend skills",
        # "4+ years as an AI Engineer ... MLOps", "8+ years", "Senior-level backend software
        # development, Node.js, TypeScript, AWS, CI/CD".
        #
        # What survives is the integration/deployment half of the lane — the roles where the job
        # is wiring AI into someone's business, not writing their backend by hand. fit_gate has a
        # matching TITLE veto, because the search path often sees only a short snippet with the
        # years requirement missing, and a title veto holds when the description is unreadable.
        "work": ("designing, shipping and operating AI products, agents and integrations by "
                 "directing AI coding tools — the deployment and integration half of the work, "
                 "not building someone's backend by hand."),
        "titles": (
            "AI Automation Engineer",
            "AI Solutions Engineer",
            "AI Integration Engineer",
            "Forward Deployed Engineer",
            "Forward-Deployed AI Engineer",
            "AI Builder",
        ),
        "not": ("generic software-engineering roles wearing an AI label — AI Engineer, Applied / "
                "Senior AI Engineer, Machine Learning Engineer, Founding Engineer, or anything "
                "demanding years of hand-written backend code, a CS degree or a language stack. "
                "She directs AI coding tools; she is not a hand-coding backend engineer."),
    },
    {
        "name": "GEO / AEO / AI SEARCH VISIBILITY",
        "work": ("making companies visible and quotable in AI answers and search — generative- "
                 "and answer-engine optimization, AI-crawler access, structured data, "
                 "technical SEO. She built and runs a full production stack for this."),
        "titles": (
            "GEO Specialist",
            "GEO Manager",
            "AEO Lead",
            "AEO Specialist",
            "AI Search Visibility Lead",
            "LLM Visibility Manager",
            "AI Discovery Manager",
            "Technical SEO Lead",
            "Technical SEO Manager",
            "AI SEO Strategist",
            "Generative Engine Optimization Specialist",
            "Answer Engine Optimization Manager",
        ),
    },
    {
        "name": "AI-QUALIFIED EXECUTIVE SUPPORT",
        # 2026-10-06: the last sentence is new. Elena kept this lane on 6 Oct, yet the judge
        # still vetoed it as "4. This role is primarily administrative" — even for
        # "AI-Forward Executive Assistant to the CEO", a title listed below, when the listing
        # asked for Zapier/Make automations next to inbox and calendar work. A role that covers
        # inbox and calendar AND asks for AI tooling is this lane, not the "not" line.
        "work": ("running and automating a founder's or executive's operations with AI tools "
                 "(ChatGPT / Claude, Zapier / Make / n8n, agents, research and reporting "
                 "automation). An executive or personal assistant whose listing asks the "
                 "assistant to use or build AI tools or automations IS this lane, even when the "
                 "role also covers inbox, calendar and travel."),
        "not": ("generic administrative, secretarial, calendar-only, household, lifestyle or "
                "travel-concierge assistants with no AI or automation in the work itself."),
        "titles": (
            "AI Chief of Staff",
            "Chief of Staff, AI",
            "AI Executive Assistant",
            "AI-Proficient Executive Assistant",
            "AI-Forward Executive Assistant to the CEO",
            "AI Personal Assistant",
            "AI Operations Assistant to the Founder",
            "Executive Operations Manager, AI",
        ),
    },
    # 2026-10-06 (Elena): the "EXPERT AI EVALUATION & TRAINING (contract)" lane is DROPPED. It
    # is not in her Professional Outlook, and the judge must not approve those gigs as hers. Its
    # gate keywords (job_gate / fit_gate) were left alone on purpose: the gates are the RECALL
    # layer, and the judge, which renders this list, is where an off-lane job is now vetoed.
    {
        # 2026-09-28 (Elena: "Make step 2"). Her creative work was invisible to her own job search:
        # not one creative word in any lane, so VJH never searched for it and the judge would have
        # rejected it as marketing. Evidence she can show: 8 published AI films from an automated
        # production pipeline (atuona.xyz/aifilmstudio), 99 published poems in two languages, a bot
        # that drives a dozen image and video models with an LLM as director. In this field,
        # operating the models IS the production method — nothing to apologise for.
        # Added LAST so the letters the judge cites for the other lanes do not shift.
        # 2026-10-06: dropping the evaluation lane moved this one from 3i to 3h. Nothing in the
        # code parses lane letters (grepped); only old log lines say "3i".
        "name": "CREATIVE AI & GENERATIVE MEDIA SYSTEMS",
        "work": ("designing and running generative image, video and audio production end to end — "
                 "concept and narrative, directing the models, and building the pipeline that takes "
                 "an idea to a finished, published film or campaign. Hands-on generation with AI "
                 "models is the craft here."),
        "not": ("video editing, motion graphics, graphic design, photography or social-media content "
                "work done without generative AI; paid-media buying; influencer or UGC gigs."),
        "titles": (
            "Creative Technologist, Generative AI",
            "Creative Technologist (AI)",
            "Generative AI Producer",
            "AI Video Producer",
            "AI Filmmaker",
            "Creative AI Engineer",
            "Generative AI Creative Lead",
            "AI Creative Technology Lead",
            "GenAI Production Lead",
            "AI Content Production Lead",
            "AI Innovation Producer",
            "Head of Generative AI Content",
            # 2026-10-06 Professional Outlook p.7 ("Creative technology"), written as she
            # publishes them. The comma form above stays: employers write both.
            "Creative Technologist — GenAI",
            "Creative AI Pipeline Builder",
        ),
    },
)


def all_titles():
    """Every target title, in lane order."""
    for lane in LANES:
        yield from lane["titles"]


def _letter(i: int) -> str:
    return chr(ord("a") + i)


def _no_braces(text: str) -> str:
    if "{" in text or "}" in text:
        raise ValueError("target lane text must not contain braces")
    return text


def render_lanes_for_prompt(indent: str = "   ") -> str:
    """The lane block both LLM prompts embed. Braces are forbidden: the judge's
    prompt is later passed through str.format()."""
    out = []
    for i, lane in enumerate(LANES):
        out.append(f"{indent}{_letter(i)}) {lane['name']} — {lane['work']}")
        out.append(f"{indent}   Titles include: " + "; ".join(lane["titles"]) + ".")
        if lane.get("not"):
            out.append(f"{indent}   DISQUALIFY the non-AI version: {lane['not']}")
    return _no_braces("\n".join(out))


def render_lane_names_for_prompt() -> str:
    """'a) NAME, b) NAME, ...' — the same letters render_lanes_for_prompt prints.
    2026-10-06: the judge named only some lanes as her "CORE" ones and vetoed the rest as
    "not aligned with her primary target lanes" (Shortical, 5 Oct). Rendering EVERY name from
    here means a lane added later is equal in the prompt the day it is added."""
    return _no_braces(", ".join(f"{_letter(i)}) {lane['name']}" for i, lane in enumerate(LANES)))


def render_fit_for_prompt(indent: str = "  ") -> str:
    """2026-10-06: her Professional Outlook's GOOD FIT / NOT MY FIT lines, for the LLM prompts.
    "Unaided" is the word that matters, so the text says so: coding THROUGH her AI environment
    is her work, and the line must never become a wider coding veto than the judge's own."""
    return _no_braces("\n".join((
        f"{indent}GOOD FIT — {OUTLOOK_LOOKING_FOR}: {OUTLOOK_GOOD_FIT}.",
        f"{indent}NOT MY FIT — {OUTLOOK_NOT_MY_FIT}",
        f"{indent}\"Unaided\" is the word that matters: coding THROUGH her AI environment is her work.",
    )))
