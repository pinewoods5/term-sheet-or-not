"""The scoring rubric: weights, anchors, and the verdict tiers.

The division of labour matters here. The model scores each category 1-10 and
writes the prose. It does *not* pick the overall score or the verdict badge --
this module computes both from the category scores. That way the badge can
never contradict the numbers sitting underneath it, and the whole thing is
unit-testable without spending an API call.

Weights differ per mode because the evidence available differs per mode. For a
running company, revenue and retention are the least-fakeable things a founder
has, so traction leads. For a pre-build idea there is no evidence except the
people and their access, so team and connections carry it.
"""

from __future__ import annotations

from dataclasses import dataclass

MODES = ("operator", "scout")


def searches_web(mode: str) -> bool:
    """Whether this mode gets a live web-search tool.

    Only The Operator does. The Scout reasons from what the founder typed plus
    its own training knowledge, so anything that would imply it checked a claim
    against the live web -- the tool itself, the `research_notes` field, the
    prompt's research directive, the loading copy -- keys off this.
    """
    return mode == "operator"


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    weight: float
    judging: str
    anchors: dict[int, str]


# --------------------------------------------------------------------------
# The Operator -- an existing, running startup.
#
# Traction leads at 30% because post-launch it is the only input a founder
# cannot narrate their way around. Team is a close second at 25% since it
# predicts the next eighteen months better than the last six do. Clout is a
# real multiplier but never a foundation, so it is capped at 10%.
# --------------------------------------------------------------------------

OPERATOR = [
    Category(
        key="traction",
        label="Traction & Financials",
        weight=0.30,
        judging="MRR/ARR, month-over-month growth, churn, CAC/LTV, burn multiple, runway",
        anchors={
            2: "Negligible or flat revenue, or revenue that is really consulting. "
               "Churn above 10% monthly, or unknown. Under 6 months runway with no plan.",
            5: "Real but small revenue growing single-digit percent monthly. Churn "
               "in the 5-8% range. Runway 6-12 months. Unit economics unproven.",
            8: "15%+ month-over-month sustained across 6+ months, net revenue "
               "retention at or above 100%, burn multiple under 1.5, 12+ months runway.",
            10: "Growth a fund would fight over: 20%+ compounding, negative churn, "
                "capital-efficient, default alive without the raise.",
        },
    ),
    Category(
        key="team",
        label="Team",
        weight=0.25,
        judging="founder count and backgrounds, technical ability in-house, full-time commitment, prior exits",
        anchors={
            2: "Part-time founders, no technical ability in-house for a technical "
               "product, or a team with no connection to the problem.",
            5: "Committed full-time, credible backgrounds, but a real gap -- no "
               "domain depth, or engineering is outsourced.",
            8: "Complementary full-time founders who have shipped before, technical "
               "ability in-house, and genuine reason to be the ones doing this.",
            10: "A team with prior exits or deep operator credibility in exactly "
                "this domain, already executing faster than the competition.",
        },
    ),
    Category(
        key="product",
        label="Product & PMF",
        weight=0.20,
        judging="sharpness of the problem, retention and NPS evidence, painkiller vs vitamin",
        anchors={
            2: "No retention data, or retention that falls off a cliff. Testimonials "
               "instead of numbers. Clearly a vitamin.",
            5: "Some evidence -- a waitlist, positive quotes, early cohorts -- but "
               "nothing that proves people would be upset if it disappeared.",
            8: "Flat-tailing retention curves, strong qualitative pull, customers "
               "expanding usage. A painkiller with proof.",
            10: "Undeniable pull: inbound demand outpacing the ability to serve it, "
                "customers building workflows around the product.",
        },
    ),
    Category(
        key="market",
        label="Market & Moat",
        weight=0.15,
        judging="TAM honesty, competitive landscape, why-now, defensibility",
        anchors={
            2: "TAM lifted from a report with no bottom-up check, 'no competitors', "
               "no answer to why now, nothing defensible.",
            5: "Real market, credible size, but crowded and the moat is 'we'll "
               "execute better'.",
            8: "Well-sized market with a specific why-now, a clear wedge, and a moat "
               "that compounds -- data, integrations, switching costs, or distribution.",
            10: "A market inflecting right now where this team's wedge gets "
                "structurally harder to attack every month.",
        },
    ),
    Category(
        key="clout",
        label="Distribution & Clout",
        weight=0.10,
        judging="audience quality, viral moments, press, advisors, warm intro access, owned channels",
        anchors={
            2: "No audience, no owned channel, no warm path to capital or customers. "
               "Cold outbound is the entire plan.",
            5: "Modest audience or a couple of useful relationships, but distribution "
               "is still something to be figured out later.",
            8: "An owned channel that reliably produces customers, credible advisors, "
               "and warm access to the investors they'd want.",
            10: "Distribution is itself the advantage -- the founders can reach their "
                "market on demand and everybody in the space takes their call.",
        },
    ),
]

# --------------------------------------------------------------------------
# The Scout -- a pre-build idea.
#
# There is no traction to weigh, so team and market carry roughly half the
# score, which is how seed investors actually behave pre-revenue. Connections
# is deliberately high at 25%: at idea stage, access to distribution is the
# only thing separating an idea from a wish, and it is the input founders
# underrate most consistently.
# --------------------------------------------------------------------------

SCOUT = [
    Category(
        key="team_fit",
        label="Team & Founder-Market Fit",
        weight=0.35,
        judging="who is building it, complementary skills, prior startup experience including failures",
        anchors={
            2: "A solo non-technical founder planning to outsource a software "
               "product, or a team with no relationship to the problem at all.",
            5: "Capable people with real skills, but a visible gap or no particular "
               "reason it should be them rather than anyone else.",
            8: "Complementary skills covering build and sell, genuine time in the "
               "domain, and prior startup scar tissue.",
            10: "The obvious team for this problem. If they don't build it, whoever "
                "does will wish they had hired them.",
        },
    ),
    Category(
        key="advantage",
        label="Unfair Advantage & Connections",
        weight=0.25,
        judging="distribution access, capital access, access to the target customer",
        anchors={
            2: "No path to the first hundred customers beyond 'post about it', no "
               "capital, and no way to get the target customer on a call.",
            5: "Could reach some customers with effort, some savings or friendly "
               "angels, but nothing that compounds.",
            8: "An existing channel or relationship that reliably reaches the target "
               "customer, plus a credible route to capital.",
            10: "Access most people simply cannot buy: an owned audience of exactly "
                "this customer, or a network that closes the first ten deals.",
        },
    ),
    Category(
        key="idea",
        label="Idea Strength",
        weight=0.20,
        judging="is the problem real and acute, is this a company or a feature",
        anchors={
            2: "A solution looking for a problem, or a feature an incumbent ships in "
               "a quarter. Nobody has been asked whether they want it.",
            5: "A real annoyance for a real group of people, but the pain is mild and "
               "the current workaround is fine.",
            8: "A specific, expensive, recurring problem for an identifiable buyer, "
               "with a clear reason a standalone company is the right shape.",
            10: "A problem people are already hacking around badly and would pay for "
                "today, in a shape that grows into more than the wedge.",
        },
    ),
    Category(
        key="timing",
        label="Market & Timing",
        weight=0.20,
        judging="TAM sanity, the why-now argument, whether the window is actually open",
        anchors={
            2: "A TAM number with no derivation, and no why-now beyond 'AI'.",
            5: "Decent market, plausible timing, but the same argument was true "
               "three years ago and will be true in three more.",
            8: "Honest bottom-up market sizing and a specific change -- technology, "
               "regulation, cost curve, behaviour -- that opened this window recently.",
            10: "A window that is provably open right now and provably closing, in a "
                "market big enough to matter.",
        },
    ),
]

CATEGORIES: dict[str, list[Category]] = {"operator": OPERATOR, "scout": SCOUT}


# --------------------------------------------------------------------------
# Verdict tiers
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Tier:
    key: str
    label: str
    tone: str          # green | yellow | red -- drives the badge colour
    blurb: str


TIERS = {
    "term_sheet": Tier("term_sheet", "TERM SHEET", "green",
                       "Wire the docs. This is a real company."),
    "wagmi": Tier("wagmi", "WAGMI", "green",
                  "Genuinely working. Keep going and don't get distracted."),
    "delusional": Tier("delusional", "DELUSIONAL BUT MIGHT WORK", "yellow",
                       "Wildly uneven. One part of this is excellent and one part is "
                       "held together with tape."),
    "mid": Tier("mid", "MID", "yellow",
                "Not bad. Not yet a company. The gap between those is the work."),
    "ngmi": Tier("ngmi", "NGMI", "red",
                 "Structurally broken in a way more effort will not fix."),
    "skill_issue": Tier("skill_issue", "SKILL ISSUE", "red",
                        "The problem is upstream of the startup."),
}

# Ordered high to low; each entry is (minimum inclusive score, tier key).
BANDS = [
    (88.0, "term_sheet"),
    (72.0, "wagmi"),
    (48.0, "mid"),
    (25.0, "ngmi"),
    (0.0, "skill_issue"),
]

# A profile this uneven gets its own badge instead of being averaged into
# blandness -- a 9 team with a 3 market is not the same animal as a 6 across
# the board, and calling both of them MID would be the least useful thing we
# could tell either founder.
VARIANCE_SPREAD = 5
VARIANCE_RANGE = (48.0, 88.0)


def weights(mode: str) -> dict[str, float]:
    return {c.key: c.weight for c in CATEGORIES[mode]}


def overall_score(mode: str, scores: dict[str, int]) -> float:
    """Weighted 1-10 category scores, expressed 0-100 to one decimal."""
    cats = CATEGORIES[mode]
    missing = [c.key for c in cats if c.key not in scores]
    if missing:
        raise ValueError(f"missing scores for {mode}: {', '.join(missing)}")
    for key, value in scores.items():
        if not 1 <= value <= 10:
            raise ValueError(f"score for {key} out of range 1-10: {value}")
    return round(sum(scores[c.key] * c.weight for c in cats) * 10, 1)


def verdict_tier(mode: str, scores: dict[str, int], overall: float) -> Tier:
    lo, hi = VARIANCE_RANGE
    values = [scores[c.key] for c in CATEGORIES[mode]]
    if lo <= overall < hi and max(values) - min(values) >= VARIANCE_SPREAD:
        return TIERS["delusional"]
    for minimum, key in BANDS:
        if overall >= minimum:
            return TIERS[key]
    return TIERS["skill_issue"]


def grade(mode: str, scores: dict[str, int]) -> tuple[float, Tier]:
    overall = overall_score(mode, scores)
    return overall, verdict_tier(mode, scores, overall)
