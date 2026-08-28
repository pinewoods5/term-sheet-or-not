"""Term Sheet or Not — FastAPI app.

Serves the single-page frontend, the form definitions, and the evaluation
stream. Run with:

    uvicorn app:app --reload
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import store
from evaluator.client import MissingKey, evaluate
from evaluator.forms import FORMS, field_keys, required_keys
from evaluator.rubric import CATEGORIES

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
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


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@app.post("/api/evaluate")
def run_evaluation(submission: Submission) -> StreamingResponse:
    if submission.mode not in FORMS:
        raise HTTPException(status_code=400, detail="unknown mode")

    allowed = field_keys(submission.mode)
    answers = {k: v for k, v in submission.answers.items() if k in allowed}
    missing = [k for k in required_keys(submission.mode) if not answers.get(k, "").strip()]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing required: {', '.join(missing)}")

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
