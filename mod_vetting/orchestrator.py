"""Orchestrator. implementation-spec.md section 5.

created -> fetching -> triaging -> adjudicating -> grounding -> awaiting_human

Stops at awaiting_human. synthesising/steelmanning/reconciling have no
prompt spec in implementation-spec.md (it explicitly supersedes only
stages 1-2 of a sister design doc) -- this build does not fabricate them.
Section 8's own rule is "everything else renders to awaiting_human
regardless," which is exactly what stopping here does; it isn't a
shortcut around the design, it's the design's own fallback path with
stages 3-5 simply not there yet.
"""

from __future__ import annotations

import hashlib
import time

from . import prompts
from .fetch import fetch_applicant_history
from .grounding import CorpusItem, ground
from .report import assemble_report
from .stage1_triage import chunk, flag_rate, triage_batch
from .stage2_adjudicate import HARD_FAIL_PENDING_REVIEW_THRESHOLD, adjudicate_flagged
from .storage import Storage

RUBRIC_VERSION = "v1"


def compute_contract_hash() -> str:
    """Hash over the prompt templates -- an edit to either changes scores
    as surely as a model swap does (spec intro)."""
    h = hashlib.sha256()
    h.update(prompts.TRIAGE_SYSTEM_PROMPT.encode())
    h.update(prompts.ADJUDICATE_SYSTEM_PROMPT.encode())
    h.update(RUBRIC_VERSION.encode())
    return h.hexdigest()[:16]


def run_job(
    storage: Storage,
    applicant_username: str,
    rules: str,
    register_notes: str,
    applicant_meta: dict,
    comment_cap: int = 1000,
    post_cap: int = 100,
    api_key: str | None = None,
) -> dict:
    """Runs one applicant end to end. Not resumable mid-call in this v1 --
    checkpoints are written after each stage so a *new* run of the same
    job_id could in principle pick up from storage, but this function
    itself always re-executes from fetching onward. Wiring true resume
    (reading storage first, skipping completed stages) is separable and
    left as a follow-up; the storage layer already supports it (see
    storage.py idempotency tests)."""
    contract_hash = compute_contract_hash()
    job = storage.create_job(applicant_username, contract_hash)
    contract = {
        "rubric_version": RUBRIC_VERSION,
        "prompt_template_hash": contract_hash,
        "models": {"triage": "claude-haiku-4-5-20251001", "adjudicate": "claude-sonnet-5"},
    }

    # --- fetching ---
    storage.set_state(job.job_id, "fetching")
    items = fetch_applicant_history(applicant_username, comment_cap=comment_cap, post_cap=post_cap)
    comments = [i for i in items if i.type == "comment"]
    storage.checkpoint_stage(job.job_id, "fetching", {"comment_count": len(comments), "item_count": len(items)})

    # --- triaging ---
    storage.set_state(job.job_id, "triaging")
    triage_results = []
    for i, batch in enumerate(chunk(comments)):
        triage_results.extend(triage_batch(batch, batch_id=f"{job.job_id}-{i}", api_key=api_key))
    rate = flag_rate(triage_results, len(comments))
    storage.checkpoint_stage(
        job.job_id, "triaging",
        {"flag_rate": rate, "flagged_count": sum(1 for r in triage_results if r.flags)},
    )

    flagged_ids = {r.id for r in triage_results if r.flags}
    flagged_comments = [c for c in comments if c.id in flagged_ids]

    if len(flagged_comments) > HARD_FAIL_PENDING_REVIEW_THRESHOLD:
        storage.set_state(job.job_id, "awaiting_human")
        return {
            "job_id": job.job_id,
            "state": "awaiting_human",
            "blocked_reason": f"{len(flagged_comments)} flagged items exceeds "
            f"{HARD_FAIL_PENDING_REVIEW_THRESHOLD} -- human review of triage output required "
            "before adjudication proceeds (spec section 5 cost control).",
        }

    # --- adjudicating ---
    storage.set_state(job.job_id, "adjudicating")
    triage_flags_by_id = {r.id: set(r.flags) for r in triage_results if r.flags}
    outcomes = adjudicate_flagged(
        flagged_comments, applicant_username, rules, register_notes,
        api_key=api_key, triage_flags_by_id=triage_flags_by_id,
    )

    unparseable_count = 0
    excluded_count = 0  # true exclusions only -- unparseable/error. context_unavailable is
    # NOT an exclusion (the finding still proceeds, just without j3/j4/d3
    # answered); conflating the two under one "excluded" bucket would make
    # a routine missing-thread-context case look like a pipeline failure.
    findings_input = []
    for comment, outcome in zip(flagged_comments, outcomes):
        if outcome.unparseable:
            unparseable_count += 1
            excluded_count += 1
            storage.record_excluded(job.job_id, "adjudicating", comment.id, f"unparseable: {outcome.error}")
            continue
        if outcome.error:
            excluded_count += 1
            storage.record_excluded(job.job_id, "adjudicating", comment.id, f"error: {outcome.error}")
            continue
        if outcome.finding is not None:
            findings_input.append((comment, outcome))
    storage.checkpoint_stage(
        job.job_id, "adjudicating",
        {"adjudicated_count": len(findings_input), "unparseable_count": unparseable_count},
    )

    # --- grounding ---
    storage.set_state(job.job_id, "grounding")
    corpus = {c.id: CorpusItem(id=c.id, body=c.body, permalink=c.permalink) for c, _ in findings_input}
    corpus_meta = {
        c.id: {
            "permalink": c.permalink, "created_utc": c.created_utc, "subreddit": c.subreddit,
            "context_note": o.context_note, "register_note": o.register_note,
            "body": c.body, "parent_body": o.parent_body, "replies": o.replies,
            "submission_title": c.submission_title,
        }
        for c, o in findings_input
    }
    all_findings = [o.finding for _, o in findings_input]
    total_quotes_checked = sum(1 for f in all_findings for q in f.quotes.values() if q is not None)
    kept, dropped = ground(all_findings, corpus)
    storage.checkpoint_stage(
        job.job_id, "grounding",
        {"kept": len(kept), "dropped": len(dropped), "total_quotes_checked": total_quotes_checked},
    )

    window_start = min((c.created_utc for c in comments), default=None)
    window_end = max((c.created_utc for c in comments), default=None)
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)) if t is not None else None  # noqa: E731

    # --- report (stops at awaiting_human; see module docstring) ---
    report = assemble_report(
        job_id=job.job_id,
        applicant=applicant_meta,
        contract=contract,
        kept_findings=kept,
        corpus_meta=corpus_meta,
        findings_dropped_ungrounded=len(dropped),
        comments_fetched=len(comments),
        comments_flagged=len(flagged_comments),
        unparseable_count=unparseable_count,
        triage_flag_rate=rate,
        any_stage_excluded=excluded_count > 0,
        window_start=iso(window_start),
        window_end=iso(window_end),
        activity_items=items,
    )
    storage.set_state(job.job_id, "awaiting_human")
    storage.checkpoint_stage(job.job_id, "awaiting_human", report)
    return report
