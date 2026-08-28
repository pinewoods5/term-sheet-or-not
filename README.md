# Term Sheet or Not

An AI venture capitalist that tells you the truth about your startup.

Pick one of two evaluators, fill in a short form, and get back a scored,
structured verdict written the way a sharp VC would actually say it in the
replies. Funny, but every joke is attached to a real point.
## The two modes

**The Operator** — for a startup that already exists and is running. Judges the
whole business: traction and financials, team, product/PMF, market and moat,
distribution and clout.

**The Operator** is the premium mode and needs an access key. It runs three web
searches per evaluation to check your competitive claim, your why-now, and your
TAM number against the live market, and it links what it finds.

**The Scout** — for an idea you haven't built yet. Judges whether the idea and
the people behind it are worth building at all. It asks nothing about MRR, ARR,
traction, or funding, because there isn't any and asking would tell you it
wasn't listening.

**The Scout is free and needs no key.** It also has no web access: it reasons
from what you typed plus what it already knows, and it is built to say so rather
than imply it checked anything. It will still catch TAM arithmetic that doesn't
multiply, a customer described too vaguely to sell to, and contradictions
between your own answers — which is most of what matters at idea stage. It never
produces a URL, and the response contract rejects one if it tries.

They have separate forms, separate rubrics, separate system prompts, and
different access to the world. They share a voice.

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

Each evaluation is one streamed call to `claude-opus-5` and costs real money.
Operator runs 3 web searches (~30–60s); Scout runs none (~20–40s). Search is the
largest single line item in a run — Anthropic bills $10 per 1,000 searches on top
of the tokens the results inject — which is why the free mode doesn't get it.

## Access keys

The Operator is gated. Issue a key to yourself:

```
python -m premium issue "your name"
```

The key is printed once and stored only as a SHA-256 hash. Paste it into the
prompt behind the Operator card; the browser keeps it in `localStorage` and
sends it as an `X-Access-Key` header.

```
python -m premium list             # who has keys, and how much they've used
python -m premium revoke <id>      # kill one key without touching the others
```

The Scout path never reads that header, never imports the premium module, and
never touches the keys table — so it keeps working even if the premium side is
broken or removed entirely. There are tests that assert exactly that.

## Environment variables

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required to run any evaluation. |
| `SCOUT_RATE_LIMIT` | `50` | Free Scout runs per IP per day. `0` disables. |
| `SCOUT_DAILY_CAP` | `200` | Free Scout runs per day in total. `0` disables. |
| `TRUST_PROXY` | unset | Set to `1` when behind a proxy so `X-Forwarded-For` is used for rate limiting. Leave unset locally — the header is caller-supplied and spoofable when nothing sets it. |

The caps apply to Scout only. The Operator is already key-gated, and letting
free traffic exhaust a cap that then blocked a paying user would be the wrong
failure. The limiter also fails open: if it errors, the request goes through.

Results are saved to `data/app.db` (SQLite, gitignored) and get a permanent
`/r/<id>` URL. Nothing leaves your machine except the evaluation request itself.
No accounts, no auth — it's built for one person running it locally.

## Tests

```
python -m pytest
```

Covers the scoring arithmetic, every verdict-tier boundary from both sides, the
variance override, the model-output contract, access keys and the gate, the free
tier caps, and the properties the prompts have to hold — including that nothing
in the Scout rubric depends on numbers a pre-build founder can't have, and that
a Scout response containing a URL is rejected outright.

The frontend is exercised too. There's no Node here, so `tests/frontend/` runs
`static/app.js` against a DOM stub under macOS JavaScriptCore and asserts the
app boots, the Operator card locks, and the Scout card never does.

## Layout

```
app.py               routes, SSE streaming, request validation
store.py             sqlite persistence
evaluator/
  forms.py           form definitions — the single source of truth, served to the frontend
  rubric.py          weights, scoring anchors, tier logic
  schema.py          the JSON contract the model fills in, plus response validation
  result.py          assembles the payload the UI renders
  client.py          the Claude call: per-mode tools, structured output, streaming
  prompts/
    style_guide.py   the voice: persona, phrase bank, density rule, hard bans
    operator.py      Operator mandate, hard gates, research directive
    scout.py         Scout mandate, hard gates, research directive
premium.py           access keys: issue, verify, revoke, plus a CLI
ratelimit.py         daily caps on the free tier
static/              hand-written frontend, no build step
```
