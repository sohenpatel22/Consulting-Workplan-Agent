import json
import logging
import time
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from workplan_agent.config import get_settings
from workplan_agent.llm.base import schema_instruction
from workplan_agent.llm.caching import (
    ContentBlock,
    LLMMessage,
    count_cache_blocks,
    has_cached_blocks,
    system_blocks_to_api,
)
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.prompts import (
    brief_parser_system_blocks,
    raid_generator_system_blocks,
    revision_system_blocks,
    wbs_generator_system_blocks,
)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def model_rejects_sampling_params(model: str) -> bool:
    """Opus 4.7+ returns 400 if temperature, top_p, or top_k are present."""
    normalized = model.lower()
    return "opus-4-7" in normalized or "opus-4-8" in normalized


class AnthropicProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic models.")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    def warm_prompt_cache(self) -> None:
        if not self._settings.enable_prompt_cache:
            return

        model = self._settings.resolve_model()
        warmups: list[tuple[str, list[ContentBlock]]] = [
            ("brief_parser", brief_parser_system_blocks(ParsedBrief)),
            ("wbs_generator", wbs_generator_system_blocks(WBS)),
            ("raid_generator", raid_generator_system_blocks(RAIDLog)),
            ("revision", revision_system_blocks(WBS)),
        ]

        for name, system_blocks in warmups:
            try:
                warmup_kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": 16,
                    "system": system_blocks_to_api(system_blocks),
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                }
                self._client.messages.create(**warmup_kwargs)
                logger.debug("Warmed Anthropic prompt cache for %s", name)
            except Exception as exc:
                logger.warning("Prompt cache warmup failed for %s: %s", name, exc)

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        model = self._settings.resolve_model()
        if has_cached_blocks(messages) and count_cache_blocks(messages) > 4:
            raise ValueError(
                f"Prompt has {count_cache_blocks(messages)} cache blocks; "
                "Anthropic allows at most 4 per request."
            )
        system, user_messages = self._prepare_messages(messages, response_model)
        last_error: Exception | None = None

        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": 8192,
                    "system": system,
                    "messages": user_messages,
                }
                if not model_rejects_sampling_params(model):
                    kwargs["temperature"] = 0.2
                # Block-level cache_control is set in prompts; top-level cache_control
                # would add another breakpoint and can exceed the limit of 4.
                response = self._client.messages.create(**kwargs)
                content = response.content[0].text
                text = content.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(
                        lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                    )
                data = json.loads(text)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt < self._settings.max_repair_attempts:
                    user_messages = user_messages + [
                        {
                            "role": "user",
                            "content": (
                                f"Your previous response failed validation: {exc}. "
                                f"{schema_instruction(response_model)}"
                            ),
                        }
                    ]
                    time.sleep(0.5)
                else:
                    raise
            except Exception:
                if attempt < self._settings.max_repair_attempts:
                    time.sleep(1.0)
                else:
                    raise

        raise last_error or RuntimeError("Anthropic call failed.")

    def _prepare_messages(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> tuple[Any, list[dict[str, Any]]]:
        system: Any = ""
        user_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg["role"] == "system":
                content = msg["content"]
                if isinstance(content, list):
                    system = system_blocks_to_api(content)
                else:
                    system = f"{content}\n\n{schema_instruction(response_model)}"
            else:
                content = msg["content"]
                if isinstance(content, list):
                    user_messages.append(
                        {"role": msg["role"], "content": system_blocks_to_api(content)}
                    )
                else:
                    user_messages.append({"role": msg["role"], "content": content})

        return system, user_messages
