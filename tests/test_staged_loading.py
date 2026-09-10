from api import _serialize_activity_preview
from mod_vetting.fetch import RedditItem
from mod_vetting.orchestrator import run_job
from mod_vetting.storage import Storage


def item(index: int, item_type: str = "comment", body: str | None = None) -> RedditItem:
    return RedditItem(
        id=str(index),
        type=item_type,
        subreddit="testing",
        title="A post" if item_type == "post" else None,
        body=body if body is not None else f"comment {index}",
        score=index,
        created_utc=index,
        permalink=f"https://reddit.com/{index}",
        author="example_user",
        submission_title="Context",
    )


def test_activity_preview_is_newest_mixed_content_and_bounded():
    items = [*[item(index, body="x" * 400) for index in range(1, 9)], item(9, "post", body="p" * 400)]

    preview = _serialize_activity_preview(items)

    assert [entry["id"] for entry in preview] == ["9", "8", "7", "6", "5", "4"]
    assert preview[0]["type"] == "post"
    assert preview[0]["title"] == "A post"
    assert all(len(entry["body"]) == 300 for entry in preview)


def test_run_job_reuses_prefetched_items(monkeypatch, tmp_path):
    def fail_fetch(*args, **kwargs):
        raise AssertionError("history should not be fetched twice")

    monkeypatch.setattr("mod_vetting.orchestrator.fetch_applicant_history", fail_fetch)
    storage = Storage(str(tmp_path / "prefetch.sqlite3"))
    report = run_job(
        storage=storage,
        applicant_username="example_user",
        rules="No harassment.",
        register_notes="Read literally.",
        applicant_meta={
            "username": "example_user",
            "account_age_days": 0,
            "sub_tenure_days": 0,
            "comments_in_sub": 0,
            "subs_modded": 0,
        },
        prefetched_items=[],
    )

    assert report["activity"] == []
    assert report["provenance"]["comments_fetched"] == 0