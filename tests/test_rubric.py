"""Tests for the scoring layer.

This is the part of the app that must never be vibes, so it gets the tests:
the weights, the arithmetic, every tier boundary from both sides, and the
variance override that produces DELUSIONAL BUT MIGHT WORK.
"""

import pytest

from evaluator import rubric


def flat(mode: str, value: int) -> dict[str, int]:
    """Every category scored the same -- zero spread, so no variance override."""
    return {c.key: value for c in rubric.CATEGORIES[mode]}


@pytest.mark.parametrize("mode", rubric.MODES)
def test_weights_sum_to_one(mode):
    assert sum(rubric.weights(mode).values()) == pytest.approx(1.0)


@pytest.mark.parametrize("mode", rubric.MODES)
def test_every_category_has_four_anchors(mode):
    for category in rubric.CATEGORIES[mode]:
        assert sorted(category.anchors) == [2, 5, 8, 10]


def test_scout_has_no_traction_category():
    keys = {c.key for c in rubric.CATEGORIES["scout"]}
    assert not keys & {"traction", "clout"}


@pytest.mark.parametrize("mode", rubric.MODES)
def test_flat_scores_scale_linearly(mode):
    assert rubric.overall_score(mode, flat(mode, 1)) == 10.0
    assert rubric.overall_score(mode, flat(mode, 10)) == 100.0
    assert rubric.overall_score(mode, flat(mode, 7)) == 70.0


def test_weighted_arithmetic():
    # 9*.30 + 8*.25 + 7*.20 + 6*.15 + 5*.10 = 7.5 -> 75.0
    scores = {"traction": 9, "team": 8, "product": 7, "market": 6, "clout": 5}
    assert rubric.overall_score("operator", scores) == 75.0


def test_missing_and_out_of_range_scores_are_rejected():
    with pytest.raises(ValueError, match="missing scores"):
        rubric.overall_score("operator", {"traction": 5})
    bad = flat("operator", 5) | {"team": 11}
    with pytest.raises(ValueError, match="out of range"):
        rubric.overall_score("operator", bad)


@pytest.mark.parametrize(
    "overall,expected",
    [
        (100.0, "term_sheet"),
        (88.0, "term_sheet"),
        (87.9, "wagmi"),
        (72.0, "wagmi"),
        (71.9, "mid"),
        (48.0, "mid"),
        (47.9, "ngmi"),
        (25.0, "ngmi"),
        (24.9, "skill_issue"),
        (10.0, "skill_issue"),
    ],
)
def test_tier_boundaries(overall, expected):
    # Flat scores keep the spread at zero so only the band logic is exercised.
    tier = rubric.verdict_tier("operator", flat("operator", 5), overall)
    assert tier.key == expected


def test_variance_override_fires_on_a_lopsided_profile():
    scores = {"traction": 3, "team": 9, "product": 5, "market": 4, "clout": 8}
    overall, tier = rubric.grade("operator", scores)
    assert rubric.VARIANCE_RANGE[0] <= overall < rubric.VARIANCE_RANGE[1]
    assert tier.key == "delusional"


def test_variance_override_needs_a_spread_of_five():
    four = {"traction": 5, "team": 9, "product": 6, "market": 6, "clout": 6}
    assert max(four.values()) - min(four.values()) == 4
    assert rubric.grade("operator", four)[1].key != "delusional"

    five = four | {"traction": 4}
    assert rubric.grade("operator", five)[1].key == "delusional"


def test_variance_override_does_not_reach_outside_its_range():
    # Excellent but uneven still gets the good badge; bad but uneven stays bad.
    high = {"traction": 10, "team": 10, "product": 10, "market": 10, "clout": 5}
    assert rubric.overall_score("operator", high) >= 88.0
    assert rubric.grade("operator", high)[1].key == "term_sheet"

    low = {"traction": 2, "team": 8, "product": 3, "market": 3, "clout": 2}
    assert rubric.overall_score("operator", low) < 48.0
    assert rubric.grade("operator", low)[1].key == "ngmi"


@pytest.mark.parametrize("mode", rubric.MODES)
def test_grade_is_consistent_with_its_parts(mode):
    scores = flat(mode, 6)
    overall, tier = rubric.grade(mode, scores)
    assert overall == rubric.overall_score(mode, scores)
    assert tier is rubric.verdict_tier(mode, scores, overall)
