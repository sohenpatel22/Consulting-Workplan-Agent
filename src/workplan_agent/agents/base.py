from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from workplan_agent.config import ProfileName, get_settings
from workplan_agent.llm.base import LLMProvider, build_cached_messages, build_messages
from workplan_agent.llm.caching import ContentBlock, LLMMessage

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    system_prompt: str = ""
    profile: ProfileName = "balanced"
    use_prompt_cache: bool = True

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    @property
    @abstractmethod
    def response_model(self) -> type[T]: ...

    def build_user_prompt(self, **kwargs: object) -> str:
        raise NotImplementedError

    def build_system_blocks(self) -> list[ContentBlock] | None:
        return None

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock] | None:
        return None

    def build_messages(self, **kwargs: object) -> list[LLMMessage]:
        if self._caching_enabled():
            system_blocks = self.build_system_blocks()
            user_blocks = self.build_user_blocks(**kwargs)
            if system_blocks is not None and user_blocks is not None:
                return build_cached_messages(system_blocks, user_blocks)

        from workplan_agent.llm.base import schema_instruction

        system = f"{self.system_prompt}\n\n{schema_instruction(self.response_model)}"
        return build_messages(system, self.build_user_prompt(**kwargs))

    def _caching_enabled(self) -> bool:
        return self.use_prompt_cache and get_settings().enable_prompt_cache

    def run(self, **kwargs: object) -> T:
        messages = self.build_messages(**kwargs)
        return self.provider.call_structured(
            messages, self.response_model, profile=self.profile
        )
