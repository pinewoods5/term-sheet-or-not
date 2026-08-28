"""The free-tier cap.

Scoped deliberately: it must bound Scout, never touch the Operator, and never
be the reason a free evaluation fails when something else has gone wrong.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app
import premium
import ratelimit
import store

SCOUT = {"idea_one_liner": "x", "problem": "y"}
OPERATOR = {"company_name": "PawClaim", "one_liner": "x", "problem": "y"}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    store.init()
    ratelimit.init()
    premium.init()


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch, request):
    def fake_evaluate(mode, answers):
        payload = json.loads(
            (request.path.parent / "fixtures" / f"{mode}_response.json").read_text()
        )
        from evaluator.result import build

        yield "result", build(mode, payload, answers)

    monkeypatch.setattr(app, "evaluate", fake_evaluate)


@pytest.fixture
def client():
    with TestClient(app.app) as c:
        yield c


def scout(client):
    return client.post("/api/evaluate", json={"mode": "scout", "answers": SCOUT})


def test_free_runs_are_capped_per_ip(client, monkeypatch):
    monkeypatch.setenv("SCOUT_RATE_LIMIT", "3")
    monkeypatch.setenv("SCOUT_DAILY_CAP", "0")

    for _ in range(3):
        assert scout(client).status_code == 200

    blocked = scout(client)
    assert blocked.status_code == 429
    assert "limit" in blocked.json()["detail"]


def test_a_global_cap_applies_across_callers(client, monkeypatch):
    monkeypatch.setenv("SCOUT_RATE_LIMIT", "0")
    monkeypatch.setenv("SCOUT_DAILY_CAP", "2")

    assert scout(client).status_code == 200
    assert scout(client).status_code == 200
    assert scout(client).status_code == 429


def test_setting_the_limit_to_zero_restores_unrestricted_scout(client, monkeypatch):
    """The literal brief was "free and unrestricted" -- that must stay reachable."""
    monkeypatch.setenv("SCOUT_RATE_LIMIT", "0")
    monkeypatch.setenv("SCOUT_DAILY_CAP", "0")
    for _ in range(12):
        assert scout(client).status_code == 200


def test_the_cap_never_touches_the_operator(client, monkeypatch):
    monkeypatch.setenv("SCOUT_RATE_LIMIT", "1")
    monkeypatch.setenv("SCOUT_DAILY_CAP", "1")
    _, key = premium.issue("alice")

    assert scout(client).status_code == 200
    assert scout(client).status_code == 429  # free tier exhausted

    for _ in range(5):
        r = client.post(
            "/api/evaluate",
            json={"mode": "operator", "answers": OPERATOR},
            headers={"X-Access-Key": key},
        )
        assert r.status_code == 200, "paying users must not inherit the free cap"


def test_a_broken_limiter_lets_traffic_through(client, monkeypatch):
    """Fail open: a bug here must not take down the tier it protects."""
    monkeypatch.setenv("SCOUT_RATE_LIMIT", "1")

    def explode(*_args, **_kwargs):
        raise sqlite_error()

    def sqlite_error():
        import sqlite3

        return sqlite3.OperationalError("no such table")

    monkeypatch.setattr(ratelimit, "_connect", explode)
    assert scout(client).status_code == 200
    assert scout(client).status_code == 200


def test_forwarded_headers_are_only_trusted_when_configured(monkeypatch):
    class FakeRequest:
        headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        client = type("C", (), {"host": "10.0.0.1"})()

    monkeypatch.delenv("TRUST_PROXY", raising=False)
    assert ratelimit.client_ip(FakeRequest()) == "10.0.0.1"

    monkeypatch.setenv("TRUST_PROXY", "1")
    assert ratelimit.client_ip(FakeRequest()) == "1.2.3.4"


def test_defaults_match_what_the_readme_advertises(monkeypatch):
    """Keeps the documented numbers and the real ones from drifting apart."""
    for var in ("SCOUT_RATE_LIMIT", "SCOUT_DAILY_CAP"):
        monkeypatch.delenv(var, raising=False)
    assert ratelimit.per_ip_limit() == 50
    assert ratelimit.global_limit() == 200

    readme = (Path(__file__).parent.parent / "README.md").read_text()
    assert "| `SCOUT_RATE_LIMIT` | `50` |" in readme
    assert "| `SCOUT_DAILY_CAP` | `200` |" in readme
