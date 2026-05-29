import pytest

from workplan_agent.llm.routing_provider import RoutingLLMProvider
from workplan_agent.models.brief import ParsedBrief


def test_routing_openai_only_falls_back_from_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("MODEL", "claude-opus-4-8")
    monkeypatch.setenv("FALLBACK_MODEL", "gpt-5.5-pro")

    import workplan_agent.config as config_module

    config_module._settings = None

    provider = RoutingLLMProvider()
    with pytest.warns(UserWarning, match="Falling back to"):
        model = provider._settings.resolve_model()
    assert model == "gpt-5.5-pro"


def test_routing_requires_key_for_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("MODEL", "claude-opus-4-8")

    import workplan_agent.config as config_module

    config_module._settings = None

    provider = RoutingLLMProvider()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        provider._settings.resolve_model()


def test_routing_uses_configured_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("MODEL", "claude-opus-4-8")

    import workplan_agent.config as config_module

    config_module._settings = None

    provider = RoutingLLMProvider()
    assert provider._settings.resolve_model() == "claude-opus-4-8"
