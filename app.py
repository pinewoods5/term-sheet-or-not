"""Term Sheet or Not — FastAPI app.

Serves the single-page frontend and the evaluation API.

Run with:
    uvicorn app:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from evaluator.forms import FORMS

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Term Sheet or Not")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/forms")
def forms() -> dict:
    """The form definitions, so the frontend and the prompt can't drift apart."""
    return FORMS


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
