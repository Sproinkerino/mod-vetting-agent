import pytest

from mod_vetting.storage import Storage, UnknownJobError


@pytest.fixture
def storage(tmp_path):
    return Storage(str(tmp_path / "test.sqlite3"))


def test_create_and_get_job(storage):
    job = storage.create_job("someuser", contract_hash="abc123")
    fetched = storage.get_job(job.job_id)
    assert fetched.applicant_username == "someuser"
    assert fetched.state == "created"
    assert fetched.contract_hash == "abc123"


def test_unknown_job_raises(storage):
    with pytest.raises(UnknownJobError):
        storage.get_job("does-not-exist")


def test_set_state_rejects_unknown_state(storage):
    job = storage.create_job("u", "c1")
    with pytest.raises(ValueError):
        storage.set_state(job.job_id, "not_a_real_state")


def test_checkpoint_is_resumable_and_idempotent(storage):
    job = storage.create_job("u", "c1")
    storage.checkpoint_stage(job.job_id, "fetching", {"items": [1, 2, 3]})
    # simulate a crash + resume: re-checkpointing the same stage overwrites
    # cleanly rather than erroring or duplicating
    storage.checkpoint_stage(job.job_id, "fetching", {"items": [1, 2, 3, 4]})
    result = storage.get_stage_output(job.job_id, "fetching")
    assert result == {"items": [1, 2, 3, 4]}


def test_work_unit_idempotency_same_contract(storage):
    job = storage.create_job("u", "contract-v1")
    assert storage.work_unit_done(job.job_id, "adjudicating", "item1", "contract-v1") is None

    storage.record_work_unit(job.job_id, "adjudicating", "item1", "contract-v1", {"answer": True})
    # a retry under the SAME contract must see it as already done
    assert storage.work_unit_done(job.job_id, "adjudicating", "item1", "contract-v1") == {"answer": True}


def test_work_unit_not_reused_across_contract_change(storage):
    job = storage.create_job("u", "contract-v1")
    storage.record_work_unit(job.job_id, "adjudicating", "item1", "contract-v1", {"answer": True})

    # a prompt edit bumps the contract hash -- the old result must NOT be
    # served for the new contract (spec: "a re-run after a prompt change
    # invalidates only the stages downstream of the change")
    assert storage.work_unit_done(job.job_id, "adjudicating", "item1", "contract-v2") is None


def test_excluded_items_are_recorded_not_silently_dropped(storage):
    job = storage.create_job("u", "c1")
    storage.record_excluded(job.job_id, "adjudicating", "item42", "unparseable")
    excluded = storage.get_excluded(job.job_id)
    assert len(excluded) == 1
    assert excluded[0]["item_id"] == "item42"
    assert excluded[0]["reason"] == "unparseable"
