import pytest

from workplan_agent.agents.raci_generator import RaciMatrixGeneratorAgent
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, WBS_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix, RaciLetter
from workplan_agent.render import render_raci_markdown


@pytest.fixture
def parsed_brief() -> ParsedBrief:
    return ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)


@pytest.fixture
def wbs() -> WBS:
    return WBS.model_validate(WBS_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_raci_generator_returns_valid_matrix(
    provider: MockLLMProvider, parsed_brief: ParsedBrief, wbs: WBS
) -> None:
    agent = RaciMatrixGeneratorAgent(provider)
    matrix = agent.run(parsed_brief=parsed_brief, wbs=wbs)
    assert isinstance(matrix, RaciMatrix)
    assert len(matrix.roles) >= 2
    assert len(matrix.rows) >= 2
    for row in matrix.rows:
        assert row.activity
        assert len(row.assignments) == len(matrix.roles)


def test_raci_markdown_render(parsed_brief: ParsedBrief) -> None:
    matrix = RaciMatrix.model_validate(
        {
            "roles": ["Sponsor", "Delivery Lead"],
            "rows": [
                {
                    "wbs_code": "1.1.1",
                    "activity": "Discovery workshops",
                    "assignments": {
                        "Sponsor": "A",
                        "Delivery Lead": "R",
                    },
                }
            ],
        }
    )
    md = render_raci_markdown(matrix, parsed_brief)
    assert "WBS Code | Task / Activity | Sponsor | Delivery Lead" in md
    assert "1.1.1" in md
    assert "Discovery workshops" in md
    assert RaciLetter.ACCOUNTABLE.value in md
