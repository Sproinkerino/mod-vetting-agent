"""Regression tests for the tree-flattening bug found while smoke-testing
fetch.py against the real Arctic Shift API: /api/comments/tree returns
Reddit's native nested listing shape (replies nested inside each node,
not flat siblings), and the first version of _flatten_tree/_fetch_replies
only saw top-level comments as a result -- a reply buried under a
top-level comment silently looked like "no replies," not an error.
"""

import pytest

from mod_vetting.fetch import _flatten_tree, comment_id_from_url, username_from_url


def test_comment_id_from_canonical_reddit_url():
    assert comment_id_from_url("https://www.reddit.com/r/test/comments/abc123/a_title/xyz789/") == "xyz789"


def test_comment_id_rejects_post_only_and_non_reddit_urls():
    with pytest.raises(ValueError, match="specific comment"):
        comment_id_from_url("https://www.reddit.com/r/test/comments/abc123/a_title/")
    with pytest.raises(ValueError, match="reddit.com"):
        comment_id_from_url("https://example.com/r/test/comments/abc/title/xyz")

@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.reddit.com/user/Some_User/", "Some_User"),
        ("https://reddit.com/u/another-user", "another-user"),
    ],
)
def test_username_from_reddit_profile_url(url, expected):
    assert username_from_url(url) == expected


def test_username_from_url_ignores_comment_urls_and_rejects_lookalike_hosts():
    assert username_from_url("https://www.reddit.com/r/test/comments/abc/a_title/xyz/") is None
    with pytest.raises(ValueError, match="reddit.com"):
        username_from_url("https://notreddit.com/user/someone")


def _listing(children):
    return {"kind": "Listing", "data": {"children": children}}


def _comment(id_, parent_id, body="body", replies=None):
    return {
        "kind": "t1",
        "data": {
            "id": id_,
            "parent_id": parent_id,
            "body": body,
            "author": "someone",
            "replies": _listing(replies) if replies else "",
        },
    }


def test_flatten_collects_nested_replies_not_just_top_level():
    # top comment p1 (child of the post) has a reply p2, which itself has
    # a reply p3 -- the real shape observed against the live API.
    tree = [
        _comment(
            "p1",
            "t3_post",
            replies=[
                _comment("p2", "t1_p1", replies=[_comment("p3", "t1_p2")]),
            ],
        ),
        _comment("p4", "t3_post"),  # a second, unrelated top-level comment
    ]

    flat = _flatten_tree(tree)
    ids = {n["id"] for n in flat}

    assert ids == {"p1", "p2", "p3", "p4"}
    p3 = next(n for n in flat if n["id"] == "p3")
    assert p3["parent_id"] == "t1_p2"


def test_flatten_handles_comment_with_no_replies_field():
    tree = [_comment("solo", "t3_post")]  # replies == "" (Reddit's "no replies" sentinel)
    flat = _flatten_tree(tree)
    assert [n["id"] for n in flat] == ["solo"]


def test_flatten_empty_payload():
    assert _flatten_tree([]) == []
