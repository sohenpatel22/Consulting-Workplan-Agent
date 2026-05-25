import pytest

from workplan_agent.agents.brief_parser import BriefParserAgent
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_brief_parser_returns_valid_brief(provider: MockLLMProvider) -> None:
    agent = BriefParserAgent(provider)
    result = agent.run_and_validate("Sample brief text about Northwind CDP project.")
    assert isinstance(result, ParsedBrief)
    assert result.client_name == "Northwind Retail Group"
    assert len(result.objectives) >= 1
    assert len(result.scope_in) >= 1


def test_brief_parser_records_llm_call(provider: MockLLMProvider) -> None:
    agent = BriefParserAgent(provider)
    agent.run(brief_text="Some brief")
    assert len(provider.call_log) == 1
    model, profile = provider.call_log[0]
    assert model is ParsedBrief
    assert profile == "balanced"


def test_brief_validation_fails_on_empty_objectives() -> None:
    brief = ParsedBrief(
        client_name="Test",
        project_title="Test Project",
        objectives=[],
        scope_in=["item"],
    )
    errors = brief.validate_required()
    assert any("objective" in e.lower() for e in errors)
