"""Tests for the model-output contract and the result builder."""

import json
import re
from pathlib import Path

import pytest

from evaluator import forms, rubric, schema
from evaluator.prompts import system_prompt, user_message
from evaluator.result import build

FIXTURES = Path(__file__).parent / "fixtures"


def load(mode: str) -> dict:
    return json.loads((FIXTURES / f"{mode}_response.json").read_text())


@pytest.mark.parametrize("mode", rubric.MODES)
def test_fixture_validates(mode):
    schema.validate(mode, load(mode))


@pytest.mark.parametrize("mode", rubric.MODES)
def test_schema_matches_the_rubric(mode):
    s = schema.evaluation_schema(mode)
    keys = [c.key for c in rubric.CATEGORIES[mode]]
    assert s["properties"]["categories"]["items"]["properties"]["key"]["enum"] == keys
    assert s["properties"]["categories"]["minItems"] == len(keys)
    assert s["properties"]["mode"]["enum"] == [mode]


@pytest.mark.parametrize("mode", rubric.MODES)
def test_schema_is_closed_everywhere(mode):
    """additionalProperties:false throughout, or strict mode won't hold."""

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema.evaluation_schema(mode))


@pytest.mark.parametrize(
    "mutate,message",
    [
        (lambda d: d.update(mode="scout"), "mode is"),
        (lambda d: d["categories"].pop(), "expected 5 categories"),
        (lambda d: d["categories"][0].update(score=0), "not an integer 1-10"),
        (lambda d: d["categories"][0].update(key="nonsense"), "do not match"),
        (lambda d: d["fix_this_first"].pop(), "expected 3 fix_this_first"),
        (lambda d: d["fix_this_first"][0].update(rank=3), "ranks must be"),
        (lambda d: d.update(red_flags=[]), "red_flags must be a list of 1-4"),
        (lambda d: d.update(headline="  "), "headline is missing"),
    ],
)
def test_malformed_responses_are_rejected(mutate, message):
    data = load("operator")
    mutate(data)
    with pytest.raises(ValueError, match=message):
        schema.validate("operator", data)


@pytest.mark.parametrize("mode", rubric.MODES)
def test_build_attaches_scoring_and_labels(mode):
    data = load(mode)
    result = build(mode, data, {"company_name": "Test"})

    expected = rubric.grade(mode, schema.scores_from(data))
    assert result["overall_score"] == expected[0]
    assert result["tier"]["label"] == expected[1].label

    assert [c["key"] for c in result["categories"]] == [
        c.key for c in rubric.CATEGORIES[mode]
    ]
    assert all(c["label"] and c["weight"] for c in result["categories"])
    assert [f["rank"] for f in result["fix_this_first"]] == [1, 2, 3]
    assert result["id"] and result["created_at"]


# --------------------------------------------------------------------------
# The prompts. These assert the properties the app depends on, not the wording.
# --------------------------------------------------------------------------


def test_scout_form_asks_nothing_about_traction():
    text = json.dumps(forms.FORMS["scout"]).lower()
    for word in ("mrr", "arr", "revenue", "churn", "burn", "runway", "raised", "valuation"):
        assert word not in text, f"scout form mentions {word}"


def test_scout_rubric_never_scores_traction():
    """The vernacular block may mention burn multiples; the rubric may not.

    What matters is that nothing the scout is asked to *score* depends on
    numbers a pre-build founder cannot have.
    """
    banned = re.compile(r"\b(mrr|arr|revenue|churn|burn|runway|raised|valuation)\b", re.I)
    for category in rubric.CATEGORIES["scout"]:
        assert not banned.search(category.judging), category.key
        for anchor in category.anchors.values():
            assert not banned.search(anchor), (category.key, anchor)

    # ...and the mandate says so out loud, so the model can't infer otherwise.
    assert "no revenue" in system_prompt("scout").lower()


@pytest.mark.parametrize("mode", rubric.MODES)
def test_system_prompt_carries_the_live_rubric(mode):
    prompt = system_prompt(mode)
    for category in rubric.CATEGORIES[mode]:
        assert category.label in prompt
        assert f"weight {int(category.weight * 100)}%" in prompt
        for anchor in category.anchors.values():
            assert anchor.split(".")[0] in prompt


@pytest.mark.parametrize("mode", rubric.MODES)
def test_system_prompt_withholds_the_badge_decision(mode):
    prompt = system_prompt(mode)
    assert "You do NOT choose the badge" in prompt
    for tier in rubric.TIERS.values():
        assert tier.label in prompt


@pytest.mark.parametrize("mode", rubric.MODES)
def test_user_message_marks_skipped_fields(mode):
    filled = next(iter(forms.required_keys(mode)))
    message = user_message(mode, {filled: "something specific"})
    assert "something specific" in message
    assert "(left blank)" in message
    # every question reaches the model under the label the founder saw
    for step in forms.fields_for(mode):
        for field in step["fields"]:
            assert field["label"] in message
