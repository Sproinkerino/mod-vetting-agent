import pytest

from mod_vetting.grounding import Finding
from mod_vetting.report import (
    assemble_report,
    build_findings,
    check_human_gate,
    compute_hard_fails,
    compute_scores,
    validate_report,
)


def _conduct_finding(id_, level_answers, quote="you idiot"):
    f = Finding(id=id_, model_id="m", quotes={"conduct": quote}, answers=level_answers)
    f.grounded_quotes["conduct"] = {"quote": quote, "offset": 0}
    return f


def test_build_findings_skips_ungrounded_category_where_booleans_dont_clear():
    # quote grounded under "bias" but the booleans don't actually clear
    # bias_level (b3 missing) -- must not become a finding just because a
    # quote happened to be present.
    f = Finding(
        id="c1", model_id="m",
        quotes={"bias": "some group thing"},
        answers={"b1": True, "b2": True, "b3": None, "b4": None},
    )
    f.grounded_quotes["bias"] = {"quote": "some group thing", "offset": 0}
    findings = build_findings([f], corpus_meta={})
    assert findings == []


def test_build_findings_conduct_level_3():
    answers = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": True}
    f = _conduct_finding("c1", answers)
    findings = build_findings([f], corpus_meta={"c1": {"permalink": "https://x", "created_utc": 1, "subreddit": "s"}})
    assert len(findings) == 1
    assert findings[0]["category"] == "conduct"
    assert findings[0]["level"] == 3


def test_scores_worst_case_across_multiple_findings():
    a1 = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": False}  # level 1
    a2 = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": True}  # level 3
    findings = build_findings(
        [_conduct_finding("c1", a1), _conduct_finding("c2", a2)],
        corpus_meta={"c1": {"permalink": "x", "created_utc": 1, "subreddit": "s"}, "c2": {"permalink": "y", "created_utc": 2, "subreddit": "s"}},
    )
    scores = compute_scores(findings)
    assert scores["conduct"]["level"] == 3
    assert set(scores["conduct"]["finding_ids"]) == {"c1", "c2"}


def test_hard_fail_doxxing_triggers_on_any_grounded_doxxing_finding():
    f = Finding(
        id="d1", model_id="m", quotes={"doxxing": "his name is John Smith"},
        answers={"d1": True, "d2": True, "d3": True},
    )
    f.grounded_quotes["doxxing"] = {"quote": "his name is John Smith", "offset": 0}
    findings = build_findings([f], corpus_meta={"d1": {"permalink": "x", "created_utc": 1, "subreddit": "s"}})
    hard_fails = compute_hard_fails(findings)
    doxxing = next(hf for hf in hard_fails if hf["code"] == "doxxing")
    assert doxxing["triggered"] is True
    assert doxxing["finding_ids"] == ["d1"]

    # and the codes dropped from the spec (undisclosed_coi, application_dishonesty)
    # must not appear at all
    codes = {hf["code"] for hf in hard_fails}
    assert "undisclosed_coi" not in codes
    assert "application_dishonesty" not in codes


def test_human_gate_blocks_on_hard_fail():
    report = {
        "scores": {"bias": {"level": 0}, "coordination": {"level": 0}},
        "hard_fails": [{"code": "doxxing", "triggered": True, "finding_ids": ["d1"]}],
        "provenance": {"findings_dropped_ungrounded": 0},
    }
    blocked, reasons = check_human_gate(report, flagged_item_count=5, any_unparseable=False)
    assert blocked is True
    assert "doxxing" in reasons[0]


def test_human_gate_clear_case_not_blocked():
    report = {
        "scores": {"bias": {"level": 0}, "coordination": {"level": 0}},
        "hard_fails": [{"code": "doxxing", "triggered": False, "finding_ids": []}],
        "provenance": {"findings_dropped_ungrounded": 0},
    }
    blocked, reasons = check_human_gate(report, flagged_item_count=5, any_unparseable=False)
    assert blocked is False
    assert reasons == []


def test_full_assemble_report_validates_against_schema():
    answers = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": True}
    report = assemble_report(
        job_id="11111111-1111-1111-1111-111111111111",
        applicant={
            "username": "testuser", "account_age_days": 100, "sub_tenure_days": 50,
            "comments_in_sub": 20, "subs_modded": 1,
        },
        contract={"rubric_version": "v1", "prompt_template_hash": "abc", "models": {"triage": "haiku", "adjudicate": "sonnet"}},
        kept_findings=[_conduct_finding("c1", answers)],
        corpus_meta={"c1": {"permalink": "https://reddit.com/x", "created_utc": 100, "subreddit": "test"}},
        findings_dropped_ungrounded=0,
        comments_fetched=10,
        comments_flagged=1,
        unparseable_count=0,
        triage_flag_rate=0.1,
        any_stage_excluded=False,
        window_start="2026-01-01T00:00:00Z",
        window_end="2026-02-01T00:00:00Z",
    )
    # assemble_report already calls validate_report internally; call again
    # explicitly here so this test fails loudly (not just via an internal
    # exception) if that contract ever changes.
    validate_report({k: v for k, v in report.items() if k != "_human_gate"})
    assert report["scores"]["conduct"]["level"] == 3
    # conduct.level==3 (initiating, not just responding) is this build's
    # own policy trigger for the targeted_harassment hard fail (see
    # report.py HARD_FAIL_RULES) -- any triggered hard fail blocks per
    # section 8, so this case should be blocked, and for that reason.
    assert report["_human_gate"]["blocked"] is True
    assert "targeted_harassment" in report["_human_gate"]["reasons"][0]
