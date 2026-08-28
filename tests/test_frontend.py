"""Runs the frontend against a DOM stub under JavaScriptCore.

There is no Node on this machine and no browser automation available, so
without this the hand-written frontend ships entirely unexercised. It already
reached a browser once as a blank page: a build-step string replacement hit
two call sites instead of one, which moved the bootstrap block inside go() and
left render() never called. Every assertion here fails on that bug.

macOS-only, since it leans on osascript's JavaScriptCore. Skipped elsewhere.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from evaluator.forms import FORMS
from evaluator.result import build

ROOT = Path(__file__).parent.parent
FRONTEND = ROOT / "tests" / "frontend"

pytestmark = pytest.mark.skipif(
    shutil.which("osascript") is None, reason="needs macOS JavaScriptCore"
)


def _fixtures() -> str:
    result = build(
        "operator",
        json.loads((FRONTEND.parent / "fixtures" / "operator_response.json").read_text()),
        {"company_name": "PawClaim"},
    )
    return (
        "const FIXTURES = "
        + json.dumps(
            {
                "/api/forms": FORMS,
                "/api/history": [],
                # locked by default; the smoke test unlocks in-place
                "/api/access": {"operator": False, "available": True},
            }
        )
        + ";\nconst RESULT = "
        + json.dumps(result)
        + ";\n"
    )


def test_frontend_boots_renders_and_responds(tmp_path):
    script = "\n".join(
        [
            (FRONTEND / "dom_stub.js").read_text(),
            _fixtures(),
            (ROOT / "static" / "app.js").read_text(),
            (FRONTEND / "smoke.js").read_text(),
        ]
    )
    path = tmp_path / "run.js"
    path.write_text(script)

    proc = subprocess.run(
        ["osascript", "-l", "JavaScript", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = (proc.stdout + proc.stderr).strip()
    assert "PASS" in output and "FAIL" not in output, output
