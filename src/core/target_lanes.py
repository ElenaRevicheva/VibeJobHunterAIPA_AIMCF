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

# Each title is a REAL posting shape. Titles are what the tests push through the
# gates, so keep them as employers actually write them.
LANES = (
    {
        "name": "AI PRODUCT & PROGRAM MANAGEMENT",
        "work": ("owning AI products, agents or automation platforms end to end — "
                 "discovery, roadmap, specs, shipping and adoption. No hand-coding required."),
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
        "work": ("setting AI strategy and leading AI adoption, transformation and teams at "
                 "startups, scale-ups or as a fractional leader. Seniority is NOT a reason "
                 "to reject in this lane — seven years as Deputy CEO is exactly the fit."),
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
        ),
    },
    {
        "name": "AI AUTOMATION & OPERATIONS",
        "work": ("building and running automations and AI agents with no-code / low-code "
                 "tools (n8n, Make, Zapier, Clay) and LLMs, and operating AI workflows."),
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
            # 2026-09-20: same replacement intake, same rule — each traceable to a positive.
            "Business Operations Lead, AI",       # Business Ops & Growth Lead @ Niuro
            "AI Solutions Specialist",
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
        "work": ("running and automating a founder's or executive's operations with AI tools "
                 "(ChatGPT / Claude, Zapier / Make / n8n, agents, research and reporting "
                 "automation)."),
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
    {
        "name": "EXPERT AI EVALUATION & TRAINING (contract)",
        "work": ("expert-level evaluation, red-teaming and training of AI models and agents in "
                 "domains she knows: AI systems, automation, product, business and law."),
        "not": "generic data labeling, annotation or transcription gigs.",
        "titles": (
            "AI Evaluation Specialist",
            "LLM Evaluator",
            "AI Red Team Specialist",
            "AI Trainer, Expert Contractor",
            "AI Quality Reviewer",
            "AI Tutor, Business & Product",
        ),
    },
)


def all_titles():
    """Every target title, in lane order."""
    for lane in LANES:
        yield from lane["titles"]


def render_lanes_for_prompt(indent: str = "   ") -> str:
    """The lane block both LLM prompts embed. Braces are forbidden: the judge's
    prompt is later passed through str.format()."""
    out = []
    for i, lane in enumerate(LANES):
        letter = chr(ord("a") + i)
        out.append(f"{indent}{letter}) {lane['name']} — {lane['work']}")
        out.append(f"{indent}   Titles include: " + "; ".join(lane["titles"]) + ".")
        if lane.get("not"):
            out.append(f"{indent}   DISQUALIFY the non-AI version: {lane['not']}")
    text = "\n".join(out)
    if "{" in text or "}" in text:
        raise ValueError("target lane text must not contain braces")
    return text
