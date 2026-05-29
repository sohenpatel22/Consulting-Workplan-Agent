from typing import Protocol, TypeVar

from pydantic import BaseModel

from workplan_agent.llm.caching import ContentBlock, LLMMessage

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    def call_structured(
        self,
        messages: list[LLMMessage],
        response_model: type[T],
    ) -> T: ...

    def warm_prompt_cache(self) -> None: ...


def build_messages(system: str, user: str) -> list[LLMMessage]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_cached_messages(
    system_blocks: list[ContentBlock],
    user_blocks: list[ContentBlock],
) -> list[LLMMessage]:
    return [
        {"role": "system", "content": system_blocks},
        {"role": "user", "content": user_blocks},
    ]


def schema_instruction(response_model: type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        "Respond with valid JSON matching this schema exactly. "
        "Do not include markdown fences or extra text.\n"
        f"{schema}"
    )
