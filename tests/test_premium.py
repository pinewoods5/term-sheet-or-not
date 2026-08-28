"""Access keys.

Every test here runs against a throwaway database -- the fixture repoints
store.DB_PATH -- so running the suite never touches real issued keys.
"""

import sqlite3

import pytest

import premium
import store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    premium.init()


def test_issue_returns_a_prefixed_key_and_an_id():
    key_id, key = premium.issue("alice")
    assert key.startswith(premium.KEY_PREFIX)
    assert len(key) > 24
    assert key_id and key_id != key


def test_issued_keys_are_unique():
    keys = {premium.issue(f"user {i}")[1] for i in range(20)}
    assert len(keys) == 20


def test_a_valid_key_verifies():
    _, key = premium.issue("alice")
    assert premium.verify(key) is True


@pytest.mark.parametrize(
    "candidate",
    [None, "", "wrong", "tsn_", "tsn_notarealkey", "Bearer tsn_x", " "],
)
def test_junk_does_not_verify(candidate):
    premium.issue("alice")  # a real key exists, but not this one
    assert premium.verify(candidate) is False


def test_the_plaintext_key_is_never_stored():
    """The database must not be a list of usable credentials."""
    _, key = premium.issue("alice")
    with sqlite3.connect(store.DB_PATH) as conn:
        dump = "\n".join(line for line in conn.iterdump())
    assert key not in dump
    assert premium._hash(key) in dump


def test_revoked_keys_stop_working():
    key_id, key = premium.issue("alice")
    assert premium.verify(key) is True

    assert premium.revoke(key_id) is True
    assert premium.verify(key) is False

    # revoking twice is a no-op, not an error
    assert premium.revoke(key_id) is False
    assert premium.revoke("nonexistent") is False


def test_revoking_one_key_leaves_the_others_alone():
    alice_id, alice = premium.issue("alice")
    _, bob = premium.issue("bob")
    premium.revoke(alice_id)
    assert premium.verify(alice) is False
    assert premium.verify(bob) is True


def test_verify_records_usage():
    key_id, key = premium.issue("alice")
    assert premium.keys()[0]["uses"] == 0
    assert premium.keys()[0]["last_used_at"] is None

    premium.verify(key)
    premium.verify(key)

    row = next(k for k in premium.keys() if k["id"] == key_id)
    assert row["uses"] == 2
    assert row["last_used_at"] is not None


def test_failed_attempts_do_not_count_as_uses():
    key_id, _ = premium.issue("alice")
    premium.verify("tsn_wrong")
    assert next(k for k in premium.keys() if k["id"] == key_id)["uses"] == 0


def test_cli_round_trip(capsys):
    assert premium.main(["issue", "alice"]) == 0
    printed = capsys.readouterr().out
    key = next(l.split("key: ")[1].strip() for l in printed.splitlines() if l.startswith("key:"))
    key_id = next(l.split("id:")[1].strip() for l in printed.splitlines() if l.startswith("id:"))
    assert premium.verify(key) is True

    assert premium.main(["list"]) == 0
    assert "alice" in capsys.readouterr().out

    assert premium.main(["revoke", key_id]) == 0
    assert premium.verify(key) is False

    assert premium.main(["revoke", "nope"]) == 1
    assert premium.main(["issue"]) == 2
    assert premium.main([]) == 0
