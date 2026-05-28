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
                self._client.messages.create(
                    model=model,
                    max_tokens=16,
                    system=system_blocks_to_api(system_blocks),
                    messages=[{"role": "user", "content": "Reply with OK."}],
                    temperature=0,
                )
                logger.debug("Warmed Anthropic prompt cache for %s", name)
            except Exception as exc:
                logger.warning("Prompt cache warmup failed for %s: %s", name, exc)

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        model = self._settings.resolve_model()
        system, user_messages = self._prepare_messages(messages, response_model)
        last_error: Exception | None = None

        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "max_tokens": 8192,
                    "system": system,
                    "messages": user_messages,
                    "temperature": 0.2,
                }
                if self._settings.enable_prompt_cache and has_cached_blocks(messages):
                    kwargs["cache_control"] = {"type": "ephemeral"}

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
