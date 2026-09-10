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