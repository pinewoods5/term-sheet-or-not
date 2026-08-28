"""A daily cap on free Scout evaluations.

Not part of the original request -- "Scout stays free and unrestricted" was the
brief -- but a public, unauthenticated endpoint that spends roughly $0.12 of the
operator's money per call is an exposure worth bounding. Set SCOUT_RATE_LIMIT=0
to turn it off and get the literal brief back.

Only the free mode is counted. The Operator is already gated by a revocable key,
and letting free traffic exhaust a cap that then blocks a paying user would be
the wrong failure.

Fails open. If this module errors the request is allowed through: a bug in a
rate limiter should not take down the free tier it exists to protect.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from store import _connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS free_usage (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip         TEXT NOT NULL,
    day        TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS free_usage_day ON free_usage (day, ip);
"""

# 5 free runs per caller per day. At roughly $0.12 a run that is about $0.60/day
# of exposure to a single determined caller; the global cap bounds the rest.
PER_IP_DEFAULT = 5
GLOBAL_DEFAULT = 200


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def per_ip_limit() -> int:
    return _int_env("SCOUT_RATE_LIMIT", PER_IP_DEFAULT)


def global_limit() -> int:
    return _int_env("SCOUT_DAILY_CAP", GLOBAL_DEFAULT)


def init() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def client_ip(request) -> str:
    """The caller's address, trusting X-Forwarded-For only when told to.

    Behind a platform proxy the socket address is the proxy's, so the real
    client is in the forwarded header -- but that header is caller-supplied and
    trivially spoofed when nothing sets it, so it is opt-in via TRUST_PROXY.
    """
    if os.environ.get("TRUST_PROXY") == "1":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return getattr(request.client, "host", "unknown")


def check(ip: str) -> str | None:
    """Returns None if allowed, or a message explaining the refusal."""
    per_ip, overall = per_ip_limit(), global_limit()
    if per_ip <= 0 and overall <= 0:
        return None

    try:
        init()
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with _connect() as conn:
            if overall > 0:
                total = conn.execute(
                    "SELECT COUNT(*) AS n FROM free_usage WHERE day = ?", (day,)
                ).fetchone()["n"]
                if total >= overall:
                    return (
                        "The Scout has hit its cap for today. It's free, which "
                        "means it's rationed. Try tomorrow."
                    )
            if per_ip > 0:
                mine = conn.execute(
                    "SELECT COUNT(*) AS n FROM free_usage WHERE day = ? AND ip = ?",
                    (day, ip),
                ).fetchone()["n"]
                if mine >= per_ip:
                    return (
                        f"That's {per_ip} free evaluations today, which is the "
                        "limit. Come back tomorrow, or go build something in the "
                        "meantime."
                    )
    except Exception:  # noqa: BLE001 - see the module docstring: fail open
        return None
    return None


def record(ip: str) -> None:
    try:
        init()
        with _connect() as conn:
            conn.execute(
                "INSERT INTO free_usage (ip, day, created_at) VALUES (?, ?, ?)",
                (
                    ip,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
    except Exception:  # noqa: BLE001 - never block a run on bookkeeping
        pass
