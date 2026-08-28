"""Term Sheet or Not — FastAPI app.

Serves the single-page frontend, the form definitions, and the evaluation
stream. Run with:

    uvicorn app:app --reload
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ratelimit
import store
from evaluator.client import MissingKey, evaluate
from evaluator.forms import FORMS, field_keys, required_keys
from evaluator.rubric import CATEGORIES

# Premium (Operator) access lives behind a guarded import on purpose. The free
# Scout mode must keep working if this module is mid-build, broken or absent --
# so a failure here downgrades Operator to a 503 and touches nothing else.
try:
    import premium
except Exception:  # noqa: BLE001 - any import failure must be survivable
    premium = None

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    ratelimit.init()
    if premium is not None:
        premium.init()
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        # Not fatal -- saved evaluations are still browsable without a key --
        # but say it loudly at startup rather than at submit time.
        print(
            "\n  WARNING: ANTHROPIC_API_KEY is not set.\n"
            "  Saved results will open, but no new evaluation can run.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-... and restart.\n"
        )
    yield


app = FastAPI(title="Term Sheet or Not", lifespan=lifespan)


class Submission(BaseModel):
    mode: str
    answers: dict[str, str]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/r/{evaluation_id}")
def permalink(evaluation_id: str) -> FileResponse:
    """Same page; the frontend reads the id out of the path and fetches it."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/forms")
def forms() -> dict:
    """Form definitions, so the frontend and the prompt can't drift apart."""
    return FORMS


@app.get("/api/rubric")
def rubric() -> dict:
    """The weights, exposed so the results screen can show its own maths."""
    return {
        mode: [
            {"key": c.key, "label": c.label, "weight": c.weight, "judging": c.judging}
            for c in categories
        ]
        for mode, categories in CATEGORIES.items()
    }


@app.get("/api/history")
def history() -> list[dict]:
    return store.recent()


@app.get("/api/result/{evaluation_id}")
def result(evaluation_id: str) -> dict:
    found = store.get(evaluation_id)
    if not found:
        raise HTTPException(status_code=404, detail="no such evaluation")
    return found


def _require_operator_access(key: str | None) -> None:
    """Gate for the premium mode. Never called on the Scout path."""
    if premium is None:
        raise HTTPException(
            status_code=503,
            detail="The Operator is temporarily unavailable. The Scout still works.",
        )
    if not premium.verify(key):
        raise HTTPException(
            status_code=402,
            detail="The Operator needs an access key. The Scout is free and needs nothing.",
        )


@app.get("/api/access")
def access(x_access_key: str | None = Header(default=None)) -> dict:
    """Whether the presented key unlocks the Operator. Echoes nothing back."""
    ok = premium is not None and premium.verify(x_access_key)
    return {"operator": bool(ok), "available": premium is not None}


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@app.post("/api/evaluate")
def run_evaluation(
    request: Request,
    submission: Submission,
    x_access_key: str | None = Header(default=None),
) -> StreamingResponse:
    if submission.mode not in FORMS:
        raise HTTPException(status_code=400, detail="unknown mode")

    # The gate is checked here and only here. On the scout path nothing below
    # reads the header, imports premium, or touches the access_keys table.
    ip = None
    if submission.mode == "operator":
        _require_operator_access(x_access_key)
    else:
        # Free tier: bounded, because it spends real money and asks for nothing.
        ip = ratelimit.client_ip(request)
        refusal = ratelimit.check(ip)
        if refusal:
            raise HTTPException(status_code=429, detail=refusal)

    allowed = field_keys(submission.mode)
    answers = {k: v for k, v in submission.answers.items() if k in allowed}
    missing = [k for k in required_keys(submission.mode) if not answers.get(k, "").strip()]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing required: {', '.join(missing)}")

    if ip is not None:
        ratelimit.record(ip)

    def stream():
        try:
            for event, payload in evaluate(submission.mode, answers):
                if event == "result":
                    store.save(payload)
                yield _sse(event, payload)
        except MissingKey as exc:
            yield _sse("error", {"message": str(exc)})
        except Exception as exc:  # noqa: BLE001 - the UI needs *something* to show
            yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
