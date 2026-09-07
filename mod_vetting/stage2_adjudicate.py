"""Stage 2 -- Adjudicate. implementation-spec.md section 2.

One call per flagged comment, concurrency cap 20 (spec section 5: cost
control, not politeness -- a permissive stage produces N workers where a
handful would do).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .fetch import ThreadContextUnavailable, fetch_thread_context
from .grounding import Finding
from .llm import ADJUDICATE_MODEL, SchemaValidationError, call_model
from .prompts import ADJUDICATE_SYSTEM_PROMPT, render_adjudicate_user_prompt

CONCURRENCY_CAP = 20
HARD_FAIL_PENDING_REVIEW_THRESHOLD = 400
REPLY_CONTEXT_FLAGS = {"rule_reasoning", "factual_assertion", "doxxing"}

ANSWER_KEYS = {
    "c1", "c2", "c3", "c4", "c5",
    "b1", "b2", "b3", "b4",
    "j1", "j2", "j3", "j4",
    "co1", "co2", "co3", "co4",
    "d1", "d2", "d3",
    "s1",
}
QUOTE_CATEGORIES = {"conduct", "bias", "judgment", "coordination", "doxxing", "self_description"}

_BOOL_OR_NULL = {"type": ["boolean", "null"]}
_STR_OR_NULL = {"type": ["string", "null"]}

ADJUDICATE_TOOL_SCHEMA = {
    "type": "object",
    "required": ["answers", "quotes"],
    "properties": {
        "answers": {
            "type": "object",
            "properties": {k: _BOOL_OR_NULL for k in ANSWER_KEYS},
        },
        "quotes": {
            "type": "object",
            "properties": {k: _STR_OR_NULL for k in QUOTE_CATEGORIES},
        },
        "context_note": _STR_OR_NULL,
        "register_note": _STR_OR_NULL,
    },
}


@dataclass
class AdjudicationOutcome:
    finding: Finding | None
    context_note: str | None = None
    register_note: str | None = None
    context_unavailable_reason: str | None = None
    unparseable: bool = False
    error: str | None = None
    # Carried through to the report so the frontend can render the quote
    # highlighted inside the full body (FR-C2-C4) and replies for judgment
    # findings (FR-C7) -- an offset into a body the frontend never
    # receives is unusable, so these have to travel with the finding.
    parent_body: str | None = None
    replies: list = field(default_factory=list)


def _validate(parsed) -> dict:
    if not isinstance(parsed, dict):
        raise SchemaValidationError(f"expected a JSON object, got {type(parsed).__name__}")
    if "answers" not in parsed or not isinstance(parsed["answers"], dict):
        raise SchemaValidationError("missing or malformed 'answers'")
    if "quotes" not in parsed or not isinstance(parsed["quotes"], dict):
        raise SchemaValidationError("missing or malformed 'quotes'")
    bad_answer_keys = set(parsed["answers"]) - ANSWER_KEYS
    if bad_answer_keys:
        raise SchemaValidationError(f"unknown answer keys: {bad_answer_keys}")
    bad_quote_keys = set(parsed["quotes"]) - QUOTE_CATEGORIES
    if bad_quote_keys:
        raise SchemaValidationError(f"unknown quote categories: {bad_quote_keys}")
    return parsed


def adjudicate_one(
    comment,  # fetch.RedditItem, must be a comment with parent_id/link_id set
    applicant_username: str,
    rules: str,
    register_notes: str,
    api_key: str | None = None,
    triage_flags: set[str] | None = None,
) -> AdjudicationOutcome:
    context_unavailable_reason = None
    parent_body, replies = None, []
    include_replies = triage_flags is None or bool(triage_flags & REPLY_CONTEXT_FLAGS)
    try:
        parent_body, replies = fetch_thread_context(
            comment.id, comment.parent_id, comment.link_id, include_replies=include_replies
        )
    except ThreadContextUnavailable as e:
        context_unavailable_reason = str(e)

    # A deliberately-skipped fetch (cost optimisation: this comment's
    # triage flags didn't need replies) must render to the model exactly
    # like a genuine fetch failure -- "not fetched", never "fetched and
    # empty". Collapsing the two would let the model read absence-by-
    # design as evidence that no correction happened, which is precisely
    # the confusion fetch.py's own docstring says must never occur.
    replies_skipped = include_replies is False and not context_unavailable_reason
    user_prompt = render_adjudicate_user_prompt(
        rules=rules,
        register_notes=register_notes,
        parent_body=parent_body,
        body=comment.body,
        replies=replies,
        commenter_author=applicant_username,
        context_unavailable=(context_unavailable_reason is not None) or replies_skipped,
    )

    try:
        parsed = _validate(
            call_model(
                ADJUDICATE_SYSTEM_PROMPT, user_prompt, ADJUDICATE_MODEL, ADJUDICATE_TOOL_SCHEMA,
                max_tokens=1400, api_key=api_key,
            )
        )
    except SchemaValidationError as e:
        retry_prompt = user_prompt + f"\n\nYour previous output failed validation: {e}\nReturn valid JSON only."
        try:
            parsed = _validate(
                call_model(
                    ADJUDICATE_SYSTEM_PROMPT, retry_prompt, ADJUDICATE_MODEL, ADJUDICATE_TOOL_SCHEMA,
                    max_tokens=1400, api_key=api_key
                )
            )
        except SchemaValidationError as e2:
            return AdjudicationOutcome(finding=None, unparseable=True, error=str(e2))
    except Exception as e:  # noqa: BLE001 -- network/HTTP errors surface to caller as excluded+counted
        return AdjudicationOutcome(finding=None, error=str(e))

    finding = Finding(
        id=comment.id,
        model_id=ADJUDICATE_MODEL,
        quotes={cat: parsed["quotes"].get(cat) for cat in QUOTE_CATEGORIES},
        answers=parsed["answers"],
    )
    return AdjudicationOutcome(
        finding=finding,
        context_note=parsed.get("context_note"),
        register_note=parsed.get("register_note"),
        context_unavailable_reason=context_unavailable_reason,
        parent_body=parent_body,
        replies=replies,
    )


def adjudicate_flagged(
    flagged_comments: list,
    applicant_username: str,
    rules: str,
    register_notes: str,
    api_key: str | None = None,
    triage_flags_by_id: dict[str, set[str]] | None = None,
) -> list[AdjudicationOutcome]:
    if len(flagged_comments) > HARD_FAIL_PENDING_REVIEW_THRESHOLD:
        raise RuntimeError(
            f"{len(flagged_comments)} flagged items exceeds {HARD_FAIL_PENDING_REVIEW_THRESHOLD} -- "
            "hard-fail the job pending human review of the triage output (spec section 5)"
        )

    outcomes: list[AdjudicationOutcome | None] = [None] * len(flagged_comments)
    with ThreadPoolExecutor(max_workers=CONCURRENCY_CAP) as pool:
        futures = {
            pool.submit(
                adjudicate_one, c, applicant_username, rules, register_notes, api_key,
                (triage_flags_by_id or {}).get(c.id),
            ): i
            for i, c in enumerate(flagged_comments)
        }
        for fut in as_completed(futures):
            outcomes[futures[fut]] = fut.result()
    return outcomes  # type: ignore[return-value]
