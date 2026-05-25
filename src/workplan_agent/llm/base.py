from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from workplan_agent.config import ProfileName

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    def call_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        profile: ProfileName = "balanced",
    ) -> T: ...


def build_messages(system: str, user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def schema_instruction(response_model: type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        "Respond with valid JSON matching this schema exactly. "
        "Do not include markdown fences or extra text.\n"
        f"{schema}"
    )
