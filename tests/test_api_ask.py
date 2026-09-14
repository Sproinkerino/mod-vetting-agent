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
        if schema["required"] == ["matches"]:
            return {"matches": [{"id": item["id"], "strength": 3} for item in _activity()]}
        if schema["required"] == ["source_ids"]:
            captured["judge_schema"] = schema
            return {"source_ids": ["abc120", "abc121", "abc122", "abc123"]}
        if system_prompt == api_module.COMEBACK_SYSTEM_PROMPT:
            captured.update(system_prompt=system_prompt, schema=schema, kwargs=kwargs)
        return {
            "opener": "Item abc122 contradicts you.",
            "answer": "Item abc120 supports the statement; abc121 adds context.",
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
    assert captured["schema"]["required"] == ["opener", "answer"]
    assert captured["schema"]["properties"]["opener"]["maxLength"] == 100
    assert captured["schema"]["properties"]["answer"]["maxLength"] == 320
    assert captured["judge_schema"]["properties"]["source_ids"]["maxItems"] == 3
    assert captured["kwargs"]["max_tokens"] == 140


def test_ask_returns_no_uncorroborated_sources_when_model_provider_fails(monkeypatch):
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
    assert payload["sources"] == []


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

def test_empty_activity_uses_the_same_reply_shape():
    response = TestClient(api_module.app).post(
        "/jobs/missing/ask",
        json={"question": "unrelatedzz", "username": "example", "activity": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "opener": "No matching receipt was found.",
        "answer": "The fetched activity does not support that claim.",
        "sources": [],
        "provider_fallback": False,
    }


def test_ask_sends_complete_archive_to_llm_without_keyword_filter(monkeypatch):
    captured = {}
    activity = _activity(20)
    activity[-1]["body"] = "Looking at the colour, you should not be surprised."

    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        if schema["required"] == ["matches"]:
            captured["review_system_prompt"] = system_prompt
            captured["review_user_prompt"] = user_prompt
            return {"matches": [{"id": activity[-1]["id"], "strength": 3}]}
        return {
            "opener": "That prejudice was hiding in plain sight.",
            "answer": "Calling attention to skin colour says exactly what you meant.",
            "source_ids": [activity[-1]["id"]],
        }

    monkeypatch.setattr(api_module, "call_model", reply_model)
    response = TestClient(api_module.app).post(
        "/jobs/semantic-ask/ask",
        json={
            "question": "Find racist remarks or anything about color",
            "username": "example",
            "activity": activity,
        },
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["id"] == activity[-1]["id"]
    assert all(item["id"] in captured["review_user_prompt"] for item in activity)
    assert "Interpret meaning, not exact word overlap" in captured["review_system_prompt"]


def test_ask_does_not_attach_arbitrary_sources_when_llm_finds_none(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "call_model",
        lambda *args, **kwargs: {
            "opener": "That claim has no receipt here.",
            "answer": "The supplied material does not support that accusation.",
            "source_ids": [],
        },
    )
    response = TestClient(api_module.app).post(
        "/jobs/no-semantic-match/ask",
        json={"question": "racist remarks", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_ask_uses_posts_as_first_class_sources(monkeypatch):
    captured = {}

    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        captured["user_prompt"] = user_prompt
        if schema["required"] == ["matches"]:
            return {"matches": [{"id": "post123", "strength": 3}]}
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
    assert '"type":"post"' in captured["user_prompt"]
    assert "Exact displayed receipts" in captured["user_prompt"]


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
    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        if schema["required"] == ["matches"]:
            return {"matches": [{"id": "abc120", "strength": 3}]}
        return {
            "opener": "One receipt is enough.",
            "answer": "The closest statement answers it.",
            "source_ids": ["abc120", "abc121", "abc122"],
        }

    monkeypatch.setattr(api_module, "call_model", reply_model)
    response = TestClient(api_module.app).post(
        "/jobs/default-one/ask",
        json={"question": "work", "username": "example", "activity": _activity()},
    )

    assert response.status_code == 200
    assert len(response.json()["sources"]) == 1


def test_archive_reviewer_inspects_every_bounded_window(monkeypatch):
    activity = _activity(125)
    reviewed_ids = []

    def review_batch(question, items):
        reviewed_ids.extend(item["id"] for item in items)
        return [(items[-1]["id"], 3)]

    monkeypatch.setattr(api_module, "_review_activity_batch", review_batch)
    candidates = api_module._find_relevant_activity("What do they say about work?", activity)

    assert sorted(reviewed_ids) == sorted(item["id"] for item in activity)
    assert [item["id"] for item in candidates] == ["abc1229", "abc1259", "abc1289", "abc12119", "abc12124"]


def test_archive_reviewer_retries_a_failed_window(monkeypatch):
    activity = _activity(61)
    attempts = {}

    def flaky_review(question, items):
        window = items[0]["id"]
        attempts[window] = attempts.get(window, 0) + 1
        if len(items) == 1 and attempts[window] == 1:
            raise RuntimeError("temporary provider failure")
        return [(items[-1]["id"], 3)]

    monkeypatch.setattr(api_module, "_review_activity_batch", flaky_review)
    candidates = api_module._find_relevant_activity("work", activity)

    assert attempts["abc1260"] == 2
    assert {item["id"] for item in candidates} == {"abc1229", "abc1259", "abc1260"}

def test_ask_rejects_source_counts_outside_one_to_three():
    client = TestClient(api_module.app)
    for count in (0, 4):
        response = client.post(
            "/jobs/invalid-source-count/ask",
            json={"question": "work", "username": "example", "activity": _activity(), "source_count": count},
        )
        assert response.status_code == 422
