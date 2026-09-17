from mod_vetting.toxic_receipts import verified_toxic_receipts


def _comment(item_id="c1", body="You are an awful little troll"):
    return {
        "id": item_id, "type": "comment", "body": body,
        "permalink": f"https://reddit.com/r/test/comments/post/title/{item_id}/",
        "subreddit": "test", "created_utc": 1,
    }


def test_verifier_keeps_exact_grounded_quote():
    result = verified_toxic_receipts(
        [{"id": "c1", "quote": "awful little troll", "severity": 4}],
        [_comment()],
    )
    assert result[0]["quote"] == "awful little troll"


def test_verifier_rejects_paraphrase_foreign_id_and_unsafe_url():
    unsafe = _comment("c2")
    unsafe["permalink"] = "https://example.com/steal"
    result = verified_toxic_receipts([
        {"id": "c1", "quote": "paraphrased insult", "severity": 5},
        {"id": "foreign", "quote": "awful little troll", "severity": 5},
        {"id": "c2", "quote": "awful little troll", "severity": 5},
    ], [_comment(), unsafe])
    assert result == []


def test_verifier_caps_at_ten_and_orders_severity():
    candidates = [_comment(f"c{i}", f"targeted attack number {i}") for i in range(12)]
    rows = [{"id": f"c{i}", "quote": f"targeted attack number {i}", "severity": 3 + (i % 3)}
            for i in range(12)]
    result = verified_toxic_receipts(rows, candidates)
    assert len(result) == 10
    assert [item["severity"] for item in result] == sorted(
        [item["severity"] for item in result], reverse=True)


def test_compile_endpoint_returns_only_verified_comments(monkeypatch):
    import api as api_module
    from fastapi.testclient import TestClient

    activity = [_comment("c1", "You are an awful little troll")]
    monkeypatch.setattr(api_module, "_find_relevant_activity",
                        lambda question, items: [{**items[0], "_review_strength": 3}])
    monkeypatch.setattr(api_module, "call_model",
                        lambda *args, **kwargs: {"receipts": [
                            {"id": "c1", "quote": "awful little troll", "severity": 4}
                        ]})
    response = TestClient(api_module.app).post("/jobs/missing/compile-toxic", json={
        "username": "example", "activity": activity, "subreddits": [],
    })
    assert response.status_code == 200
    assert response.json()["sources"][0]["quote"] == "awful little troll"


def test_push_subscription_rejects_unknown_hosts():
    import api as api_module

    assert not api_module._valid_push_subscription({
        "endpoint": "https://example.com/push",
        "keys": {"p256dh": "A" * 44, "auth": "A" * 16},
    })
