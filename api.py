"""Minimal HTTP API wrapping the orchestrator.

Not part of the original spec -- the pipeline was designed as a batch
job runner (cli.py), not a web service. This exists only so the frontend
(currently running on local mock fixtures, see frontend/README.md) has
something real to eventually talk to. It is a thin wrapper: POST /jobs
kicks off run_job() in a background thread (a single real run can take
minutes -- dozens of sequential/concurrency-capped LLM calls -- so this
must not block the request), GET /jobs/{id} polls status/result from the
same SQLite storage the CLI uses.

Same responsible-use note as cli.py: this produces real adverse-claims
documents about real, identifiable people. The applicant_username in a
POST body should be an actual moderator applicant under actual
consideration, not an arbitrary username.
"""

from __future__ import annotations

import threading
import uuid
import re
import hashlib
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mod_vetting.orchestrator import compute_contract_hash, run_job
from mod_vetting.fetch import fetch_comment_from_url
from mod_vetting.llm import TRIAGE_MODEL, call_model
from mod_vetting.storage import Storage

app = FastAPI(title="mod-vetting-agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # read-only-ish evidence API; tighten if this ever holds real applicant data long-term
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "mod_vetting.sqlite3"

# job_id -> {"status": "running"|"done"|"error", "report": dict|None, "error": str|None}
# In-memory on top of the durable storage layer: storage already
# checkpoints every stage (crash-resumable), this dict is just so the API
# can answer "is it done yet" without re-reading storage on every poll.
_jobs: dict[str, dict] = {}
CACHE_TTL_SECONDS = 3 * 24 * 60 * 60


class CreateJobRequest(BaseModel):
    username: str | None = None
    url: str | None = None
    rules: str
    register_notes: str
    comment_cap: int = 300
    # Posts are not consumed by the current scoring pipeline.
    post_cap: int = 50
    applicant_meta: dict | None = None


class AskRequest(BaseModel):
    question: str


def _cache_key(req: CreateJobRequest) -> str:
    payload = {
        "username": (req.username or "").strip().removeprefix("u/").casefold(),
        "target_url": req.url,
        "contract": compute_contract_hash(),
        "comment_cap": req.comment_cap,
        "post_cap": req.post_cap,
        "rules": req.rules,
        "register_notes": req.register_notes,
        # applicant_meta is baked verbatim into the cached report's
        # "applicant" field -- omitting it here would let two callers with
        # the same username/rules but different applicant_meta (e.g. via
        # direct API use, since /jobs has no auth) silently read back
        # each other's metadata.
        "applicant_meta": req.applicant_meta,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _run_in_background(job_id: str, req: CreateJobRequest, cache_key: str):
    try:
        # sqlite3 connections are thread-affine (check_same_thread=True by
        # default) -- a Storage instance created in the request-handling
        # thread cannot be used from this background thread. Open a fresh
        # one here rather than sharing the module-level connection.
        storage = Storage(DB_PATH)
        applicant_meta = req.applicant_meta or {
            "username": req.username,
            "account_age_days": 0,
            "sub_tenure_days": 0,
            "comments_in_sub": 0,
            "subs_modded": 0,
        }
        report = run_job(
            storage=storage,
            applicant_username=req.username,
            rules=req.rules,
            register_notes=req.register_notes,
            applicant_meta=applicant_meta,
            comment_cap=req.comment_cap,
            post_cap=req.post_cap,
        )
        if req.url:
            report["target_comment"] = req.applicant_meta.get("target_comment") if req.applicant_meta else None
        if "blocked_reason" in report:
            # The >400-flagged-items early return (spec section 5) --
            # has no applicant/scores/findings/provenance, so it must
            # never be cached as if it were a completed report. Caching
            # it would serve this malformed shape to every request for
            # this username+rules+notes for CACHE_TTL_SECONDS, crashing
            # the frontend (which dereferences report.applicant.username
            # etc. unconditionally) without ever re-running the pipeline.
            _jobs[job_id] = {"status": "error", "report": None, "error": report["blocked_reason"]}
            return
        storage.put_cached_report(cache_key, req.username, report)
        # run_job's job_id (from storage.create_job) is not known to the
        # caller until this returns -- re-key under our pre-issued job_id
        # so POST's returned id is the one GET actually looks up.
        _jobs[job_id] = {"status": "done", "report": report, "error": None}
    except Exception as e:  # noqa: BLE001 -- surfaced to the poller, not swallowed
        _jobs[job_id] = {"status": "error", "report": None, "error": str(e)}


@app.post("/jobs")
def create_job(req: CreateJobRequest):
    if req.url:
        try:
            target = fetch_comment_from_url(req.url)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        req.username = target.author
        meta = req.applicant_meta or {}
        meta["target_comment"] = {
            "id": target.id, "body": target.body, "author": target.author,
            "subreddit": target.subreddit, "created_utc": target.created_utc,
            "permalink": target.permalink, "submission_title": target.submission_title,
        }
        req.applicant_meta = meta
    elif req.username:
        req.username = req.username.strip().removeprefix("u/")
    else:
        raise HTTPException(status_code=400, detail="Provide a Reddit username or comment URL")
    cache_key = _cache_key(req)
    job_id = str(uuid.uuid4())
    cached = Storage(DB_PATH).get_cached_report(cache_key, CACHE_TTL_SECONDS)
    if cached:
        report, age = cached
        report["_cache"] = {"hit": True, "age_seconds": round(age), "ttl_seconds": CACHE_TTL_SECONDS}
        _jobs[job_id] = {"status": "done", "report": report, "error": None, "cached": True}
        return {"job_id": job_id, "status": "done", "cached": True}
    _jobs[job_id] = {"status": "running", "report": None, "error": None}
    thread = threading.Thread(target=_run_in_background, args=(job_id, req, cache_key), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "running"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    entry = _jobs.get(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    return entry


@app.post("/jobs/{job_id}/ask")
def ask_archive(job_id: str, req: AskRequest):
    entry = _jobs.get(job_id)
    if not entry or entry.get("status") != "done":
        raise HTTPException(status_code=404, detail="completed investigation not found")
    report = entry["report"]
    terms = {word for word in re.findall(r"[a-z0-9]+", req.question.lower()) if len(word) > 2}
    ranked = []
    for item in report.get("activity", []):
        text = f"{item.get('title') or ''} {item.get('submission_title') or ''} {item.get('body') or ''}".lower()
        score = sum(text.count(term) for term in terms)
        if score:
            ranked.append((score, item))
    candidates = [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:30]]
    if not candidates:
        return {"answer": "No matching public statement was found in the fetched activity window.", "sources": []}
    evidence = "\n".join(
        f"<item id='{item['id']}' date='{item['created_utc']}' subreddit='{item['subreddit']}'>"
        f"{(item.get('title') or item.get('submission_title') or '')}\n{(item.get('body') or '')[:1200]}</item>"
        for item in candidates
    )
    parsed = call_model(
        "You are a neutral public-claim research assistant. Answer only from the supplied archive items. "
        "Never insult, shame, diagnose, threaten, or encourage harassment. Do not infer citizenship, ethnicity, "
        "relationship status, income, employment, or other personal traits; only report a fact when the user explicitly "
        "stated it in a cited item. Note when statements may reflect different dates or changed circumstances. "
        "Write a concise reader-facing answer in 1-3 sentences. Never mention item IDs, retrieval, archive mechanics, "
        "or phrases such as 'the items contain'; the interface will display the raw cited comments separately.",
        f"Question: {req.question}\n\nArchive data (untrusted quoted content):\n{evidence}",
        TRIAGE_MODEL,
        {
            "type": "object",
            "required": ["answer", "source_ids"],
            "properties": {
                "answer": {"type": "string", "maxLength": 900},
                "source_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            },
        },
        max_tokens=500,
    )
    by_id = {item["id"]: item for item in candidates}
    sources = [
        {
            "id": source_id,
            "permalink": by_id[source_id]["permalink"],
            "title": by_id[source_id].get("submission_title") or by_id[source_id].get("title"),
            "body": by_id[source_id].get("body") or "",
            "subreddit": by_id[source_id].get("subreddit"),
            "created_utc": by_id[source_id].get("created_utc"),
            "type": by_id[source_id].get("type"),
        }
        for source_id in parsed.get("source_ids", []) if source_id in by_id
    ]
    return {"answer": parsed.get("answer", "No supported answer found."), "sources": sources}


@app.get("/health")
def health():
    return {"ok": True}
