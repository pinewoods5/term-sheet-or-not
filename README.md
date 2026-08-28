# Term Sheet or Not

An AI venture capitalist that tells you the truth about your startup.

Pick one of two evaluators, fill in a short form, and get back a scored,
structured verdict written the way a sharp VC would actually say it in the
replies. Funny, but every joke is attached to a real point.
## The two modes

**The Operator** — for a startup that already exists and is running. Judges the
whole business: traction and financials, team, product/PMF, market and moat,
distribution and clout.

**The Scout** — for an idea you haven't built yet. Judges whether the idea and
the people behind it are worth building at all. It asks nothing about MRR, ARR,
traction, or funding, because there isn't any and asking would tell you it
wasn't listening.

They have separate forms, separate rubrics, and separate system prompts. They
share a voice.

## How the scoring works

The model scores each category 1–10 and writes the prose. It does **not** pick
the overall score or the verdict badge — those are computed in Python from the
category scores (`evaluator/rubric.py`). That means the badge can never
disagree with the numbers underneath it, and the tier logic is unit-tested
rather than vibes.

**The Operator**

| Category | Weight |
|---|---|
| Traction & Financials | 30% |
| Team | 25% |
| Product & PMF | 20% |
| Market & Moat | 15% |
| Distribution & Clout | 10% |

Traction leads because post-launch it's the only input a founder can't narrate
around. "Fundability" isn't a sixth category — it's the weighted composite.

**The Scout**

| Category | Weight |
|---|---|
| Team & Founder-Market Fit | 35% |
| Unfair Advantage & Connections | 25% |
| Idea Strength | 20% |
| Market & Timing | 20% |

Roughly how seed investors behave pre-revenue. Connections sits high because at
idea stage, access to distribution is the only thing separating an idea from a
wish.

Each category carries scoring anchors describing what a 2, 5, 8 and 10 actually
look like, which is what keeps scores comparable between runs — without them the
same startup drifts a couple of points every time you submit it.

**The badge** is one of six fixed tiers, derived from the weighted total:

| Tier | Score |
|---|---|
| `TERM SHEET` | 88–100 |
| `WAGMI` | 72–87 |
| `MID` | 48–71 |
| `NGMI` | 25–47 |
| `SKILL ISSUE` | 0–24 |
| `DELUSIONAL BUT MIGHT WORK` | any mid-range total with a 5+ point spread between the best and worst category |

That last one is a deterministic override, not a mood. A 9-team with a 3-market
genuinely isn't the same animal as a flat 6, and calling both of them MID would
help neither founder.

## Running it locally

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app:app --reload
```

Then open http://localhost:8000.

Each evaluation is one streamed call to `claude-opus-5` with web search enabled,
so it takes 30–60 seconds and costs real money. The search is what lets it name
your actual competitors instead of hand-waving about the landscape — what it
finds shows up in the "What I found when I looked it up" section with links.

Results are saved to `data/app.db` (SQLite, gitignored) and get a permanent
`/r/<id>` URL. Nothing leaves your machine except the evaluation request itself.
No accounts, no auth — it's built for one person running it locally.

## Tests

```
python -m pytest
```

Covers the scoring arithmetic, every verdict-tier boundary from both sides, the
variance override, the model-output contract, and the properties the prompts
have to hold — including that nothing in the Scout rubric depends on numbers a
pre-build founder can't have.

## Layout

```
app.py               routes, SSE streaming, request validation
store.py             sqlite persistence
evaluator/
  forms.py           form definitions — the single source of truth, served to the frontend
  rubric.py          weights, scoring anchors, tier logic
  schema.py          the JSON contract the model fills in, plus response validation
  result.py          assembles the payload the UI renders
  client.py          the Claude call: web search, structured output, streaming
  prompts/
    style_guide.py   the voice: persona, phrase bank, density rule, hard bans
    operator.py      Operator mandate, hard gates, research directive
    scout.py         Scout mandate, hard gates, research directive
static/              hand-written frontend, no build step
```
