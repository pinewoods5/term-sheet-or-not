"""The JSON contract the model must fill in.

Passed to the API as `output_config.format`, which guarantees the response's
final text block is valid JSON matching this shape. The frontend therefore
never parses prose, and a malformed roast is not a failure mode we have to
design around.

Note what is *not* in here: the overall score and the verdict tier. Those are
computed from the category scores in rubric.py.
"""

from __future__ import annotations

from .rubric import CATEGORIES


def _string(desc: str, max_len: int | None = None) -> dict:
    field: dict = {"type": "string", "description": desc}
    if max_len:
        field["maxLength"] = max_len
    return field


def _obj(props: dict, desc: str = "") -> dict:
    schema = {
        "type": "object",
        "properties": props,
        "required": list(props),
        "additionalProperties": False,
    }
    if desc:
        schema["description"] = desc
    return schema


def evaluation_schema(mode: str) -> dict:
    keys = [c.key for c in CATEGORIES[mode]]
    count = len(keys)

    category = _obj(
        {
            "key": {"type": "string", "enum": keys},
            "score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Score against the anchors given for this category. "
                               "Use the whole range. A 7 for everything is a refusal to judge.",
            },
            "verdict": _string(
                "The judgement in eight words or fewer. Quotable, no hedging.", 70
            ),
            "reasoning": _string(
                "One to three sentences. Must quote or cite at least one specific "
                "number or phrase the founder actually typed. No generic filler."
            ),
        }
    )

    fix = _obj(
        {
            "rank": {"type": "integer", "minimum": 1, "maximum": 3},
            "title": _string("The fix, stated as an instruction.", 90),
            "why": _string("Why this one is the highest leverage, in one or two sentences."),
            "do_this": _string("The concrete first action, specific enough to start on Monday."),
        }
    )

    note = _obj(
        {
            "title": _string("Short label for the note.", 80),
            "note": _string("Two to four sentences on a longer-horizon issue or opportunity."),
        }
    )

    research = _obj(
        {
            "claim": _string("The founder's claim you checked."),
            "finding": _string("What the search actually turned up."),
            "source_url": _string("A real URL from the search results."),
        }
    )

    return _obj(
        {
            "mode": {"type": "string", "enum": [mode]},
            "headline": _string(
                "The verdict as one line, under 140 characters. This is the pinned "
                "post. Make it quotable and specific to this company.",
                140,
            ),
            "thesis": _string(
                "Two to four sentences giving the overall read: what this is, what "
                "it hinges on, and what you'd need to see to change your mind."
            ),
            "categories": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": category,
                "description": f"Exactly {count} entries, one per category, in the order given.",
            },
            "fix_this_first": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": fix,
                "description": "The three highest-leverage changes, ranked. Ranked by "
                               "impact per unit of effort, not by how bad they are.",
            },
            "strategic_notes": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": note,
            },
            "green_flags": {
                "type": "array",
                "minItems": 0,
                "maxItems": 3,
                "items": _string("Something genuinely working, stated plainly."),
            },
            "red_flags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": _string("Something genuinely broken, stated plainly."),
            },
            "research_notes": {
                "type": "array",
                "minItems": 0,
                "maxItems": 5,
                "items": research,
                "description": "What web search turned up when you checked their claims. "
                               "Empty only if you genuinely could not search.",
            },
        }
    )


def validate(mode: str, data: dict) -> dict:
    """Structural check on a model response.

    `output_config.format` already constrains the shape, so this is a belt to
    that braces -- but it runs on every response anyway, because the scoring
    layer downstream indexes into these fields and a clear error here beats a
    KeyError three functions later.
    """
    keys = [c.key for c in CATEGORIES[mode]]

    def fail(msg: str):
        raise ValueError(f"malformed evaluation: {msg}")

    if not isinstance(data, dict):
        fail(f"expected an object, got {type(data).__name__}")
    if data.get("mode") != mode:
        fail(f"mode is {data.get('mode')!r}, expected {mode!r}")

    for field in ("headline", "thesis"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            fail(f"{field} is missing or empty")

    cats = data.get("categories")
    if not isinstance(cats, list) or len(cats) != len(keys):
        fail(f"expected {len(keys)} categories, got {len(cats or [])}")
    seen = [c.get("key") for c in cats]
    if sorted(seen) != sorted(keys):
        fail(f"category keys {seen} do not match the {mode} rubric {keys}")
    for c in cats:
        score = c.get("score")
        if not isinstance(score, int) or not 1 <= score <= 10:
            fail(f"score for {c.get('key')} is not an integer 1-10: {score!r}")
        for field in ("verdict", "reasoning"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                fail(f"{field} for {c.get('key')} is missing or empty")

    fixes = data.get("fix_this_first")
    if not isinstance(fixes, list) or len(fixes) != 3:
        fail(f"expected 3 fix_this_first entries, got {len(fixes or [])}")
    if sorted(f.get("rank") for f in fixes) != [1, 2, 3]:
        fail("fix_this_first ranks must be exactly 1, 2 and 3")

    for field, low, high in (("strategic_notes", 2, 4), ("green_flags", 0, 3),
                             ("red_flags", 1, 4), ("research_notes", 0, 5)):
        value = data.get(field)
        if not isinstance(value, list) or not low <= len(value) <= high:
            fail(f"{field} must be a list of {low}-{high} items, got {value!r}")

    return data


def scores_from(data: dict) -> dict[str, int]:
    return {c["key"]: c["score"] for c in data["categories"]}
