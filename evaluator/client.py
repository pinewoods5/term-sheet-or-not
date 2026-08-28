"""The Claude call.

One streamed request per evaluation. Three things are happening in it that are
worth knowing about:

1. `output_config.format` pins the response to the JSON schema, so the final
   text block is guaranteed-valid JSON and the frontend never parses prose.
2. `web_search` is a server-side tool -- it runs on Anthropic's infrastructure
   inside the same turn, so there is no client-side tool loop here. It is what
   lets the evaluator name real competitors instead of hand-waving.
3. The whole thing is streamed. Search pushes a call to 30-60 seconds, which is
   long enough to hit request timeouts and far too long to show a founder a
   frozen button, so we stream and narrate what's happening as it happens.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import anthropic

from .prompts import system_prompt, user_message
from .result import build
from .schema import evaluation_schema

MODEL = "claude-opus-5"
MAX_TOKENS = 32000
MAX_SEARCHES = 6
MAX_PAUSE_RESTARTS = 5

# Narration for the wait. Written in the evaluator's voice because a spinner
# that says "Loading..." would be the one part of the app with no personality.
SEARCH_LINES = [
    "Looking up who else is already doing this…",
    "Checking whether that market number is real…",
    "Reading about your competitors so you don't have to…",
    "Pulling the receipts…",
]


class MissingKey(RuntimeError):
    pass


def _client() -> anthropic.Anthropic:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise MissingKey(
            "ANTHROPIC_API_KEY is not set. Export it and restart the server."
        )
    return anthropic.Anthropic()


def _request_kwargs(mode: str, answers: dict) -> dict:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        # The system prompt is identical for every evaluation in a mode, so it
        # is worth a cache breakpoint -- it's the largest stable prefix here.
        "system": [
            {
                "type": "text",
                "text": system_prompt(mode),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": "high",
            "format": {"type": "json_schema", "schema": evaluation_schema(mode)},
        },
        "tools": [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": MAX_SEARCHES}
        ],
        # A prompt this full of deliberately aggressive framing is exactly the
        # shape that can trip a safety classifier. Routing around a refusal
        # beats showing a founder a stack trace.
        "betas": ["server-side-fallback-2026-07-01"],
        "fallbacks": "default",
        "messages": [{"role": "user", "content": user_message(mode, answers)}],
    }


def _final_json(message) -> dict:
    for block in message.content:
        if block.type == "text" and block.text.strip():
            return json.loads(block.text)
    raise ValueError("the model returned no text block to parse")


def evaluate(mode: str, answers: dict) -> Iterator[tuple[str, dict]]:
    """Run one evaluation, yielding (event, payload) as it progresses.

    Events are `status` (narration for the UI), `result` (the finished
    evaluation), and `error`.
    """
    client = _client()
    kwargs = _request_kwargs(mode, answers)
    messages = list(kwargs["messages"])

    yield "status", {"text": "Reading your submission. Not skimming it."}

    searches = 0
    final = None

    for _ in range(MAX_PAUSE_RESTARTS + 1):
        with client.beta.messages.stream(**{**kwargs, "messages": messages}) as stream:
            for event in stream:
                if event.type != "content_block_start":
                    continue
                kind = event.content_block.type
                if kind == "server_tool_use":
                    yield "status", {"text": SEARCH_LINES[searches % len(SEARCH_LINES)]}
                    searches += 1
                elif kind == "text":
                    yield "status", {"text": "Writing it up. This part is fast."}
            final = stream.get_final_message()

        if final.stop_reason != "pause_turn":
            break
        # A long server-tool turn can pause; resume by replaying it back.
        messages = messages + [{"role": "assistant", "content": final.content}]
        yield "status", {"text": "Still digging. Give me a second."}

    if final is None:
        yield "error", {"message": "The evaluation never started. Try again."}
        return

    if final.stop_reason == "refusal":
        yield "error", {
            "message": "The model declined to evaluate this one. Rephrase and try again."
        }
        return

    if final.stop_reason == "pause_turn":
        yield "error", {"message": "The evaluation kept stalling on search. Try again."}
        return

    try:
        payload = build(mode, _final_json(final), answers)
    except (ValueError, json.JSONDecodeError) as exc:
        yield "error", {"message": f"The evaluation came back malformed: {exc}"}
        return

    yield "result", payload
