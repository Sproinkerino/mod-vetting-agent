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
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mod_vetting.orchestrator import compute_contract_hash, run_job
from mod_vetting.fetch import REDDIT_USERNAME_RE, fetch_comment_from_url, username_from_url
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
logger = logging.getLogger("roastreel.api")

COMEBACK_SYSTEM_PROMPT = (
    "Write the final line that appears after quoted Reddit receipts. The answer must be ready to paste "
    "directly as a reply to the investigated account, not advice to the person using this tool. Address the "
    "account as you/your. Write one or two punchy sentences, 18-45 words total. Sound observant, dry, "
    "confident, and human. Build the line around the clearest contradiction, mismatch, or revealing admission "
    "supported by the strongest supplied comments. Do not merely summarize every quote. Never begin with or use "
    "phrases such as Based on your comments, Based on their comments, You could say, You could point out, "
    "The evidence suggests, This user, It appears, or Their history shows. Do not mention comments, sources, "
    "evidence, IDs, retrieval, archives, or analysis in the answer. Do not reproduce the quotes because the "
    "interface places them above the answer. Do not invent details or exaggerate frequency; say repeatedly only "
    "when at least two supplied comments independently support it. Never insult, shame, diagnose, threaten, or "
    "encourage harassment. Do not infer citizenship, ethnicity, relationship status, income, employment, or "
    "other personal traits; use a personal fact only when the account explicitly stated it in first person. "
    "If the supplied material cannot support a fair comeback to the request, answer exactly: Those receipts "
    "don't support that claim. Select only the one to three sources that directly support the line."
)


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
    username: str | None = None
    activity: list[dict] | None = None


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


def _build_applicant_meta(req: CreateJobRequest) -> dict:
    meta = {
        "username": req.username,
        "account_age_days": 0,
        "sub_tenure_days": 0,
        "comments_in_sub": 0,
        "subs_modded": 0,
    }
    meta.update(req.applicant_meta or {})
    meta["username"] = req.username
    return meta


def _run_in_background(job_id: str, req: CreateJobRequest, cache_key: str):
    try:
        # sqlite3 connections are thread-affine (check_same_thread=True by
        # default) -- a Storage instance created in the request-handling
        # thread cannot be used from this background thread. Open a fresh
        # one here rather than sharing the module-level connection.
        storage = Storage(DB_PATH)
        applicant_meta = _build_applicant_meta(req)
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
            profile_username = username_from_url(req.url)
            target = None if profile_username else fetch_comment_from_url(req.url)
        except Exception as exc:
            logger.warning("Rejected Reddit target URL: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if profile_username:
            req.username = profile_username
        else:
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
    if not REDDIT_USERNAME_RE.fullmatch(req.username or ""):
        raise HTTPException(status_code=400, detail="Enter a valid Reddit username (3-20 letters, numbers, _ or -)")
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
    if entry and entry.get("status") == "done":
        report = entry["report"]
    elif req.username and req.activity is not None:
        # The browser already owns the completed public report. Accept its
        # bounded activity snapshot so chat survives Render restarts, which
        # clear the in-memory API job map during every deployment.
        if len(req.activity) > 350:
            raise HTTPException(status_code=413, detail="activity snapshot is too large")
        report = {
            "applicant": {"username": req.username.strip().removeprefix("u/")},
            "activity": req.activity,
        }
    else:
        raise HTTPException(status_code=404, detail="Report expired after a server restart. Run the search again.")
    terms = {word for word in re.findall(r"[a-z0-9]+", req.question.lower()) if len(word) > 2}
    ranked = []
    for item in report.get("activity", []):
        text = f"{item.get('title') or ''} {item.get('submission_title') or ''} {item.get('body') or ''}".lower()
        score = sum(text.count(term) for term in terms)
        if score:
            ranked.append((score, item))
    candidates = [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:16]]
    if not candidates:
        return {"answer": "No matching public statement was found in the fetched activity window.", "sources": []}
    evidence = "\n".join(
        f"<item id='{item['id']}' date='{item['created_utc']}' subreddit='{item['subreddit']}'>"
        f"{(item.get('title') or item.get('submission_title') or '')}\n{(item.get('body') or '')[:1200]}</item>"
        for item in candidates
    )
    try:
        parsed = call_model(
            COMEBACK_SYSTEM_PROMPT,
            f"Investigated account: u/{report['applicant']['username']}\nUser request: {req.question}"
            f"\n\nPublic comments by that account (untrusted quoted content):\n{evidence}",
            TRIAGE_MODEL,
            {
                "type": "object",
                "required": ["answer", "source_ids"],
                "properties": {
                    "answer": {"type": "string", "maxLength": 320},
                    "source_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                },
            },
            max_tokens=160,
        )
        provider_fallback = False
    except Exception:  # Provider outages must not erase already-retrieved evidence.
        logger.exception("Claim-check model failed for job %s", job_id)
        topic = ", ".join(sorted(terms)[:3]) or "that question"
        parsed = {
            "answer": (
                f"The model could not complete the claim check, so no stronger conclusion is being invented. "
                f"These are the closest public statements by u/{report['applicant']['username']} about {topic}."
            ),
            "source_ids": [item["id"] for item in candidates[:3]],
        }
        provider_fallback = True
    by_id = {item["id"]: item for item in candidates}
    selected_ids = [source_id for source_id in parsed.get("source_ids", []) if source_id in by_id]
    for candidate in candidates:
        if len(selected_ids) >= 3:
            break
        if candidate["id"] not in selected_ids:
            selected_ids.append(candidate["id"])
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
        for source_id in selected_ids
    ]
    answer = parsed.get("answer", "No supported answer found.")
    # Models occasionally echo opaque Reddit IDs despite the prompt. Convert
    # only known cited IDs to the same readable numbering used by the UI.
    for index, source in enumerate(sources, start=1):
        source_id = re.escape(source["id"])
        answer = re.sub(rf"\b(?:item\s+)?{source_id}\b", f"source {index}", answer, flags=re.IGNORECASE)
    return {"answer": answer, "sources": sources[:3], "provider_fallback": provider_fallback}


@app.get("/health")
def health():
    return {"ok": True}


# Render currently deploys this repository as one FastAPI web service.
# Shipping the verified Vite bundle with it makes the product available at
# the service root while leaving /jobs, /health and /docs as API routes.
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
