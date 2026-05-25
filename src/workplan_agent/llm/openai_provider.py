import json
import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.base import schema_instruction

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models.")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._settings = settings

    def call_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        profile: ProfileName = "balanced",
    ) -> T:
        model = self._settings.get_model_for_profile(profile)
        if self._settings.is_anthropic_model(model):
            raise ValueError(
                f"Model '{model}' is an Anthropic model; use AnthropicProvider instead."
            )

        last_error: Exception | None = None
        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                content = response.choices[0].message.content or "{}"
                data = json.loads(content)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt < self._settings.max_repair_attempts:
                    messages = messages + [
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
