"""Report assembly + validation. implementation-spec.md section 4 + 8.

Turns grounded findings into the report shape, computes top-level scores
and hard_fails from them, and applies the human-in-the-loop gate.

Stage 3 (synthesise, unimplemented -- see README) is where the spec says
"stage 3 adjusts for pattern" (scoring.py conduct_level comment). Without
it, this report's top-level category scores are a v1 approximation:
level = the worst single finding in that category, finding_ids = every
finding in that category. This is documented, not hidden -- a real
pattern-aware synthesis stage should replace this function, not silently
coexist with it.

hard_fails mapping is this build's own policy choice -- the spec defines
the four codes but not the exact level thresholds that trigger each one.
See HARD_FAIL_RULES below; change these deliberately, they're a judgment
call standing in for a real policy decision.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import jsonschema

from .grounding import Finding
from .scoring import score_all

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "report.schema.json"
SCHEMA = json.loads(_SCHEMA_PATH.read_text())

CATEGORY_ANCHORS = {
    0: "cleared",
    1: "isolated / responsive, not initiated",
    2: "confirmed, not aimed at an individual",
    3: "confirmed, aimed at a specific person",
    4: "confirmed and maintained after correction",
}


def build_findings(kept: list[Finding], corpus_meta: dict) -> list[dict]:
    """kept: grounding.ground()'s `kept` list. corpus_meta: {item_id: {permalink, created_utc, subreddit}}.
    One Finding (one comment) can expand into multiple report findings --
    one per category that actually grounded a quote."""
    from .scoring import CATEGORY_LEVEL_FNS, doxxing_triggered

    out = []
    for f in kept:
        meta = corpus_meta.get(f.id, {})
        scores = score_all(f.answers)
        for category, grounded in f.grounded_quotes.items():
            if category == "self_description":
                if not f.answers.get("s1"):
                    continue
                level = None
            elif category == "doxxing":
                if not doxxing_triggered(f.answers):
                    continue
                level = None
            else:
                level = scores.get(category)
                if level is None:
                    continue  # quote grounded but the booleans didn't clear -- not a finding
            out.append(
                {
                    "id": f.id,
                    "permalink": meta.get("permalink", f.permalink or ""),
                    "created_utc": meta.get("created_utc", 0),
                    "subreddit": meta.get("subreddit", ""),
                    "quote": grounded["quote"],
                    "quote_offset": grounded["offset"],
                    "category": category,
                    "level": level,
                    "answers": f.answers,
                    "context_note": meta.get("context_note"),
                    "register_note": meta.get("register_note"),
                    # Frontend needs the full body to render the quote
                    # highlighted at quote_offset (FR-C2-C4), and
                    # parent_body/replies for context (FR-C2, FR-C7).
                    "body": meta.get("body", ""),
                    "parent_body": meta.get("parent_body"),
                    "replies": meta.get("replies", []),
                }
            )
    return out


def compute_scores(findings: list[dict]) -> dict:
    scores = {}
    for category in ("conduct", "bias", "judgment", "coordination"):
        cat_findings = [f for f in findings if f["category"] == category]
        if not cat_findings:
            scores[category] = {"level": 0, "anchor": CATEGORY_ANCHORS[0], "finding_ids": []}
            continue
        level = max(f["level"] for f in cat_findings)
        scores[category] = {
            "level": level,
            "anchor": CATEGORY_ANCHORS.get(level, str(level)),
            "finding_ids": [f["id"] for f in cat_findings],
        }
    return scores


# v1 policy: which finding levels trigger which hard_fail code. Not
# specified in the spec beyond the four code names -- see module docstring.
HARD_FAIL_RULES = {
    "hate_speech": lambda findings: [f["id"] for f in findings if f["category"] == "bias" and f["level"] == 3],
    "targeted_harassment": lambda findings: [
        f["id"] for f in findings if f["category"] == "conduct" and f["level"] == 3
    ],
    "doxxing": lambda findings: [f["id"] for f in findings if f["category"] == "doxxing"],
    "vote_manipulation": lambda findings: [
        f["id"] for f in findings if f["category"] == "coordination" and f["level"] in (2, 3)
    ],
}


def compute_hard_fails(findings: list[dict]) -> list[dict]:
    result = []
    for code, rule in HARD_FAIL_RULES.items():
        finding_ids = rule(findings)
        result.append({"code": code, "triggered": bool(finding_ids), "finding_ids": finding_ids})
    return result


HUMAN_GATE_THRESHOLDS = {
    "bias_level": 3,
    "coordination_level": 3,
    "findings_dropped_ungrounded": 3,
    "flagged_item_count": 400,
}


def check_human_gate(report: dict, flagged_item_count: int, any_unparseable: bool) -> tuple[bool, list[str]]:
    """Section 8: automatic rendering stops and requires a named human
    before the report can circulate when any condition holds. Returns
    (blocked, reasons). Everything renders to awaiting_human regardless --
    this only decides whether it ALSO carries a block reason."""
    reasons = []
    if any(hf["triggered"] for hf in report["hard_fails"]):
        triggered = [hf["code"] for hf in report["hard_fails"] if hf["triggered"]]
        reasons.append(f"hard fail triggered: {', '.join(triggered)}")
    if report["scores"].get("bias", {}).get("level", 0) >= HUMAN_GATE_THRESHOLDS["bias_level"]:
        reasons.append(f"bias.level >= {HUMAN_GATE_THRESHOLDS['bias_level']}")
    if report["scores"].get("coordination", {}).get("level", 0) >= HUMAN_GATE_THRESHOLDS["coordination_level"]:
        reasons.append(f"coordination.level >= {HUMAN_GATE_THRESHOLDS['coordination_level']}")
    dropped = report["provenance"].get("findings_dropped_ungrounded", 0)
    if dropped > HUMAN_GATE_THRESHOLDS["findings_dropped_ungrounded"]:
        reasons.append(f"findings_dropped_ungrounded ({dropped}) > {HUMAN_GATE_THRESHOLDS['findings_dropped_ungrounded']}")
    if any_unparseable:
        reasons.append("one or more items unparseable")
    if flagged_item_count > HUMAN_GATE_THRESHOLDS["flagged_item_count"]:
        reasons.append(f"flagged-item count ({flagged_item_count}) exceeds {HUMAN_GATE_THRESHOLDS['flagged_item_count']}")
    return bool(reasons), reasons


def validate_report(report: dict):
    """Raises jsonschema.ValidationError, or AssertionError for the
    level>0-requires-finding_ids rule the spec calls out as enforced in
    code, not schema (section 4)."""
    jsonschema.validate(report, SCHEMA)
    for category, score in report.get("scores", {}).items():
        if score["level"] > 0 and not score["finding_ids"]:
            raise AssertionError(f"scores.{category}.level={score['level']} but finding_ids is empty -- not allowed")


def assemble_report(
    job_id: str,
    applicant: dict,
    contract: dict,
    kept_findings: list[Finding],
    corpus_meta: dict,
    findings_dropped_ungrounded: int,
    comments_fetched: int,
    comments_flagged: int,
    unparseable_count: int,
    triage_flag_rate: float,
    any_stage_excluded: bool,
    window_start: str | None = None,
    window_end: str | None = None,
    purge_after_days: int = 90,
) -> dict:
    findings = build_findings(kept_findings, corpus_meta)
    scores = compute_scores(findings)
    hard_fails = compute_hard_fails(findings)

    report = {
        "job_id": job_id,
        "state": "awaiting_human",
        "applicant": applicant,
        "contract": contract,
        "scores": scores,
        "hard_fails": hard_fails,
        "findings": findings,
        "recommendation": {
            "text": "Not generated -- stages 3-5 (synthesise/steelman/reconcile) are not "
            "implemented in this build. This report contains evidence and computed "
            "scores only; see findings and scores for a human to read directly.",
            "dissent": None,
        },
        "provenance": {
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "window_start": window_start,
            "window_end": window_end,
            "comments_fetched": comments_fetched,
            "comments_flagged": comments_flagged,
            "findings_upheld": len(findings),
            "findings_dropped_ungrounded": findings_dropped_ungrounded,
            "unparseable_count": unparseable_count,
            "triage_flag_rate": triage_flag_rate,
            "any_stage_excluded": any_stage_excluded,
            "purge_after": time.strftime("%Y-%m-%d", time.gmtime(time.time() + purge_after_days * 86400)),
        },
    }

    blocked, reasons = check_human_gate(report, comments_flagged, unparseable_count > 0)
    report["_human_gate"] = {"blocked": blocked, "reasons": reasons}  # not part of the pinned schema; renderer reads this

    validate_report({k: v for k, v in report.items() if k != "_human_gate"})
    return report
