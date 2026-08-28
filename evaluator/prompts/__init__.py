"""Assembles the two system prompts.

Both are built from the same parts in the same order -- shared style guide,
mode mandate, the rubric with its scoring anchors, the hard gates, the
evidence policy, and the output contract. Only the middle blocks differ,
which is what keeps the two evaluators sounding like colleagues rather than
two unrelated apps.

The rubric section is generated from evaluator/rubric.py rather than written
out here, so the weights the prompt describes can never drift away from the
weights the scoring actually uses.
"""

from __future__ import annotations

import json

from ..rubric import CATEGORIES, TIERS, searches_web
from . import operator, scout
from .style_guide import style_block

_MODE_BLOCKS = {"operator": operator, "scout": scout}


def _rubric_block(mode: str) -> str:
    lines = [
        "THE RUBRIC",
        "",
        "Score each category from 1 to 10 against the anchors below. The anchors",
        "are what keeps your scoring comparable between evaluations, so use them",
        "literally: find the anchor the founder's evidence actually matches and",
        "score there, rather than starting at 7 and adjusting by feel.",
        "",
        "Use the whole range. Scoring everything 6 or 7 is not caution, it is a",
        "refusal to do the job. If something deserves a 2, give it a 2.",
        "",
    ]
    for category in CATEGORIES[mode]:
        lines.append(f"{category.label} — weight {int(category.weight * 100)}%")
        lines.append(f"  Judging: {category.judging}")
        for score in sorted(category.anchors):
            lines.append(f"  {score}/10 — {category.anchors[score]}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _tiers_block() -> str:
    labels = ", ".join(t.label for t in TIERS.values())
    return f"""\
THE VERDICT BADGE

You do NOT choose the badge and you do NOT output an overall score. Those are
computed from your category scores by the application, which is deliberate --
it means the badge can never disagree with the numbers you gave.

For context, so your prose matches the badge the founder will see, the tiers
are: {labels}.

Write your `headline` and `thesis` at the severity your own scores imply. If
you scored everything 3, do not write a hopeful headline. If you scored
everything 9, do not manufacture doom to seem rigorous.\
"""


_OUTPUT_CONTRACT = """\
OUTPUT

Return JSON matching the provided schema. Nothing else -- no preamble, no
markdown, no commentary around it.

Order the `categories` array exactly as the rubric lists them.\
"""


def system_prompt(mode: str) -> str:
    blocks = _MODE_BLOCKS[mode]
    return "\n\n".join(
        [
            blocks.MANDATE,
            style_block(),
            _rubric_block(mode),
            blocks.HARD_GATES,
            blocks.EVIDENCE_POLICY,
            _tiers_block(),
            _OUTPUT_CONTRACT,
        ]
    )


def user_message(mode: str, answers: dict[str, str]) -> str:
    """The founder's submission, with blanks made explicit.

    Skipped fields are sent as an explicit "(left blank)" rather than dropped,
    because the evaluator is supposed to notice and react to them.
    """
    from ..forms import fields_for  # local import: forms mirrors the frontend

    lines = []
    for step in fields_for(mode):
        lines.append(f"## {step['title']}")
        for field in step["fields"]:
            value = (answers.get(field["k"]) or "").strip()
            lines.append(f"- {field['label']}: {value if value else '(left blank)'}")
        lines.append("")

    # The closing nudge differs by mode: telling the Scout to "search first"
    # would be instructing it to do something it has no tool for.
    closer = (
        "Remember: search first, then score against the anchors, then write."
        if searches_web(mode)
        else "Remember: no lookups on this run. Reason from what they wrote, "
        "score against the anchors, then write."
    )
    return (
        "Here is the submission. Evaluate it.\n\n"
        + "\n".join(lines).rstrip()
        + "\n\n"
        + closer
    )


def debug_dump(mode: str) -> str:  # pragma: no cover - developer convenience
    return json.dumps({"mode": mode, "system": system_prompt(mode)}, indent=2)
