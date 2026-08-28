"""Local persistence. One SQLite file, one table, no ORM.

Evaluations are saved so a result has a permanent URL, survives a refresh, and
can be reopened and re-run later. Nothing leaves the machine.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS evaluations (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    mode        TEXT NOT NULL,
    subject     TEXT NOT NULL,
    overall     REAL NOT NULL,
    tier        TEXT NOT NULL,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS evaluations_recent ON evaluations (created_at DESC);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def subject_of(result: dict) -> str:
    """What to call this evaluation in the history list."""
    answers = result.get("answers", {})
    for key in ("company_name", "idea_one_liner", "one_liner"):
        value = (answers.get(key) or "").strip()
        if value:
            return value[:120]
    return "Untitled"


def save(result: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO evaluations "
            "(id, created_at, mode, subject, overall, tier, payload) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                result["id"],
                result["created_at"],
                result["mode"],
                subject_of(result),
                result["overall_score"],
                result["tier"]["label"],
                json.dumps(result),
            ),
        )


def get(evaluation_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM evaluations WHERE id = ?", (evaluation_id,)
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def recent(limit: int = 8) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, mode, subject, overall, tier "
            "FROM evaluations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
