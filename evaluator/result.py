"""Turns a raw model response into the payload the frontend renders.

The model returns scores and prose. Everything numeric or categorical that the
UI displays -- the overall, the badge, the per-category labels and weights --
is attached here from rubric.py, so the displayed rubric always matches the
rubric that did the scoring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .rubric import CATEGORIES, grade
from .schema import scores_from, validate


def build(mode: str, data: dict, answers: dict) -> dict:
    validate(mode, data)
    scores = scores_from(data)
    overall, tier = grade(mode, scores)

    meta = {c.key: c for c in CATEGORIES[mode]}
    order = [c.key for c in CATEGORIES[mode]]
    categories = sorted(data["categories"], key=lambda c: order.index(c["key"]))
    for c in categories:
        c["label"] = meta[c["key"]].label
        c["weight"] = meta[c["key"]].weight

    return {
        "id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "overall_score": overall,
        "tier": {"key": tier.key, "label": tier.label, "tone": tier.tone, "blurb": tier.blurb},
        "headline": data["headline"],
        "thesis": data["thesis"],
        "categories": categories,
        "fix_this_first": sorted(data["fix_this_first"], key=lambda f: f["rank"]),
        "strategic_notes": data["strategic_notes"],
        "green_flags": data["green_flags"],
        "red_flags": data["red_flags"],
        "research_notes": data["research_notes"],
        "answers": answers,
    }
