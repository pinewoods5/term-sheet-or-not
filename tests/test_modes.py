"""The Operator/Scout split.

Two modes now differ in what they can actually find out, and the ways that can
go wrong are quiet: a Scout response carrying a URL, or a prompt that still
tells it to go and look something up. These assert the split holds at every
layer it touches -- request, schema, prompt, and validation.
"""

import json
import re
from pathlib import Path

import pytest

from evaluator import schema
from evaluator.client import MAX_SEARCHES, _request_kwargs
from evaluator.prompts import system_prompt, user_message
from evaluator.rubric import MODES, searches_web

FIXTURES = Path(__file__).parent / "fixtures"


def test_only_the_operator_searches():
    assert searches_web("operator") is True
    assert searches_web("scout") is False


# --------------------------------------------------------------------------
# The request
# --------------------------------------------------------------------------


def test_operator_gets_three_searches():
    tools = _request_kwargs("operator", {})["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "web_search"
    assert tools[0]["max_uses"] == MAX_SEARCHES == 3


def test_scout_sends_no_tools_key_at_all():
    """An empty list still puts the model in a tool-using frame of mind."""
    assert "tools" not in _request_kwargs("scout", {})


@pytest.mark.parametrize("mode", MODES)
def test_both_modes_still_pin_the_output_schema(mode):
    kwargs = _request_kwargs(mode, {})
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["thinking"] == {"type": "adaptive"}


# --------------------------------------------------------------------------
# The schema -- the field that would induce invented URLs
# --------------------------------------------------------------------------


def test_research_notes_exists_only_where_it_can_be_filled_honestly():
    assert "research_notes" in schema.evaluation_schema("operator")["properties"]
    assert "research_notes" not in schema.evaluation_schema("scout")["properties"]
    assert "research_notes" not in schema.api_schema("scout")["properties"]


def test_scout_response_citing_sources_is_rejected():
    data = json.loads((FIXTURES / "scout_response.json").read_text())
    schema.validate("scout", data)  # clean fixture passes

    data["research_notes"] = [
        {"claim": "nothing exists", "finding": "three do", "source_url": "https://example.com"}
    ]
    with pytest.raises(ValueError, match="no web access"):
        schema.validate("scout", data)


def test_operator_response_still_requires_research_notes():
    data = json.loads((FIXTURES / "operator_response.json").read_text())
    schema.validate("operator", data)
    del data["research_notes"]
    with pytest.raises(ValueError, match="research_notes"):
        schema.validate("operator", data)


# --------------------------------------------------------------------------
# The prompts -- no instruction to look anything up, and no implied lookup
# --------------------------------------------------------------------------


def test_scout_prompt_is_told_it_has_no_web_access():
    prompt = system_prompt("scout")
    assert "NO WEB ACCESS" in prompt
    assert "research_notes" not in prompt
    for banned in ("use web search", "from the results you", "real URLs"):
        assert banned.lower() not in prompt.lower(), banned


def test_scout_prompt_bans_the_specific_overclaims():
    prompt = system_prompt("scout").lower()
    for rule in ("no urls", "funding rounds", "hedge it honestly", "cutoff"):
        assert rule in prompt, rule


def test_scout_prompt_still_names_what_reasoning_alone_catches():
    prompt = system_prompt("scout").lower()
    for capability in ("tam arithmetic", "too vaguely to sell", "contradictions"):
        assert capability in prompt, capability


def test_operator_prompt_budgets_its_three_searches():
    prompt = system_prompt("operator")
    assert "budget of THREE searches" in prompt
    # the three worth verifying, in priority order
    assert prompt.index("COMPETITIVE CLAIM") < prompt.index("WHY-NOW")
    assert prompt.index("WHY-NOW") < prompt.index("TAM NUMBER")


def test_closing_line_matches_what_the_mode_can_do():
    assert "search first" in user_message("operator", {})
    scout = user_message("scout", {})
    assert "no lookups on this run" in scout
    assert "search first" not in scout


def test_a_scout_response_containing_a_url_is_rejected():
    """Enforced rather than merely instructed.

    "Don't invent URLs" is the kind of rule that holds until the one time it
    doesn't, and a fabricated source is the single most damaging thing this
    mode could emit -- it is the app claiming it checked something it cannot
    check. So the contract refuses it outright rather than trusting the prompt.
    """
    data = json.loads((FIXTURES / "scout_response.json").read_text())
    schema.validate("scout", data)

    leaked = json.loads((FIXTURES / "scout_response.json").read_text())
    leaked["thesis"] += " See https://example.com/competitor for the incumbent."
    with pytest.raises(ValueError, match="cited a URL"):
        schema.validate("scout", leaked)


def test_the_url_guard_does_not_apply_to_the_operator():
    """The Operator's whole value is real links, so it must stay unaffected."""
    data = json.loads((FIXTURES / "operator_response.json").read_text())
    assert any("http" in n["source_url"] for n in data["research_notes"])
    schema.validate("operator", data)
