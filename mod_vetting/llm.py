"""Anthropic API wrapper.

Originally used the assistant-message-prefill trick ('{' as the last
message) to force bare JSON, verified working for claude-haiku-4-5 in the
separate mod-review project. claude-sonnet-5 rejected that outright:
"This model does not support assistant message prefill" (an extended-
thinking-family constraint -- the turn structure doesn't allow it).

Switched to forced tool-use instead: define a tool whose input_schema is
the desired output shape, force tool_choice to that tool, and read the
tool_use block's `input` directly -- it arrives pre-parsed as JSON matching
the schema, no brittle string parsing on either model. Verified against
both models before wiring into the stages.
"""

from __future__ import annotations

import os

import httpx

TRIAGE_MODEL = "claude-haiku-4-5-20251001"
ADJUDICATE_MODEL = "claude-sonnet-5"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
REQUEST_TIMEOUT = 60.0

TOOL_NAME = "emit_result"


class SchemaValidationError(Exception):
    """Model output didn't match the expected shape (raised by the
    stage-specific validators, not this module -- this module only
    guarantees the response is well-formed JSON matching the tool's
    input_schema at the API level; semantic checks like 'ids must be from
    this batch' happen in stage1_triage.py / stage2_adjudicate.py).
    Caller retries once with this appended to the user turn per the
    spec's retry policy (section 5); a second failure marks the item
    unparseable rather than retrying forever."""


def call_model(
    system_prompt: str,
    user_prompt: str,
    model: str,
    input_schema: dict,
    max_tokens: int = 4096,
    api_key: str | None = None,
) -> dict:
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    resp = httpx.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": "Return the result in the required shape.",
                    "input_schema": input_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    tool_use = next((b for b in data.get("content", []) if b.get("type") == "tool_use"), None)
    if tool_use is None:
        raise SchemaValidationError(f"no tool_use block in response: {data.get('content')!r}")
    return tool_use["input"]
