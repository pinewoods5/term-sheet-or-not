"""Access keys for the premium (Operator) mode.

Deliberately small and self-contained. It owns one table in the same SQLite
file the evaluations live in, and it is imported by app.py behind a try/except
so that nothing in here can take the free Scout mode down with it.

Keys are issued by hand -- `python -m premium issue "alice"` -- and shown once.
Only their SHA-256 hashes are stored, so the database is not a list of
credentials: losing it means reissuing keys, not leaking them.

Stripe is deliberately not here. When it arrives, its webhook writes rows to
this same table and nothing else in the app has to change.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import sys
from datetime import datetime, timezone

from store import _connect

KEY_PREFIX = "tsn_"

SCHEMA = """
CREATE TABLE IF NOT EXISTS access_keys (
    id           TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    key_hash     TEXT NOT NULL UNIQUE,
    created_at   TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at   TEXT,
    uses         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS access_keys_hash ON access_keys (key_hash);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def init() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def issue(label: str) -> tuple[str, str]:
    """Create a key. Returns (id, key). The key is never recoverable again."""
    init()
    key = KEY_PREFIX + secrets.token_urlsafe(24)
    key_id = secrets.token_hex(4)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO access_keys (id, label, key_hash, created_at) VALUES (?, ?, ?, ?)",
            (key_id, label, _hash(key), _now()),
        )
    return key_id, key


def verify(key: str | None) -> bool:
    """True if this key exists and has not been revoked."""
    if not key or not key.startswith(KEY_PREFIX):
        return False
    init()
    digest = _hash(key)
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, key_hash, revoked_at FROM access_keys WHERE key_hash = ?",
            (digest,),
        ).fetchone()
        # The lookup is by hash, so this comparison is belt to that braces --
        # but it costs nothing and keeps the comparison explicit.
        if row is None or not hmac.compare_digest(row["key_hash"], digest):
            return False
        if row["revoked_at"]:
            return False
        conn.execute(
            "UPDATE access_keys SET last_used_at = ?, uses = uses + 1 WHERE id = ?",
            (_now(), row["id"]),
        )
    return True


def revoke(key_id: str) -> bool:
    init()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE access_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (_now(), key_id),
        )
        return cur.rowcount > 0


def keys() -> list[dict]:
    init()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, label, created_at, last_used_at, revoked_at, uses "
            "FROM access_keys ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# CLI:  python -m premium issue "alice" | list | revoke <id>
# --------------------------------------------------------------------------

USAGE = """\
usage:
  python -m premium issue "<label>"   create a key and print it once
  python -m premium list              show every key, its usage and status
  python -m premium revoke <id>       revoke a key by id\
"""


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0

    command, args = argv[0], argv[1:]

    if command == "issue":
        if not args:
            print(USAGE)
            return 2
        key_id, key = issue(" ".join(args))
        print(f"id:  {key_id}")
        print(f"key: {key}")
        print("\nCopy it now. It is stored only as a hash and cannot be shown again.")
        return 0

    if command == "list":
        rows = keys()
        if not rows:
            print("no keys issued yet")
            return 0
        print(f"{'id':<10} {'label':<24} {'uses':>5}  {'last used':<21} status")
        for row in rows:
            status = "revoked" if row["revoked_at"] else "active"
            print(
                f"{row['id']:<10} {row['label'][:24]:<24} {row['uses']:>5}  "
                f"{(row['last_used_at'] or 'never'):<21} {status}"
            )
        return 0

    if command == "revoke":
        if not args:
            print(USAGE)
            return 2
        if revoke(args[0]):
            print(f"revoked {args[0]}")
            return 0
        print(f"no active key with id {args[0]}")
        return 1

    print(USAGE)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except sqlite3.Error as exc:
        print(f"database error: {exc}", file=sys.stderr)
        sys.exit(1)
