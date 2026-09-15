"""Stage 1 -- Triage. implementation-spec.md section 1."""

from __future__ import annotations

import copy
import logging
import random
from dataclasses import dataclass

from .llm import TRIAGE_MODEL, SchemaValidationError, call_model
from .prompts import TRIAGE_SYSTEM_PROMPT, render_triage_user_prompt

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
VALID_FLAGS = {
    "hostility_individual",
    "hostility_group",
    "rule_reasoning",
    "self_description",
    "coordination",
    "doxxing",
    "factual_assertion",
}

# Expected flag rate band -- spec section 1. Below the floor means the
# prompt has drifted conservative and recall is silently degrading.
EXPECTED_FLAG_RATE_FLOOR = 0.02
EXPECTED_FLAG_RATE_BAND = (0.08, 0.20)


TRIAGE_TOOL_SCHEMA = {
    "type": "object",
    "required": ["results"],
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "flags", "confidence"],
                "properties": {
                    "id": {"type": "string"},
                    "flags": {"type": "array", "items": {"type": "string", "enum": sorted(VALID_FLAGS)}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


@dataclass
class TriageResult:
    id: str
    flags: list[str]
    confidence: float


def _schema_for_batch(batch_ids: set[str]) -> dict:
    """Constrain tool output to IDs present in this exact review window."""
    schema = copy.deepcopy(TRIAGE_TOOL_SCHEMA)
    schema["properties"]["results"]["items"]["properties"]["id"]["enum"] = sorted(batch_ids)
    return schema


def _validate_triage_output(parsed, batch_ids: set[str]) -> list[TriageResult]:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("results"), list):
        raise SchemaValidationError(f"expected {{'results': [...]}}, got {parsed!r}")
    results = []
    foreign_ids = set()
    for row in parsed["results"]:
        if not isinstance(row, dict) or "id" not in row:
            raise SchemaValidationError(f"row missing 'id': {row!r}")
        if not isinstance(row["id"], str):
            raise SchemaValidationError(f"row id must be a string: {row['id']!r}")
        if row["id"] not in batch_ids:
            # A foreign ID can never become evidence. Drop it instead of
            # allowing one hallucinated row to abort the account's full scan.
            foreign_ids.add(row["id"])
            continue
        flags = row.get("flags", [])
        bad_flags = set(flags) - VALID_FLAGS
        if bad_flags:
            raise SchemaValidationError(f"unknown flags {bad_flags} on {row['id']}")
        results.append(TriageResult(id=row["id"], flags=flags, confidence=row.get("confidence", 0.0)))
    if foreign_ids:
        logger.warning("Discarded %d out-of-batch triage ID(s)", len(foreign_ids))
    return results


def triage_batch(comments: list, batch_id: str, api_key: str | None = None) -> list[TriageResult]:
    """comments: list of objects with .id and .body (e.g. fetch.RedditItem).
    Randomises order per the spec's position-bias mitigation -- run the
    same batch twice with different shuffles and diff the flag sets to
    get a position-consistency metric (see eval_harness.py)."""
    shuffled = list(comments)
    random.shuffle(shuffled)
    batch_ids = {c.id for c in shuffled}
    batch_schema = _schema_for_batch(batch_ids)

    user_prompt = render_triage_user_prompt(batch_id, shuffled)

    try:
        parsed = call_model(
            TRIAGE_SYSTEM_PROMPT, user_prompt, TRIAGE_MODEL, batch_schema,
            max_tokens=2600, api_key=api_key,
        )
        return _validate_triage_output(parsed, batch_ids)
    except SchemaValidationError as e:
        # One retry with the validator error appended to the user turn
        # (spec section 5 retry policy). A second failure is the caller's
        # job to mark `unparseable` and exclude -- this function raises,
        # it doesn't swallow.
        retry_prompt = user_prompt + f"\n\nYour previous output failed validation: {e}\nReturn valid JSON only."
        parsed = call_model(
            TRIAGE_SYSTEM_PROMPT, retry_prompt, TRIAGE_MODEL, batch_schema,
            max_tokens=2600, api_key=api_key,
        )
        return _validate_triage_output(parsed, batch_ids)


def chunk(items: list, size: int = BATCH_SIZE):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def flag_rate(all_results: list[TriageResult], total_comments: int) -> float:
    if total_comments == 0:
        return 0.0
    flagged = sum(1 for r in all_results if r.flags)
    return flagged / total_comments
