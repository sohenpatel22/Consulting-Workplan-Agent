import json
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from workplan_agent.config import get_settings
from workplan_agent.llm.base import schema_instruction
from workplan_agent.llm.caching import LLMMessage, flatten_content

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models.")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._settings = settings

    def warm_prompt_cache(self) -> None:
        # OpenAI applies automatic prefix caching for repeated prompt prefixes.
        return

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        model = self._settings.resolve_model()
        if self._settings.is_anthropic_model(model):
            raise ValueError(
                f"Model '{model}' is an Anthropic model; use AnthropicProvider instead."
            )

        api_messages = self._to_openai_messages(messages, response_model)
        last_error: Exception | None = None

        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=api_messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                content = response.choices[0].message.content or "{}"
                data = json.loads(content)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt < self._settings.max_repair_attempts:
                    api_messages = api_messages + [
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

        raise last_error or RuntimeError("OpenAI call failed.")

    def _to_openai_messages(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> list[dict[str, str]]:
        api_messages: list[dict[str, str]] = []
        for msg in messages:
            content = msg["content"]
            if msg["role"] == "system" and isinstance(content, str):
                text = f"{content}\n\n{schema_instruction(response_model)}"
            else:
                text = flatten_content(content)
            api_messages.append({"role": msg["role"], "content": text})
        return api_messages
