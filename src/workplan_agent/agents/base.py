from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from workplan_agent.config import ProfileName
from workplan_agent.llm.base import LLMProvider, build_messages, schema_instruction

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    system_prompt: str = ""
    profile: ProfileName = "balanced"

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    @property
    @abstractmethod
    def response_model(self) -> type[T]: ...

    def build_user_prompt(self, **kwargs: object) -> str:
        raise NotImplementedError

    def run(self, **kwargs: object) -> T:
        user_prompt = self.build_user_prompt(**kwargs)
        system = f"{self.system_prompt}\n\n{schema_instruction(self.response_model)}"
        messages = build_messages(system, user_prompt)
        return self.provider.call_structured(
            messages, self.response_model, profile=self.profile
        )
