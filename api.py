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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mod_vetting.orchestrator import run_job
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


class CreateJobRequest(BaseModel):
    username: str
    rules: str
    register_notes: str
    comment_cap: int = 500
    post_cap: int = 20
    applicant_meta: dict | None = None


def _run_in_background(job_id: str, req: CreateJobRequest):
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
        # run_job's job_id (from storage.create_job) is not known to the
        # caller until this returns -- re-key under our pre-issued job_id
        # so POST's returned id is the one GET actually looks up.
        _jobs[job_id] = {"status": "done", "report": report, "error": None}
    except Exception as e:  # noqa: BLE001 -- surfaced to the poller, not swallowed
        _jobs[job_id] = {"status": "error", "report": None, "error": str(e)}


@app.post("/jobs")
def create_job(req: CreateJobRequest):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "report": None, "error": None}
    thread = threading.Thread(target=_run_in_background, args=(job_id, req), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "running"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    entry = _jobs.get(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    return entry


@app.get("/health")
def health():
    return {"ok": True}
