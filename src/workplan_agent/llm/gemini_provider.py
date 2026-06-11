import json
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from workplan_agent.config import get_settings
from workplan_agent.llm.base import schema_instruction
from workplan_agent.llm.caching import LLMMessage, flatten_content

T = TypeVar("T", bound=BaseModel)


class GeminiProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini models.")
        # Google's OpenAI-compatible endpoint
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        self._client = OpenAI(api_key=settings.gemini_api_key, base_url=base_url)
        self._settings = settings

    def warm_prompt_cache(self) -> None:
        # Gemini does not use Anthropic-style manual prompt caching warming.
        return

    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T:
        model = self._settings.resolve_model()
        api_messages = self._to_openai_messages(messages, response_model)
        last_error: Exception | None = None

        max_output_tokens = self._settings.llm_max_output_tokens

        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=api_messages,
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_completion_tokens=max_output_tokens,
                )
                content = response.choices[0].message.content or "{}"
                data = json.loads(content)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt < self._settings.max_repair_attempts:
                    repair_hint = f"Your previous response failed validation: {exc}."
                    api_messages = api_messages + [
                        {
                            "role": "user",
                            "content": (
                                f"{repair_hint} "
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

        raise last_error or RuntimeError("Gemini call failed.")

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
