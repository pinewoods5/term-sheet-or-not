# Term Sheet or Not

An AI venture capitalist that tells you the truth about your startup.

You pick one of two evaluators, fill in a short form, and get back a scored,
structured verdict written the way a sharp VC would actually say it in the
replies — funny, but every joke attached to a real point.

## The two modes

**The Operator** — for a startup that already exists and is running. Judges the
whole business: traction and financials, team, product/PMF, market and moat,
distribution and clout.

**The Scout** — for an idea you haven't built yet. Judges whether the idea and
the people behind it are worth building at all. Asks nothing about MRR, ARR,
traction, or funding, because there isn't any and asking would be silly.

## Running it locally

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app:app --reload
```

Then open http://localhost:8000.

Each evaluation is one Claude API call and costs money. Results are stored
locally in `data/app.db` and never leave your machine except for the evaluation
request itself.

## Status

Work in progress. See `docs` in the repo history for the build order.
