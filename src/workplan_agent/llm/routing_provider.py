import warnings
from typing import TypeVar

from pydantic import BaseModel

from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.anthropic_provider import AnthropicProvider
from workplan_agent.llm.base import LLMMessage
from workplan_agent.llm.openai_provider import OpenAIProvider

T = TypeVar("T", bound=BaseModel)


class RoutingLLMProvider:
    """Routes each call to OpenAI or Anthropic based on the profile's configured model."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._openai: OpenAIProvider | None = None
        self._anthropic: AnthropicProvider | None = None

    def _openai_provider(self) -> OpenAIProvider:
        if self._openai is None:
            self._openai = OpenAIProvider()
        return self._openai

    def _anthropic_provider(self) -> AnthropicProvider:
        if self._anthropic is None:
            self._anthropic = AnthropicProvider()
        return self._anthropic

    def warm_prompt_cache(self) -> None:
        if not self._settings.enable_prompt_cache:
            return
        if self._settings.anthropic_api_key:
            self._anthropic_provider().warm_prompt_cache()

    def _resolve_profile(self, profile: ProfileName) -> ProfileName:
        model = self._settings.get_model_for_profile(profile)
        if self._settings.is_anthropic_model(model):
            if self._settings.anthropic_api_key:
                return profile
            if self._settings.openai_api_key:
                warnings.warn(
                    f"Profile '{profile}' maps to '{model}' but ANTHROPIC_API_KEY is not set. "
                    f"Falling back to balanced profile ({self._settings.model_profile_balanced}).",
                    stacklevel=2,
                )
                return "balanced"
            raise ValueError(
                f"Profile '{profile}' requires ANTHROPIC_API_KEY (model: {model}). "
                "Set ANTHROPIC_API_KEY or override MODEL_PROFILE_ACCURATE to an OpenAI model."
            )

        if self._settings.openai_api_key:
            return profile
        if self._settings.anthropic_api_key:
            warnings.warn(
                f"Profile '{profile}' maps to '{model}' but OPENAI_API_KEY is not set. "
                f"Using balanced profile ({self._settings.model_profile_balanced}).",
                stacklevel=2,
            )
            return "balanced"
        raise ValueError(
            f"Profile '{profile}' requires OPENAI_API_KEY (model: {model}). "
            "Set OPENAI_API_KEY or override the model profile in .env."
        )

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
        profile: ProfileName = "balanced",
    ) -> T:
        resolved = self._resolve_profile(profile)
        model = self._settings.get_model_for_profile(resolved)
        if self._settings.is_anthropic_model(model):
            return self._anthropic_provider().call_structured(
                messages, response_model, profile=resolved
            )
        return self._openai_provider().call_structured(
            messages, response_model, profile=resolved
        )
