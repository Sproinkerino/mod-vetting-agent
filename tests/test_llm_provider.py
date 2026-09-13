from mod_vetting import llm


def test_explicit_openrouter_provider_wins_over_anthropic(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    captured = {}

    def fake_openrouter(*args, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(llm, "_call_openrouter", fake_openrouter)
    result = llm.call_model("system", "user", llm.TRIAGE_MODEL, {"type": "object"})

    assert result == {"ok": True}
    assert captured["api_key"] == "openrouter-secret"


def test_explicit_openrouter_requires_its_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    try:
        llm.call_model("system", "user", llm.TRIAGE_MODEL, {"type": "object"})
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("expected a missing OpenRouter key error")


def test_explicit_deepseek_provider_wins_over_other_keys(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    captured = {}

    def fake_deepseek(*args, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(llm, "_call_deepseek", fake_deepseek)
    result = llm.call_model("system", "user", llm.TRIAGE_MODEL, {"type": "object"})

    assert result == {"ok": True}
    assert captured["api_key"] == "deepseek-secret"


def test_explicit_deepseek_requires_its_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-secret")

    try:
        llm.call_model("system", "user", llm.TRIAGE_MODEL, {"type": "object"})
    except RuntimeError as exc:
        assert "DEEPSEEK_API_KEY" in str(exc)
    else:
        raise AssertionError("expected a missing DeepSeek key error")


def test_deepseek_adapter_uses_flash_and_parses_tool_arguments(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "tool_calls": [{"function": {"arguments": '{"ok": true}'}}],
                    },
                }],
            }

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse()

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    result = llm._call_deepseek(
        "system", "user", llm.TRIAGE_MODEL, {"type": "object"},
        max_tokens=32, api_key="deepseek-secret",
    )

    assert result == {"ok": True}
    assert captured["url"] == llm.DEEPSEEK_URL
    assert captured["json"]["model"] == "deepseek-v4-flash"
    assert captured["json"]["thinking"] == {"type": "disabled"}
    assert captured["json"]["tool_choice"]["function"]["name"] == llm.TOOL_NAME


def test_deepseek_models_are_reported_and_change_contract_hash(monkeypatch):
    from mod_vetting.orchestrator import compute_contract_hash

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    anthropic_hash = compute_contract_hash()

    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    models = llm.configured_models()
    deepseek_hash = compute_contract_hash()

    assert models == {
        "provider": "deepseek",
        "triage": "deepseek-v4-flash",
        "adjudicate": "deepseek-v4-pro",
    }
    assert deepseek_hash != anthropic_hash
