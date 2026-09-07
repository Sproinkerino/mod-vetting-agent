"""Regression tests for the tree-flattening bug found while smoke-testing
fetch.py against the real Arctic Shift API: /api/comments/tree returns
Reddit's native nested listing shape (replies nested inside each node,
not flat siblings), and the first version of _flatten_tree/_fetch_replies
only saw top-level comments as a result -- a reply buried under a
top-level comment silently looked like "no replies," not an error.
"""

from mod_vetting.fetch import _flatten_tree


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
