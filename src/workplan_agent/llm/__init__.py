from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.anthropic_provider import AnthropicProvider
from workplan_agent.llm.base import LLMProvider
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.llm.openai_provider import OpenAIProvider


def get_provider(use_mock: bool = False) -> LLMProvider:
    if use_mock:
        return MockLLMProvider()

    settings = get_settings()
    profile_model = settings.get_model_for_profile(settings.default_profile)

    if settings.is_anthropic_model(profile_model):
        if settings.anthropic_api_key:
            return AnthropicProvider()
        if settings.openai_api_key:
            return OpenAIProvider()
        raise ValueError(
            "No API keys configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
            "or use --mock for offline demo."
        )

    if settings.openai_api_key:
        return OpenAIProvider()
    if settings.anthropic_api_key:
        return AnthropicProvider()
    raise ValueError(
        "No API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY, "
        "or use --mock for offline demo."
    )


def get_provider_for_profile(profile: ProfileName, use_mock: bool = False) -> LLMProvider:
    if use_mock:
        return MockLLMProvider()

    settings = get_settings()
    model = settings.get_model_for_profile(profile)

    if settings.is_anthropic_model(model):
        return AnthropicProvider()
    return OpenAIProvider()
