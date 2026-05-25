import json
import time
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.base import schema_instruction

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic models.")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    def call_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        profile: ProfileName = "balanced",
    ) -> T:
        model = self._settings.get_model_for_profile(profile)
        system = ""
        user_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                user_messages.append(msg)

        system = f"{system}\n\n{schema_instruction(response_model)}"
        last_error: Exception | None = None

        for attempt in range(self._settings.max_repair_attempts + 1):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=8192,
                    system=system,
                    messages=user_messages,
                    temperature=0.2,
                )
                content = response.content[0].text
                # Strip markdown fences if present
                text = content.strip()
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
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
