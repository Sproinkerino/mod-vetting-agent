import api as api_module
from fastapi.testclient import TestClient


def _activity(count=4):
    return [
        {
            "id": f"abc12{i}",
            "type": "comment",
            "body": f"I work in data and this is public statement {i}.",
            "subreddit": "singapore",
            "created_utc": 1_700_000_000 + i,
            "permalink": f"https://reddit.com/r/singapore/comments/post/title/abc12{i}/",
            "submission_title": "Work discussion",
        }
        for i in range(count)
    ]


def test_ask_survives_missing_in_memory_job_and_humanizes_ids(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "call_model",
        lambda *args, **kwargs: {
            "answer": "Item abc120 supports the statement; abc121 adds context.",
            "source_ids": ["abc120", "abc121", "abc122", "abc123"],
        },
    )
    response = TestClient(api_module.app).post(
        "/jobs/job-lost-during-deploy/ask",
        json={"question": "What do they say about their work?", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "source 1 supports the statement; source 2 adds context."
    assert len(payload["sources"]) == 3
    assert payload["provider_fallback"] is False


def test_ask_returns_evidence_when_model_provider_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(api_module, "call_model", fail)
    response = TestClient(api_module.app).post(
        "/jobs/missing/ask",
        json={"question": "work", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_fallback"] is True
    assert len(payload["sources"]) == 3

def test_comment_url_metadata_keeps_required_applicant_fields():
    request = api_module.CreateJobRequest(
        username="example",
        url="https://reddit.com/r/test/comments/post/title/comment/",
        rules="No harassment.",
        register_notes="Read literally.",
        applicant_meta={"target_comment": {"id": "comment", "body": "example"}},
    )
    meta = api_module._build_applicant_meta(request)

    assert meta["username"] == "example"
    assert meta["account_age_days"] == 0
    assert meta["comments_in_sub"] == 0
    assert meta["target_comment"]["id"] == "comment"
