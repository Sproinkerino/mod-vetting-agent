from fastapi.testclient import TestClient

import api as api_module
from mod_vetting.cancellation import JobCancelled, ensure_not_cancelled


def test_cancel_running_job_marks_it_for_cooperative_stop():
    job_id = "cancel-running-test"
    api_module._jobs[job_id] = {
        "status": "running",
        "phase": "analyzing",
        "cancel_requested": False,
    }
    try:
        response = TestClient(api_module.app).post(f"/jobs/{job_id}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelling"
        assert api_module._jobs[job_id]["cancel_requested"] is True
        assert api_module._jobs[job_id]["phase"] == "cancelling"
    finally:
        api_module._jobs.pop(job_id, None)


def test_cancel_completed_job_is_idempotent():
    job_id = "cancel-complete-test"
    api_module._jobs[job_id] = {"status": "done", "report": {}}
    try:
        response = TestClient(api_module.app).post(f"/jobs/{job_id}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "done"
        assert "cancel_requested" not in api_module._jobs[job_id]
    finally:
        api_module._jobs.pop(job_id, None)


def test_cancellation_guard_fails_at_safe_boundary():
    try:
        ensure_not_cancelled(lambda: True)
    except JobCancelled as error:
        assert str(error) == "Investigation cancelled"
    else:
        raise AssertionError("Cancellation did not stop the next stage")