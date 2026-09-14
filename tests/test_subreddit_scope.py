from dataclasses import replace

from fastapi.testclient import TestClient

import api as api_module


def _item(item_id, subreddit, body):
    return {
        "id": item_id,
        "type": "comment",
        "body": body,
        "subreddit": subreddit,
        "created_utc": 1_700_000_000,
        "permalink": "https://reddit.com/r/" + subreddit + "/comments/post/title/" + item_id + "/",
        "submission_title": "Discussion",
    }


def test_subreddit_scope_normalizes_and_deduplicates():
    assert api_module._normalize_subreddits(["r/Singapore", "/r/singapore/", " comics "]) == [
        "Singapore",
        "comics",
    ]


def test_subreddit_scope_changes_report_cache_identity():
    base = api_module.CreateJobRequest(
        username="example",
        rules="No harassment.",
        register_notes="Read literally.",
    )
    scoped = base.model_copy(update={"subreddits": ["singapore"]})

    assert api_module._cache_key(base) != api_module._cache_key(scoped)


def test_filter_by_subreddits_is_case_insensitive():
    activity = [
        _item("sg1", "Singapore", "Singapore item"),
        _item("coffee1", "coffee", "Coffee item"),
    ]

    assert [item["id"] for item in api_module._filter_by_subreddits(activity, ["singapore"])] == ["sg1"]


def test_bundled_popular_list_keeps_curated_order():
    names = [item["name"] for item in api_module._fallback_subreddit_options()]

    assert names[:4] == ["AskReddit", "worldnews", "news", "funny"]


def test_bundled_autocomplete_includes_expected_c_communities(monkeypatch):
    monkeypatch.setattr(api_module, "_fetch_subreddit_options", lambda *args, **kwargs: [])
    with api_module._subreddit_cache_lock:
        api_module._subreddit_cache["suggestions"].clear()

    response = TestClient(api_module.app).get("/subreddits/suggest?q=c")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert "comics" in names
    assert "CompetitiveHS" in names


def test_ask_scope_never_sends_other_communities_to_llm(monkeypatch):
    captured = {}

    def reply_model(system_prompt, user_prompt, model, schema, **kwargs):
        required = schema["required"]
        if required == ["matches"]:
            captured["review_prompt"] = user_prompt
            return {"matches": [{"id": "sg1", "strength": 3}]}
        if required == ["source_ids"]:
            return {"source_ids": ["sg1"]}
        return {
            "opener": "That claim has a receipt.",
            "answer": "This statement is confined to the selected community.",
        }

    monkeypatch.setattr(api_module, "call_model", reply_model)
    activity = [
        _item("sg1", "Singapore", "This is the selected statement."),
        _item("coffee1", "coffee", "This must never reach the model."),
    ]

    response = TestClient(api_module.app).post(
        "/jobs/scoped-ask/ask",
        json={
            "question": "What did they say?",
            "username": "example",
            "activity": activity,
            "source_count": 1,
            "subreddits": ["singapore"],
        },
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["id"] == "sg1"
    assert "selected statement" in captured["review_prompt"]
    assert "must never reach" not in captured["review_prompt"]