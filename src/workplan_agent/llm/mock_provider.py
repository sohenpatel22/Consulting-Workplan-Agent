from typing import TypeVar

from pydantic import BaseModel

from workplan_agent.config import ProfileName
from workplan_agent.llm.fixtures import FIXTURES
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider:
    """Returns deterministic fixture data for offline tests and demos."""

    def __init__(self) -> None:
        self.call_log: list[tuple[type[BaseModel], ProfileName]] = []

    def call_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        profile: ProfileName = "balanced",
    ) -> T:
        self.call_log.append((response_model, profile))
        fixture = FIXTURES.get(response_model)
        if fixture is None:
            raise ValueError(f"No mock fixture for {response_model.__name__}")
        return response_model.model_validate(fixture)

    @staticmethod
    def for_profile(profile: ProfileName) -> "MockLLMProvider":
        return MockLLMProvider()
