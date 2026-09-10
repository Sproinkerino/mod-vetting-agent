"""Stage 0 -- fetch. implementation-spec.md build order step 1.

Everything goes through Arctic Shift (arctic-shift.photon-reddit.com --
note the hyphen; the spec's own photonreddit.com does not resolve, same
issue found and fixed in the separate mod-review tool). No API key, no
auth wall.

Reddit's own public /comments/<id>.json endpoint was tried first for
thread context and turned out to be login-walled as of this build (403,
then a redirect to a login page even with a descriptive User-Agent) --
DO NOT silently swallow that as "no parent/no replies"; an auth failure
and a genuinely top-level comment must be distinguishable, or j3/j4/d3
(which need to tell "no correction happened" apart from "we never saw
what happened after") get quietly and permanently answered wrong.
Arctic Shift has no such gate, so this uses it for context too:

  - /api/comments/ids?ids=<id>            -- fetch a specific comment
  - /api/comments/tree?link_id=<link_id>  -- full comment tree for a post

Only fetched for FLAGGED comments (the output of stage 1), not the whole
history -- this is the expensive-per-item lookup the design deliberately
keeps off the triage hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

import httpx

ARCTIC_SHIFT_POSTS = "https://arctic-shift.photon-reddit.com/api/posts/search"
ARCTIC_SHIFT_COMMENTS = "https://arctic-shift.photon-reddit.com/api/comments/search"
ARCTIC_SHIFT_COMMENT_IDS = "https://arctic-shift.photon-reddit.com/api/comments/ids"
ARCTIC_SHIFT_COMMENT_TREE = "https://arctic-shift.photon-reddit.com/api/comments/tree"
ARCTIC_SHIFT_POST_IDS = "https://arctic-shift.photon-reddit.com/api/posts/ids"
PAGE_LIMIT = 100
REQUEST_TIMEOUT = 15.0

# How many levels of replies to pull under the comment under review. This
# is a window, not the full downstream thread -- see the spec's note on
# subsequent_replies being bounded, and j3/j4/d3 answering null past its edge.
REPLY_DEPTH = 2
REDDIT_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")

class ThreadContextUnavailable(Exception):
    """Raised when thread context genuinely could not be fetched (network,
    upstream error, malformed id) -- as opposed to a comment that legitimately
    has no parent (top-level) or no replies (both are normal, valid results,
    not this exception). Callers must not treat this the same as an empty
    result; see the module docstring."""


@dataclass
class RedditItem:
    id: str
    type: str  # "post" | "comment"
    subreddit: str
    title: str | None
    body: str
    score: int
    created_utc: int
    permalink: str
    author: str
    parent_id: str | None = None  # comments only: "t3_x" (post) or "t1_x" (comment)
    link_id: str | None = None  # comments only: "t3_x", the submission this belongs to
    submission_title: str | None = None


def _normalize(raw: dict, item_type: str) -> RedditItem:
    permalink = raw.get("permalink") or ""
    if permalink and not permalink.startswith("http"):
        permalink = f"https://reddit.com{permalink}"
    return RedditItem(
        id=raw.get("id") or raw.get("name", ""),
        type=item_type,
        subreddit=raw.get("subreddit", ""),
        title=raw.get("title") if item_type == "post" else None,
        body=(raw.get("selftext") or raw.get("title") or "") if item_type == "post" else (raw.get("body") or ""),
        score=raw.get("score", 0),
        created_utc=raw.get("created_utc", 0),
        permalink=permalink,
        author=raw.get("author", ""),
        parent_id=raw.get("parent_id") if item_type == "comment" else None,
        link_id=raw.get("link_id") if item_type == "comment" else None,
        submission_title=raw.get("title") if item_type == "post" else None,
    )


def _reddit_url_parts(url: str) -> list[str]:
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (hostname == "reddit.com" or hostname.endswith(".reddit.com")):
        raise ValueError("Enter a full reddit.com comment URL")
    return [part for part in parsed.path.split("/") if part]


def username_from_url(url: str) -> str | None:
    """Return the username in a Reddit profile URL, or None for another Reddit URL."""
    parts = _reddit_url_parts(url)
    if len(parts) < 2 or parts[0].lower() not in {"u", "user"}:
        return None
    username = parts[1]
    if not REDDIT_USERNAME_RE.fullmatch(username):
        raise ValueError("That Reddit profile URL does not contain a valid username")
    return username


def comment_id_from_url(url: str) -> str:
    """Extract the comment id from a canonical Reddit URL."""
    parts = _reddit_url_parts(url)
    try:
        comments_at = parts.index("comments")
    except ValueError as exc:
        raise ValueError("URL is not a Reddit comments URL") from exc
    tail = parts[comments_at + 2 :]
    if len(tail) < 2:
        raise ValueError("URL points to a post, not a specific comment")
    comment_id = tail[-1]
    if not comment_id.isalnum():
        raise ValueError("Could not read the Reddit comment id")
    return comment_id


def fetch_comment_from_url(url: str) -> RedditItem:
    comment_id = comment_id_from_url(url)
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        resp = client.get(ARCTIC_SHIFT_COMMENT_IDS, params={"ids": comment_id})
        resp.raise_for_status()
        rows = resp.json().get("data", [])
        if not rows:
            raise ValueError("That Reddit comment was not found in the public archive")
        item = _normalize(rows[0], "comment")
        _hydrate_submission_titles(client, [item])
    if not item.author or item.author in {"[deleted]", "AutoModerator"}:
        raise ValueError("That comment does not have an analyzable Reddit author")
    return item


def fetch_applicant_history(username: str, comment_cap: int = 1000, post_cap: int = 100) -> list[RedditItem]:
    """Applicant vetting needs a fuller history than the mod-review tool's
    quick-lookup defaults -- this is a deliberate, consented-adjacent review
    of one specific candidate, not a quick moderator glance. Caps still
    exist to bound cost/latency, just set higher."""
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        posts = _fetch_recent(client, ARCTIC_SHIFT_POSTS, username, post_cap, "post")
        comments = _fetch_recent(client, ARCTIC_SHIFT_COMMENTS, username, comment_cap, "comment")
        _hydrate_submission_titles(client, comments)
    return sorted(posts + comments, key=lambda i: i.created_utc)


def _hydrate_submission_titles(client: httpx.Client, comments: list[RedditItem]) -> None:
    """Attach submission titles in bounded batch lookups for display.

    Purely decorative metadata -- a failure here must never abort the
    whole investigation (which by this point has already paid for real
    LLM calls downstream). One bad batch is skipped, not fatal.
    """
    raw_ids = sorted({c.link_id.removeprefix("t3_") for c in comments if c.link_id})
    titles: dict[str, str] = {}
    for start in range(0, len(raw_ids), 100):
        batch = raw_ids[start : start + 100]
        try:
            resp = client.get(ARCTIC_SHIFT_POST_IDS, params={"ids": ",".join(batch)})
            resp.raise_for_status()
            for post in resp.json().get("data", []):
                if post.get("id") and post.get("title"):
                    titles[post["id"]] = post["title"]
        except (httpx.HTTPError, ValueError):
            continue  # decorative only -- comments simply keep submission_title=None for this batch
    for comment in comments:
        if comment.link_id:
            comment.submission_title = titles.get(comment.link_id.removeprefix("t3_"))


def _fetch_recent(client: httpx.Client, base_url: str, username: str, cap: int, item_type: str) -> list[RedditItem]:
    items: list[RedditItem] = []
    before = None
    while len(items) < cap:
        page_size = min(PAGE_LIMIT, cap - len(items))
        params = {"author": username, "limit": page_size, "sort": "desc"}
        if before:
            params["before"] = before
        resp = client.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        page_items = data if isinstance(data, list) else data.get("data", [])
        if not page_items:
            break
        items.extend(_normalize(raw, item_type) for raw in page_items)
        before = page_items[-1].get("created_utc")
        if not before or len(page_items) < page_size:
            break
    return items[:cap]


def fetch_thread_context(
    comment_id: str,
    parent_id: str | None,
    link_id: str | None,
    *,
    include_replies: bool = True,
) -> tuple[str | None, list[dict]]:
    """Returns (parent_body, replies) for the comment identified by
    comment_id, given the parent_id/link_id already retained on its
    RedditItem from the original author-search fetch.

    parent_body is None when parent_id points at the submission itself
    (a genuinely top-level comment) -- a normal, valid result.

    Raises ThreadContextUnavailable on a real fetch failure. Callers MUST
    catch this separately from a legitimate empty/None result and record
    it as "context not fetched" (j3/j4/d3 -> null, explicitly, with a
    reason) rather than silently treating it as "no parent, no replies."
    """
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            parent_body = _fetch_parent_body(client, parent_id)
            # A full tree can contain hundreds of comments. Direct-hostility
            # review needs the parent, while only continuation-dependent
            # rubric categories need the expensive replies payload.
            replies = _fetch_replies(client, comment_id, link_id, REPLY_DEPTH) if link_id and include_replies else []
    except httpx.HTTPError as e:
        raise ThreadContextUnavailable(f"fetch failed for comment {comment_id}: {e}") from e

    return parent_body, replies


def _fetch_parent_body(client: httpx.Client, parent_id: str | None) -> str | None:
    if not parent_id or parent_id.startswith("t3_"):
        return None  # top-level comment: parent is the submission, not a comment
    raw_id = parent_id.removeprefix("t1_")
    resp = client.get(ARCTIC_SHIFT_COMMENT_IDS, params={"ids": raw_id})
    resp.raise_for_status()
    data = resp.json().get("data", [])
    if not data:
        return None
    return data[0].get("body")


def _flatten_tree(payload: list) -> list[dict]:
    """/api/comments/tree returns Reddit's native nested listing shape --
    each node's replies live in node['data']['replies']['data']['children'],
    not as siblings in the outer list. Recurse and collect every node
    regardless of depth into one flat list, each still carrying its real
    parent_id so the by_parent index built from this works at any depth."""
    flat: list[dict] = []
    for node in payload:
        if not isinstance(node, dict) or "data" not in node:
            continue
        data = node["data"]
        flat.append(data)
        replies = data.get("replies")
        if isinstance(replies, dict):
            children = replies.get("data", {}).get("children", [])
            flat.extend(_flatten_tree(children))
    return flat


def _fetch_replies(client: httpx.Client, comment_id: str, link_id: str, depth: int) -> list[dict]:
    resp = client.get(ARCTIC_SHIFT_COMMENT_TREE, params={"link_id": link_id, "limit": 500})
    resp.raise_for_status()
    payload = resp.json().get("data", [])
    tree = _flatten_tree(payload)

    # limit=500 is a window, not the whole thread. On a megathread (tens of
    # thousands of comments) the target itself can fall outside that
    # window -- in which case we have NOT verified "no replies", we simply
    # never saw the node. Reporting [] in that case would silently claim a
    # fact we don't have; treat it as unavailable instead, same as a
    # network failure, so the caller records it and j3/j4/d3 correctly
    # answer null with a reason rather than a confident false.
    if not any(node.get("id") == comment_id for node in tree):
        raise ThreadContextUnavailable(
            f"comment {comment_id} not present in the fetched tree window for {link_id} "
            f"(likely a megathread larger than the fetch window) -- reply data unverified"
        )

    by_parent: dict[str, list[dict]] = {}
    for node in tree:
        by_parent.setdefault(node.get("parent_id", ""), []).append(node)

    def collect(target_id: str, depth_remaining: int) -> list[dict]:
        if depth_remaining <= 0:
            return []
        children = by_parent.get(f"t1_{target_id}", [])
        out = []
        for child in children:
            out.append({"id": child.get("id"), "author": child.get("author"), "body": child.get("body")})
            out.extend(collect(child.get("id"), depth_remaining - 1))
        return out

    return collect(comment_id, depth)
