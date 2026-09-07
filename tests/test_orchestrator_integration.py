"""End-to-end orchestrator test against the REAL Anthropic API (triage +
adjudicate), but with the fetch layer monkeypatched to synthetic content.

Deliberately not run against a real Reddit user's real history, even for
smoke-testing: this pipeline's whole output shape is adverse claims about
a named person, and generating one -- even as a throwaway test artifact --
about an actual identifiable third party isn't something to do just to
check plumbing. The synthetic applicant here isn't a real person.

Requires ANTHROPIC_API_KEY; skipped otherwise (this is an integration
test that costs real API calls, not part of the offline unit suite).
"""

import os

import pytest

from mod_vetting import fetch as fetch_module
from mod_vetting.fetch import RedditItem
from mod_vetting.orchestrator import run_job
from mod_vetting.storage import Storage

pytestmark = pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY")

SYNTHETIC_APPLICANT = "totally_fake_test_applicant_zzz"

SYNTHETIC_COMMENTS = [
    RedditItem(
        id="s1", type="comment", subreddit="fakehobby", title=None,
        body="Great tips, thanks for sharing your setup!", score=5, created_utc=1000,
        permalink="https://reddit.com/fake/s1", author=SYNTHETIC_APPLICANT,
        parent_id="t3_fakepost1", link_id="t3_fakepost1",
    ),
    RedditItem(
        id="s2", type="comment", subreddit="fakehobby", title=None,
        body="You're a complete moron and everyone here agrees with me.", score=-10, created_utc=2000,
        permalink="https://reddit.com/fake/s2", author=SYNTHETIC_APPLICANT,
        parent_id="t3_fakepost2", link_id="t3_fakepost2",
    ),
    RedditItem(
        id="s3", type="comment", subreddit="fakehobby", title=None,
        body="As a licensed electrician I can confirm that wiring is unsafe.", score=12, created_utc=3000,
        permalink="https://reddit.com/fake/s3", author=SYNTHETIC_APPLICANT,
        parent_id="t3_fakepost3", link_id="t3_fakepost3",
    ),
]


def test_orchestrator_end_to_end_synthetic(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch_module, "fetch_applicant_history", lambda *a, **kw: SYNTHETIC_COMMENTS)
    monkeypatch.setattr(fetch_module, "fetch_thread_context", lambda *a, **kw: (None, []))

    # orchestrator.py imports these names directly, so they must be patched
    # where they're looked up, not just on the fetch module
    import mod_vetting.orchestrator as orch_module
    import mod_vetting.stage2_adjudicate as stage2_module

    monkeypatch.setattr(orch_module, "fetch_applicant_history", lambda *a, **kw: SYNTHETIC_COMMENTS)
    monkeypatch.setattr(stage2_module, "fetch_thread_context", lambda *a, **kw: (None, []))

    storage = Storage(str(tmp_path / "test.sqlite3"))
    report = run_job(
        storage=storage,
        applicant_username=SYNTHETIC_APPLICANT,
        rules="No harassment. No spam. No doxxing.",
        register_notes="Standard hobby subreddit, no unusual in-jokes.",
        applicant_meta={
            "username": SYNTHETIC_APPLICANT, "account_age_days": 400,
            "sub_tenure_days": 200, "comments_in_sub": 3, "subs_modded": 0,
        },
    )

    assert report["job_id"]
    assert report["applicant"]["username"] == SYNTHETIC_APPLICANT
    # s2's hostile comment should have produced at least one conduct finding
    conduct_findings = [f for f in report["findings"] if f["category"] == "conduct"]
    assert len(conduct_findings) >= 1
    assert report["scores"]["conduct"]["level"] > 0

    job = storage.get_job(report["job_id"])
    assert job.state == "awaiting_human"

    # checkpoints for every implemented stage should exist
    for stage in ("fetching", "triaging", "adjudicating", "grounding", "awaiting_human"):
        assert storage.get_stage_output(report["job_id"], stage) is not None
