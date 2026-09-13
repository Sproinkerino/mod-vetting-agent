"""Structured LLM provider adapters for Anthropic, OpenRouter, and DeepSeek.

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

import json
import os

import httpx

TRIAGE_MODEL = "claude-haiku-4-5-20251001"
ADJUDICATE_MODEL = "claude-sonnet-5"

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
REQUEST_TIMEOUT = 60.0

TOOL_NAME = "emit_result"


def configured_models() -> dict[str, str]:
    """Return the provider/model contract used for cache identity and reports."""
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "triage": os.environ.get("DEEPSEEK_TRIAGE_MODEL", "deepseek-v4-flash"),
            "adjudicate": os.environ.get("DEEPSEEK_ADJUDICATE_MODEL", "deepseek-v4-pro"),
        }
    if provider == "openrouter" or (not provider and not anthropic_key and openrouter_key):
        return {
            "provider": "openrouter",
            "triage": os.environ.get("OPENROUTER_TRIAGE_MODEL", "anthropic/claude-haiku-4.5"),
            "adjudicate": os.environ.get("OPENROUTER_ADJUDICATE_MODEL", "anthropic/claude-sonnet-5"),
        }
    return {"provider": "anthropic", "triage": TRIAGE_MODEL, "adjudicate": ADJUDICATE_MODEL}


class SchemaValidationError(Exception):
    """Model output didn't match the expected shape (raised by the
    stage-specific validators, not this module -- this module guarantees
    only that provider tool arguments decode to an object; semantic checks
    like 'ids must be from
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
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if provider == "deepseek":
        if not deepseek_key:
            raise RuntimeError("LLM_PROVIDER is deepseek but DEEPSEEK_API_KEY is not set")
        return _call_deepseek(
            system_prompt, user_prompt, model, input_schema,
            max_tokens=max_tokens, api_key=deepseek_key,
        )
    if provider == "openrouter":
        if not openrouter_key:
            raise RuntimeError("LLM_PROVIDER is openrouter but OPENROUTER_API_KEY is not set")
        return _call_openrouter(
            system_prompt, user_prompt, model, input_schema,
            max_tokens=max_tokens, api_key=openrouter_key,
        )

    # Without an explicit provider selection, Anthropic remains the
    # compatibility default whenever it is configured. OpenRouter is the
    # fallback when only its key is present.
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        if openrouter_key:
            return _call_openrouter(
                system_prompt, user_prompt, model, input_schema,
                max_tokens=max_tokens, api_key=openrouter_key,
            )
        raise RuntimeError("Neither ANTHROPIC_API_KEY nor OPENROUTER_API_KEY is set")

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


def _call_openrouter(
    system_prompt: str,
    user_prompt: str,
    model: str,
    input_schema: dict,
    *,
    max_tokens: int,
    api_key: str,
) -> dict:
    """Call Claude through OpenRouter's OpenAI-compatible tool API."""
    default_model = "anthropic/claude-haiku-4.5" if model == TRIAGE_MODEL else "anthropic/claude-sonnet-5"
    model_env = "OPENROUTER_TRIAGE_MODEL" if model == TRIAGE_MODEL else "OPENROUTER_ADJUDICATE_MODEL"
    routed_model = os.environ.get(model_env, default_model)
    resp = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:5173",
            "X-Title": "reddit-pi",
        },
        json={
            "model": routed_model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "tools": [{
                "type": "function",
                "function": {
                    "name": TOOL_NAME,
                    "description": "Return the result in the required shape.",
                    "parameters": input_schema,
                },
            }],
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
    if not calls:
        raise SchemaValidationError(f"no tool call in OpenRouter response: {data.get('choices')!r}")
    arguments = calls[0].get("function", {}).get("arguments")
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except (TypeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError("OpenRouter returned malformed tool arguments") from exc
    if not isinstance(parsed, dict):
        raise SchemaValidationError("OpenRouter tool arguments were not an object")
    return parsed


def _call_deepseek(
    system_prompt: str,
    user_prompt: str,
    model: str,
    input_schema: dict,
    *,
    max_tokens: int,
    api_key: str,
) -> dict:
    """Call DeepSeek's OpenAI-compatible tool API in non-thinking mode."""
    default_model = "deepseek-v4-flash" if model == TRIAGE_MODEL else "deepseek-v4-pro"
    model_env = "DEEPSEEK_TRIAGE_MODEL" if model == TRIAGE_MODEL else "DEEPSEEK_ADJUDICATE_MODEL"
    routed_model = os.environ.get(model_env, default_model)
    resp = httpx.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": routed_model,
            "max_tokens": max_tokens,
            "thinking": {"type": "disabled"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "tools": [{
                "type": "function",
                "function": {
                    "name": TOOL_NAME,
                    "description": "Return the result in the required shape.",
                    "parameters": input_schema,
                },
            }],
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        },
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
    if not calls:
        raise SchemaValidationError(f"no tool call in DeepSeek response: {data.get('choices')!r}")
    arguments = calls[0].get("function", {}).get("arguments")
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    except (TypeError, json.JSONDecodeError) as exc:
        raise SchemaValidationError("DeepSeek returned malformed tool arguments") from exc
    if not isinstance(parsed, dict):
        raise SchemaValidationError("DeepSeek tool arguments were not an object")
    return parsed
