"""Field definitions for both evaluators.

This is the single source of truth: the frontend fetches these from
/api/forms and renders whatever it finds, and the prompt builder uses the
same labels when it lays the submission out for the model. Keeping one copy
means a question can't exist on screen under a label the evaluator never sees.

Deliberately, the scout form contains no revenue, traction, or funding field
anywhere. Asking a pre-build founder for their MRR is how you tell them you
weren't listening.

Numeric-ish fields are plain text on purpose: "~8k, lumpy" tells the evaluator
more than a number input would let the founder say.
"""

from __future__ import annotations

FORMS: dict[str, dict] = {
    "operator": {
        "submitLabel": "Get judged",
        "steps": [
            {
                "title": "The basics",
                "blurb": "Who you are and what you claim to do. Keep the one-liner tight — if it takes three sentences, that's already information.",
                "fields": [
                    {"k": "company_name", "label": "Company name", "required": True, "ph": "Acme Inc."},
                    {"k": "one_liner", "label": "One-liner", "required": True,
                     "hint": "What you'd say at a party before they look at their phone.",
                     "ph": "Stripe for veterinary clinics"},
                    {"k": "industry", "label": "Industry / category", "ph": "vertical SaaS, fintech, devtools…"},
                    {"k": "location", "label": "Where are you based?", "ph": "San Francisco, CA"},
                    {"k": "work_mode", "label": "How does the team work?", "type": "select",
                     "options": ["", "In person", "Hybrid", "Fully remote"]},
                    {"k": "founding_date", "label": "When did you start?", "ph": "March 2023"},
                ],
            },
            {
                "title": "Traction & money",
                "blurb": "The part you either can't wait to type or have been dreading. Blank fields are an answer too, and I'll read them as one.",
                "fields": [
                    {"k": "mrr", "label": "MRR", "hint": "Monthly recurring revenue, today.", "ph": "$14,000"},
                    {"k": "arr", "label": "ARR", "hint": "Skip it if it's just MRR × 12 — I can multiply.", "ph": "$168,000"},
                    {"k": "growth_mom", "label": "Month-over-month growth", "hint": "Averaged over the last 6 months, honestly.", "ph": "12%"},
                    {"k": "churn", "label": "Churn", "hint": "Monthly logo or revenue churn. Say which.", "ph": "4% monthly logo churn"},
                    {"k": "cac_ltv", "label": "CAC and LTV", "hint": "Leave it blank if you don't really track it. Don't invent it.", "ph": "CAC ~$400, LTV ~$2,100"},
                    {"k": "funding_raised", "label": "Raised to date", "ph": "$500k pre-seed, angels"},
                    {"k": "burn", "label": "Monthly burn", "ph": "$22,000"},
                    {"k": "runway_months", "label": "Runway", "hint": "Months left at current burn.", "ph": "9 months"},
                    {"k": "raise_ask", "label": "Raising? At what?", "hint": "Amount and valuation, if you're out there now.", "ph": "$1.5M on a $12M post"},
                ],
            },
            {
                "title": "The team",
                "blurb": "The single best predictor of what happens in the next eighteen months.",
                "fields": [
                    {"k": "founder_count", "label": "How many founders?", "ph": "2"},
                    {"k": "founder_backgrounds", "label": "Who are they?", "type": "textarea",
                     "hint": "One line each: name, technical / business / domain, where they came from.",
                     "ph": "Me — technical, 6 yrs backend at Square.\nDana — domain, ran ops at two vet chains."},
                    {"k": "prior_exits", "label": "Prior exits or notable companies",
                     "hint": "Failures count here too. Say them.", "ph": "One acquihire in 2021, one that died at $3k MRR"},
                    {"k": "commitment", "label": "Full-time?", "type": "select",
                     "options": ["", "All founders full-time", "Some full-time, some part-time",
                                 "All part-time / nights and weekends"]},
                    {"k": "technical_ability", "label": "Who writes the code?", "type": "select",
                     "options": ["", "Technical founder in-house", "Hired engineers, no technical founder",
                                 "Outsourced to an agency", "No-code / nobody yet"]},
                ],
            },
            {
                "title": "Product & product-market fit",
                "blurb": "Evidence, not adjectives. \"Users love it\" is an adjective.",
                "fields": [
                    {"k": "problem", "label": "What problem does it solve?", "required": True, "type": "textarea",
                     "hint": "For whom, and what were they doing before you existed?",
                     "ph": "Vet clinics reconcile insurance claims by hand in spreadsheets…"},
                    {"k": "pmf_evidence", "label": "Evidence of PMF", "type": "textarea",
                     "hint": "Retention curves, NPS, waitlist size, quotes — whatever you actually have.",
                     "ph": "68% of week-1 clinics still active at week 12. NPS 41 across 30 responses."},
                    {"k": "competition", "label": "Who else does this?",
                     "hint": "\"No direct competitors\" is a red flag, not a moat.",
                     "ph": "Two incumbents, four seed-stage startups"},
                    {"k": "moat", "label": "What's the moat?", "type": "textarea",
                     "ph": "Integrations into 3 practice-management systems nobody else has…"},
                    {"k": "why_now", "label": "Why now?",
                     "hint": "What changed in the world that makes this possible or urgent this year?"},
                ],
            },
            {
                "title": "Clout & network",
                "blurb": "Distribution is a real asset. Vanity numbers are not. I can tell the difference and so can you.",
                "fields": [
                    {"k": "followers", "label": "Founder audience",
                     "hint": "Follower counts across platforms. Be specific about which.", "ph": "9k on X, 3k LinkedIn"},
                    {"k": "engagement_quality", "label": "What's the engagement actually like?",
                     "hint": "Do the right people reply, or is it bots and \"great post\"?"},
                    {"k": "viral_moments", "label": "Any viral moments?", "ph": "Launch post did 400k impressions, 200 signups"},
                    {"k": "press", "label": "Press coverage", "ph": "TechCrunch mention, one podcast"},
                    {"k": "advisors", "label": "Notable advisors or investors already in"},
                    {"k": "vc_access", "label": "Can you get warm intros to VCs?",
                     "hint": "Honestly. Cold outbound is not access."},
                    {"k": "distribution", "label": "Distribution channels you already own",
                     "hint": "Communities, partnerships, an email list, an existing customer base."},
                ],
            },
        ],
    },
    "scout": {
        "submitLabel": "Tell me if I should build it",
        "steps": [
            {
                "title": "The idea",
                "blurb": "No traction questions here. There isn't any traction. That's the whole point of this mode.",
                "fields": [
                    {"k": "idea_one_liner", "label": "The idea, in one line", "required": True,
                     "ph": "Stripe for veterinary clinics"},
                    {"k": "problem", "label": "What problem does it solve?", "required": True, "type": "textarea",
                     "hint": "Who has it, how badly, and what are they doing about it today?"},
                    {"k": "target_customer", "label": "Who exactly is the customer?",
                     "hint": "\"Small businesses\" is not a customer. Name the person who signs.",
                     "ph": "Practice managers at 2–8 location vet groups"},
                    {"k": "tam", "label": "Rough TAM",
                     "hint": "And how you got to it. Bottom-up beats a number from a report.",
                     "ph": "28k US clinics × $4k/yr ≈ $110M"},
                ],
            },
            {
                "title": "Who's building it",
                "blurb": "At this stage you are most of the investment. Prior failures are a signal in your favour, not a confession.",
                "fields": [
                    {"k": "builders", "label": "Who's on the team?", "type": "textarea",
                     "hint": "One line each: name, what they do, what they've done before."},
                    {"k": "complementary_skills", "label": "How do the skills split?",
                     "hint": "Tech, business, domain — who covers what, and what's missing?"},
                    {"k": "prior_startups", "label": "Prior startup experience",
                     "hint": "Including the ones that didn't work. Especially those."},
                    {"k": "commitment", "label": "Are you doing this full-time?", "type": "select",
                     "options": ["", "Full-time already", "Quitting once something works",
                                 "Nights and weekends indefinitely", "Still deciding"]},
                    {"k": "technical_ability", "label": "Who can actually build it?", "type": "select",
                     "options": ["", "Technical co-founder committed", "Me, I'm technical",
                                 "Planning to hire", "Planning to outsource", "Haven't solved this yet"]},
                ],
            },
            {
                "title": "Why you, why now",
                "blurb": "The two questions every seed investor asks and most founders answer badly.",
                "fields": [
                    {"k": "unfair_advantage", "label": "What's your unfair advantage?", "type": "textarea",
                     "hint": "Something true of you that isn't true of the next hundred people with this idea."},
                    {"k": "domain_expertise", "label": "How well do you know this domain?",
                     "hint": "Years in it, or how you got close to the problem."},
                    {"k": "why_now", "label": "Why now?", "type": "textarea",
                     "hint": "What changed — technology, regulation, behaviour — that makes this the year?"},
                ],
            },
            {
                "title": "Access",
                "blurb": "The part founders underrate hardest. An idea with distribution beats a better idea without it, every time.",
                "fields": [
                    {"k": "distribution_access", "label": "How will the first 100 customers hear about you?",
                     "type": "textarea", "hint": "Channels you already have, not channels that exist."},
                    {"k": "customer_access", "label": "Can you get to your target customer today?",
                     "hint": "Could you get ten of them on a call this week?"},
                    {"k": "capital_access", "label": "Access to capital",
                     "hint": "Savings, angels who'd take your call, an accelerator, a warm VC intro."},
                    {"k": "validation", "label": "Have you talked to anyone about this?", "type": "textarea",
                     "hint": "Customer conversations, a waitlist, a landing page, a friend who said \"sure\"."},
                ],
            },
        ],
    },
}


def fields_for(mode: str) -> list[dict]:
    return FORMS[mode]["steps"]


def field_keys(mode: str) -> set[str]:
    return {f["k"] for step in fields_for(mode) for f in step["fields"]}


def required_keys(mode: str) -> set[str]:
    return {
        f["k"]
        for step in fields_for(mode)
        for f in step["fields"]
        if f.get("required")
    }
