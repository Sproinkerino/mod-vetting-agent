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



def test_empty_scope_recommends_the_accounts_actual_communities():
    activity = [
        _item("sg1", "Singapore", "One"),
        _item("sg2", "Singapore", "Two"),
        _item("coffee1", "coffee", "Three"),
    ]

    entry = api_module._empty_scope_entry(["AskReddit", "worldnews"], activity)

    assert entry["status"] == "scope_empty"
    assert entry["requested_subreddits"] == ["AskReddit", "worldnews"]
    assert entry["activity_total"] == 3
    assert entry["community_total"] == 2
    assert entry["community_counts"] == [
        {"name": "Singapore", "count": 2},
        {"name": "coffee", "count": 1},
    ]
    assert entry["suggested_subreddits"] == ["Singapore", "coffee"]



def test_background_scope_miss_returns_recovery_without_running_ai(monkeypatch, tmp_path):
    activity = [
        _item("sg1", "Singapore", "One"),
        _item("sg2", "Singapore", "Two"),
        _item("coffee1", "coffee", "Three"),
    ]
    job_id = "scope-recovery-job"
    request = api_module.CreateJobRequest(
        username="example",
        subreddits=["AskReddit"],
        rules="No harassment.",
        register_notes="Read literally.",
    )
    monkeypatch.setattr(api_module, "DB_PATH", tmp_path / "recovery.db")
    monkeypatch.setattr(api_module, "fetch_applicant_history", lambda *args, **kwargs: activity)
    monkeypatch.setattr(api_module, "run_job", lambda **kwargs: (_ for _ in ()).throw(AssertionError("AI should not run")))
    api_module._jobs[job_id] = {"status": "running", "cancel_requested": False}
    try:
        api_module._run_in_background(job_id, request, "unused-cache-key")
        entry = api_module._jobs[job_id]
        assert entry["status"] == "scope_empty"
        assert entry["suggested_subreddits"] == ["Singapore", "coffee"]
        assert entry["community_counts"][0] == {"name": "Singapore", "count": 2}
    finally:
        api_module._jobs.pop(job_id, None)



def test_discovery_mode_ranks_communities_and_skips_ai(monkeypatch, tmp_path):
    activity = [
        _item("sg1", "Singapore", "One"),
        _item("sg2", "Singapore", "Two"),
        _item("coffee1", "coffee", "Three"),
    ]
    job_id = "community-discovery-job"
    request = api_module.CreateJobRequest(
        username="example",
        discover_communities=True,
        rules="No harassment.",
        register_notes="Read literally.",
    )
    monkeypatch.setattr(api_module, "DB_PATH", tmp_path / "discovery.db")
    monkeypatch.setattr(api_module, "fetch_applicant_history", lambda *args, **kwargs: activity)
    monkeypatch.setattr(api_module, "run_job", lambda **kwargs: (_ for _ in ()).throw(AssertionError("AI should not run")))
    api_module._jobs[job_id] = {"status": "running", "cancel_requested": False}
    try:
        api_module._run_in_background(job_id, request, "unused-cache-key")
        entry = api_module._jobs[job_id]
        assert entry["status"] == "communities_ready"
        assert entry["suggested_subreddits"] == ["Singapore", "coffee"]
        assert entry["activity_total"] == 3
    finally:
        api_module._jobs.pop(job_id, None)


def test_bundled_popular_list_contains_one_thousand_searchable_communities():
    response = TestClient(api_module.app).get("/subreddits/popular?limit=1000")

    assert response.status_code == 200
    assert response.json()["source"] == "bundled"
    names = [item["name"] for item in response.json()["items"]]
    assert len(names) == 1000
    assert names[:4] == ["funny", "AskReddit", "worldnews", "gaming"]
    assert "singapore" in names
    assert "masterduel" in names


def test_bundled_autocomplete_works_without_reddit_network(monkeypatch):
    monkeypatch.setattr(api_module, "_fetch_subreddit_options", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network called")))

    response = TestClient(api_module.app).get("/subreddits/suggest?q=master")

    assert response.status_code == 200
    assert response.json()["source"] == "bundled"
    names = {item["name"] for item in response.json()["items"]}
    assert "masterduel" in names


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