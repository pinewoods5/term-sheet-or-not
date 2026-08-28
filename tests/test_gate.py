"""The Operator gate, and Scout's independence from it.

The requirement driving this file: the free Scout mode must keep working if the
premium system is mid-build, broken, or gone. That is easy to promise and easy
to quietly break, so it is asserted here rather than described in a comment.
"""

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app
import premium
import store

OPERATOR_ANSWERS = {"company_name": "PawClaim", "one_liner": "x", "problem": "y"}
SCOUT_ANSWERS = {"idea_one_liner": "x", "problem": "y"}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", tmp_path / "test.db")
    store.init()
    premium.init()


@pytest.fixture(autouse=True)
def no_real_api(monkeypatch, request):
    """Stub the model call so these tests exercise routing, not the API."""

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


def _post(client, mode, answers, key=None):
    headers = {"X-Access-Key": key} if key else {}
    return client.post(
        "/api/evaluate", json={"mode": mode, "answers": answers}, headers=headers
    )


def _succeeded(response) -> bool:
    return response.status_code == 200 and "event: result" in response.text


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------


def test_operator_without_a_key_is_refused(client):
    r = _post(client, "operator", OPERATOR_ANSWERS)
    assert r.status_code == 402
    assert "access key" in r.json()["detail"]


@pytest.mark.parametrize("key", ["tsn_wrong", "garbage", ""])
def test_operator_with_a_bad_key_is_refused(client, key):
    premium.issue("someone else")
    assert _post(client, "operator", OPERATOR_ANSWERS, key).status_code == 402


def test_operator_with_a_valid_key_gets_through(client):
    _, key = premium.issue("alice")
    assert _succeeded(_post(client, "operator", OPERATOR_ANSWERS, key))


def test_a_revoked_key_stops_working_immediately(client):
    key_id, key = premium.issue("alice")
    assert _succeeded(_post(client, "operator", OPERATOR_ANSWERS, key))

    premium.revoke(key_id)
    assert _post(client, "operator", OPERATOR_ANSWERS, key).status_code == 402


def test_access_endpoint_reports_state_without_echoing_the_key(client):
    _, key = premium.issue("alice")
    body = client.get("/api/access", headers={"X-Access-Key": key}).json()
    assert body == {"operator": True, "available": True}
    assert key not in json.dumps(body)
    assert client.get("/api/access").json()["operator"] is False


# --------------------------------------------------------------------------
# Scout's independence -- the point of the whole design
# --------------------------------------------------------------------------


def test_scout_needs_no_key(client):
    assert _succeeded(_post(client, "scout", SCOUT_ANSWERS))


def test_scout_ignores_whatever_key_it_is_given(client):
    assert _succeeded(_post(client, "scout", SCOUT_ANSWERS, "tsn_total_nonsense"))


def test_scout_survives_the_premium_module_being_gone(client, monkeypatch):
    """The requirement, stated as a test: premium breaks, Scout does not."""
    monkeypatch.setattr(app, "premium", None)

    assert _succeeded(_post(client, "scout", SCOUT_ANSWERS))

    r = _post(client, "operator", OPERATOR_ANSWERS)
    assert r.status_code == 503
    assert "Scout still works" in r.json()["detail"]


def test_scout_survives_the_access_table_being_dropped(client):
    """Scout must not so much as touch the premium schema."""
    with sqlite3.connect(store.DB_PATH) as conn:
        conn.execute("DROP TABLE access_keys")

    assert _succeeded(_post(client, "scout", SCOUT_ANSWERS))


def test_scout_still_validates_its_own_input(client):
    """Being ungated is not being unvalidated."""
    assert _post(client, "scout", {}).status_code == 400
    assert client.post("/api/evaluate", json={"mode": "nope", "answers": {}}).status_code == 400
