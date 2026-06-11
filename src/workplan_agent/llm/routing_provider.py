from typing import TypeVar

from pydantic import BaseModel

from workplan_agent.config import get_settings
from workplan_agent.llm.anthropic_provider import AnthropicProvider
from workplan_agent.llm.base import LLMMessage
from workplan_agent.llm.openai_provider import OpenAIProvider
from workplan_agent.llm.gemini_provider import GeminiProvider
from workplan_agent.llm.deepseek_provider import DeepseekProvider

T = TypeVar("T", bound=BaseModel)


class RoutingLLMProvider:
    """Routes each call to OpenAI, Anthropic, Gemini, or Deepseek based on the configured model."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._openai: OpenAIProvider | None = None
        self._anthropic: AnthropicProvider | None = None
        self._gemini: GeminiProvider | None = None
        self._deepseek: DeepseekProvider | None = None

    def _openai_provider(self) -> OpenAIProvider:
        if self._openai is None:
            self._openai = OpenAIProvider()
        return self._openai

    def _anthropic_provider(self) -> AnthropicProvider:
        if self._anthropic is None:
            self._anthropic = AnthropicProvider()
        return self._anthropic

    def _gemini_provider(self) -> GeminiProvider:
        if self._gemini is None:
            self._gemini = GeminiProvider()
        return self._gemini

    def _deepseek_provider(self) -> DeepseekProvider:
        if self._deepseek is None:
            self._deepseek = DeepseekProvider()
        return self._deepseek

    def warm_prompt_cache(self) -> None:
        if not self._settings.enable_prompt_cache:
            return
        if self._settings.anthropic_api_key:
            self._anthropic_provider().warm_prompt_cache()

    def warm_wbs_build_prefix(self, parsed_brief_json: str) -> None:
        if not self._settings.enable_prompt_cache:
            return
        if self._settings.anthropic_api_key:
            self._anthropic_provider().warm_wbs_build_prefix(parsed_brief_json)

    def warm_raid_build_prefix(
        self,
        parsed_brief_json: str,
        wbs_json: str,
        raci_json: str,
    ) -> None:
        if not self._settings.enable_prompt_cache:
            return
        if self._settings.anthropic_api_key:
            self._anthropic_provider().warm_raid_build_prefix(
                parsed_brief_json,
                wbs_json,
                raci_json,
            )

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        model = self._settings.resolve_model()
        if self._settings.is_anthropic_model(model):
            return self._anthropic_provider().call_structured(messages, response_model)
        if self._settings.is_gemini_model(model):
            return self._gemini_provider().call_structured(messages, response_model)
        if self._settings.is_deepseek_model(model):
            return self._deepseek_provider().call_structured(messages, response_model)
        return self._openai_provider().call_structured(messages, response_model)
