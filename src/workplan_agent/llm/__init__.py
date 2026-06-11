from workplan_agent.llm.base import LLMProvider
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.llm.routing_provider import RoutingLLMProvider
from workplan_agent.config import get_settings


def get_provider(use_mock: bool = False) -> LLMProvider:
    if use_mock:
        return MockLLMProvider()

    settings = get_settings()
    if not settings.openai_api_key and not settings.anthropic_api_key and not settings.gemini_api_key and not settings.deepseek_api_key:
        raise ValueError(
            "No API keys configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or DEEPSEEK_API_KEY, "
            "or use --mock for offline demo."
        )
    return RoutingLLMProvider()


def warm_prompt_cache() -> None:
    """Prime Anthropic prompt cache with static templates and schemas."""
    provider = get_provider()
    provider.warm_prompt_cache()


def warm_build_prompt_cache(
    parsed_brief_json: str,
    *,
    wbs_json: str | None = None,
    raci_json: str | None = None,
    use_mock: bool = False,
) -> None:
    """Prime cache for WBS/RAID build calls (templates + parsed brief [+ prior artifacts])."""
    if use_mock:
        return
    from workplan_agent.config import get_settings

    if not get_settings().enable_prompt_cache:
        return
    provider = get_provider(use_mock=False)
    warm_prompt_cache()
    if hasattr(provider, "warm_wbs_build_prefix"):
        provider.warm_wbs_build_prefix(parsed_brief_json)
    if (
        wbs_json
        and raci_json
        and hasattr(provider, "warm_raid_build_prefix")
    ):
        provider.warm_raid_build_prefix(parsed_brief_json, wbs_json, raci_json)
