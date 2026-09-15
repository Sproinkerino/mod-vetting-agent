from types import SimpleNamespace

from mod_vetting import stage1_triage


def test_validator_drops_foreign_id_and_keeps_grounded_rows(caplog):
    parsed = {
        "results": [
            {"id": "p8x1byr", "flags": ["hostility_individual"], "confidence": 0.9},
            {"id": "in_batch", "flags": ["self_description"], "confidence": 0.8},
        ]
    }

    results = stage1_triage._validate_triage_output(parsed, {"in_batch"})

    assert [result.id for result in results] == ["in_batch"]
    assert "Discarded 1 out-of-batch triage ID" in caplog.text


def test_triage_schema_restricts_ids_and_foreign_only_output_fails_closed(monkeypatch):
    comments = [
        SimpleNamespace(id="first", body="one"),
        SimpleNamespace(id="second", body="two"),
    ]
    captured = {}

    def fake_call_model(system_prompt, user_prompt, model, input_schema, **kwargs):
        captured["schema"] = input_schema
        return {
            "results": [
                {"id": "p8x1byr", "flags": ["hostility_individual"], "confidence": 0.9}
            ]
        }

    monkeypatch.setattr(stage1_triage, "call_model", fake_call_model)

    results = stage1_triage.triage_batch(comments, "test-batch")

    allowed_ids = captured["schema"]["properties"]["results"]["items"]["properties"]["id"]["enum"]
    assert allowed_ids == ["first", "second"]
    assert results == []