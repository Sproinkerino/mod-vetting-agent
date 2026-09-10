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
    captured = {}

    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        captured.update(system_prompt=system_prompt, schema=schema, kwargs=kwargs)
        return {
            "opener": "Item abc122 contradicts you.",
            "answer": "Item abc120 supports the statement; abc121 adds context.",
            "source_ids": ["abc120", "abc121", "abc122", "abc123"],
        }

    monkeypatch.setattr(api_module, "call_model", reply_model)
    response = TestClient(api_module.app).post(
        "/jobs/job-lost-during-deploy/ask",
        json={"question": "What do they say about their work?", "username": "example", "activity": _activity(), "source_count": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["opener"] == "source 3 contradicts you."
    assert payload["answer"] == "source 1 supports the statement; source 2 adds context."
    assert len(payload["sources"]) == 3
    assert payload["provider_fallback"] is False
    assert "one-line opener" in captured["system_prompt"]
    assert "4-10 words" in captured["system_prompt"]
    assert "compulsive liar" in captured["system_prompt"]
    assert captured["schema"]["required"] == ["opener", "answer", "source_ids"]
    assert captured["schema"]["properties"]["opener"]["maxLength"] == 100
    assert captured["schema"]["properties"]["answer"]["maxLength"] == 320
    assert captured["schema"]["properties"]["source_ids"]["maxItems"] == 3
    assert captured["kwargs"]["max_tokens"] == 160


def test_ask_returns_evidence_when_model_provider_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(api_module, "call_model", fail)
    response = TestClient(api_module.app).post(
        "/jobs/missing/ask",
        json={"question": "work", "username": "example", "activity": _activity(), "source_count": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_fallback"] is True
    assert payload["opener"] == "No supported comeback was generated."
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

def test_no_matching_activity_uses_the_same_reply_shape():
    response = TestClient(api_module.app).post(
        "/jobs/missing/ask",
        json={"question": "unrelatedzz", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "opener": "No matching receipt was found.",
        "answer": "The fetched activity does not support that claim.",
        "sources": [],
        "provider_fallback": False,
    }


def test_ask_uses_posts_as_first_class_sources(monkeypatch):
    captured = {}

    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        captured["user_prompt"] = user_prompt
        return {"opener": "That post says otherwise.", "answer": "The post is the receipt.", "source_ids": ["post123"]}

    monkeypatch.setattr(api_module, "call_model", reply_model)
    activity = [{
        "id": "post123", "type": "post", "title": "My coffee setup", "body": "I drink coffee every morning.",
        "subreddit": "coffee", "created_utc": 1_700_000_000,
        "permalink": "https://reddit.com/r/coffee/comments/post123/my_coffee_setup/",
    }]
    response = TestClient(api_module.app).post(
        "/jobs/post-source/ask",
        json={"question": "What did they say about coffee?", "username": "example", "activity": activity},
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["type"] == "post"
    assert response.json()["sources"][0]["title"] == "My coffee setup"
    assert "type='post'" in captured["user_prompt"]
    assert "Public posts and comments" in captured["user_prompt"]


def test_post_url_metadata_keeps_required_applicant_fields():
    request = api_module.CreateJobRequest(
        username="example", url="https://reddit.com/r/test/comments/post123/a_post/",
        rules="No harassment.", register_notes="Read literally.",
        applicant_meta={"target_content": {"id": "post123", "type": "post", "title": "A post"}},
    )
    meta = api_module._build_applicant_meta(request)

    assert meta["username"] == "example"
    assert meta["target_content"]["type"] == "post"

def test_ask_defaults_to_one_source(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "call_model",
        lambda *args, **kwargs: {
            "opener": "One receipt is enough.",
            "answer": "The closest statement answers it.",
            "source_ids": ["abc120", "abc121", "abc122"],
        },
    )
    response = TestClient(api_module.app).post(
        "/jobs/default-one/ask",
        json={"question": "work", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    assert len(response.json()["sources"]) == 1


def test_ask_rejects_source_counts_outside_one_to_three():
    client = TestClient(api_module.app)
    for count in (0, 4):
        response = client.post(
            "/jobs/invalid-source-count/ask",
            json={"question": "work", "username": "example", "activity": _activity(), "source_count": count},
        )
        assert response.status_code == 422
