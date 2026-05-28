from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.base import LLMProvider
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.llm.routing_provider import RoutingLLMProvider


def get_provider(use_mock: bool = False) -> LLMProvider:
    if use_mock:
        return MockLLMProvider()

    settings = get_settings()
    if not settings.openai_api_key and not settings.anthropic_api_key:
        raise ValueError(
            "No API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY, "
            "or use --mock for offline demo."
        )
    return RoutingLLMProvider()


def warm_prompt_cache() -> None:
    """Prime Anthropic prompt cache with static templates and schemas."""
    provider = get_provider()
    provider.warm_prompt_cache()


def get_provider_for_profile(profile: ProfileName, use_mock: bool = False) -> LLMProvider:
    if use_mock:
        return MockLLMProvider()
    return get_provider()
