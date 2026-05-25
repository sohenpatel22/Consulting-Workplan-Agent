import pytest

from workplan_agent.config import Settings
from workplan_agent.llm.routing_provider import RoutingLLMProvider
from workplan_agent.models.brief import ParsedBrief


def test_routing_openai_only_falls_back_from_accurate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("MODEL_PROFILE_ACCURATE", "claude-sonnet-4-20250514")

    import workplan_agent.config as config_module

    config_module._settings = None

    provider = RoutingLLMProvider()
    with pytest.warns(UserWarning, match="Falling back to balanced"):
        resolved = provider._resolve_profile("accurate")
    assert resolved == "balanced"


def test_routing_requires_key_for_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    import workplan_agent.config as config_module

    config_module._settings = None

    provider = RoutingLLMProvider()
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        provider._resolve_profile("accurate")
