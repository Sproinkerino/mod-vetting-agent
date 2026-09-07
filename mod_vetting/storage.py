"""Durable state machine storage. implementation-spec.md section 5.

SQLite for a single-process build -- swap the connection for a real
durable store (Postgres, etc.) behind the same interface for production
concurrency; the checkpoint/idempotency contract doesn't change.

Checkpoint every stage: write outputs keyed by (job_id, stage) before
advancing, so a crash resumes instead of restarting.

Idempotency key per unit of work: (job_id, stage, item_id, contract_hash).
Retries never duplicate; a re-run after a prompt change invalidates only
stages downstream of the change, because the contract hash moves.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass

STAGES = [
    "created", "fetching", "triaging", "adjudicating", "grounding",
    "synthesising", "steelmanning", "reconciling",
    "awaiting_human", "ready_for_vote", "decided", "purged",
]

# Stages 3-5 (synthesising/steelmanning/reconciling) have no prompt spec
# in implementation-spec.md -- this build routes straight from grounding
# to awaiting_human rather than fabricate them. See README.
IMPLEMENTED_TERMINAL_STAGE = "awaiting_human"


class UnknownJobError(Exception):
    pass


@dataclass
class JobRecord:
    job_id: str
    applicant_username: str
    state: str
    contract_hash: str
    created_at: float


class Storage:
    def __init__(self, db_path: str = "mod_vetting.sqlite3"):
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                applicant_username TEXT NOT NULL,
                state TEXT NOT NULL,
                contract_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stage_outputs (
                job_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                payload TEXT NOT NULL,
                written_at REAL NOT NULL,
                PRIMARY KEY (job_id, stage)
            );

            -- Idempotency ledger: one row per unit of work actually completed.
            -- A retry checks this before re-doing (and re-billing) an item.
            CREATE TABLE IF NOT EXISTS work_units (
                job_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                item_id TEXT NOT NULL,
                contract_hash TEXT NOT NULL,
                result TEXT NOT NULL,
                completed_at REAL NOT NULL,
                PRIMARY KEY (job_id, stage, item_id, contract_hash)
            );

            CREATE TABLE IF NOT EXISTS excluded_items (
                job_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                item_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                recorded_at REAL NOT NULL
            );
            """
        )
        self._conn.commit()

    @contextmanager
    def _cursor(self):
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def create_job(self, applicant_username: str, contract_hash: str) -> JobRecord:
        job_id = str(uuid.uuid4())
        record = JobRecord(job_id, applicant_username, "created", contract_hash, time.time())
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (job_id, applicant_username, state, contract_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (record.job_id, record.applicant_username, record.state, record.contract_hash, record.created_at),
            )
        return record

    def get_job(self, job_id: str) -> JobRecord:
        with self._cursor() as cur:
            row = cur.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise UnknownJobError(job_id)
        return JobRecord(row["job_id"], row["applicant_username"], row["state"], row["contract_hash"], row["created_at"])

    def set_state(self, job_id: str, state: str):
        if state not in STAGES:
            raise ValueError(f"unknown state {state!r}")
        with self._cursor() as cur:
            cur.execute("UPDATE jobs SET state = ? WHERE job_id = ?", (state, job_id))

    def checkpoint_stage(self, job_id: str, stage: str, payload: dict):
        """Write a stage's full output before advancing state. Idempotent:
        re-checkpointing the same (job_id, stage) overwrites, it doesn't
        duplicate or error -- a resumed job re-running a stage that
        already checkpointed just replaces it with the same (or corrected)
        output."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO stage_outputs (job_id, stage, payload, written_at) VALUES (?, ?, ?, ?)",
                (job_id, stage, json.dumps(payload), time.time()),
            )

    def get_stage_output(self, job_id: str, stage: str) -> dict | None:
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT payload FROM stage_outputs WHERE job_id = ? AND stage = ?", (job_id, stage)
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def work_unit_done(self, job_id: str, stage: str, item_id: str, contract_hash: str) -> dict | None:
        """Returns the stored result if this unit of work already
        completed under this exact contract, else None. A prompt/model
        change moves contract_hash, so a re-run after a fix does NOT
        skip re-processing items -- only a pure retry of the same
        contract does."""
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT result FROM work_units WHERE job_id=? AND stage=? AND item_id=? AND contract_hash=?",
                (job_id, stage, item_id, contract_hash),
            ).fetchone()
        return json.loads(row["result"]) if row else None

    def record_work_unit(self, job_id: str, stage: str, item_id: str, contract_hash: str, result: dict):
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO work_units (job_id, stage, item_id, contract_hash, result, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, stage, item_id, contract_hash, json.dumps(result), time.time()),
            )

    def record_excluded(self, job_id: str, stage: str, item_id: str, reason: str):
        """unparseable / timed-out-twice items. Excluded items appear in
        provenance -- silent exclusion is how a review ends up looking
        clean because the pipeline choked (spec section 5)."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO excluded_items (job_id, stage, item_id, reason, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, stage, item_id, reason, time.time()),
            )

    def get_excluded(self, job_id: str) -> list[dict]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT stage, item_id, reason FROM excluded_items WHERE job_id = ?", (job_id,)
            ).fetchall()
        return [dict(r) for r in rows]
