import pytest

from workplan_agent.agents.wbs_generator import WBSGeneratorAgent
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.render import render_wbs_markdown


@pytest.fixture
def parsed_brief() -> ParsedBrief:
    return ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_wbs_generator_returns_valid_wbs(
    provider: MockLLMProvider, parsed_brief: ParsedBrief
) -> None:
    agent = WBSGeneratorAgent(provider)
    wbs = agent.run(parsed_brief=parsed_brief)
    assert isinstance(wbs, WBS)
    assert len(wbs.work_packages) >= 3
    l1 = [wp for wp in wbs.work_packages if wp.level == 1]
    assert len(l1) >= 3


def test_wbs_markdown_render(parsed_brief: ParsedBrief) -> None:
    wbs = WBS.model_validate(
        {
            "phases": ["Discovery"],
            "work_packages": [
                {
                    "id": "1.0",
                    "level": 1,
                    "name": "Discovery",
                    "description": "Assess",
                    "deliverables": ["Report"],
                    "owner_role": "EM",
                    "estimated_duration": "2w",
                    "dependencies": [],
                },
                {
                    "id": "1.1",
                    "level": 2,
                    "parent_id": "1.0",
                    "name": "Interviews",
                    "description": "Talk to stakeholders",
                    "deliverables": ["Notes"],
                    "owner_role": "BA",
                    "estimated_duration": "1w",
                    "dependencies": [],
                },
                {
                    "id": "1.2",
                    "level": 2,
                    "parent_id": "1.0",
                    "name": "Inventory",
                    "description": "Catalog sources",
                    "deliverables": ["List"],
                    "owner_role": "DA",
                    "estimated_duration": "1w",
                    "dependencies": [],
                },
                {
                    "id": "2.0",
                    "level": 1,
                    "name": "Design",
                    "description": "Design",
                    "deliverables": ["Doc"],
                    "owner_role": "SA",
                    "estimated_duration": "2w",
                    "dependencies": ["1.0"],
                },
                {
                    "id": "2.1",
                    "level": 2,
                    "parent_id": "2.0",
                    "name": "Architecture",
                    "description": "Arch",
                    "deliverables": ["Diagram"],
                    "owner_role": "SA",
                    "estimated_duration": "1w",
                    "dependencies": [],
                },
                {
                    "id": "2.2",
                    "level": 2,
                    "parent_id": "2.0",
                    "name": "Integration",
                    "description": "Integrate",
                    "deliverables": ["Spec"],
                    "owner_role": "DE",
                    "estimated_duration": "1w",
                    "dependencies": [],
                },
                {
                    "id": "3.0",
                    "level": 1,
                    "name": "Build",
                    "description": "Build",
                    "deliverables": ["MVP"],
                    "owner_role": "TL",
                    "estimated_duration": "4w",
                    "dependencies": ["2.0"],
                },
                {
                    "id": "3.1",
                    "level": 2,
                    "parent_id": "3.0",
                    "name": "Pipelines",
                    "description": "Build pipelines",
                    "deliverables": ["Deploy"],
                    "owner_role": "DE",
                    "estimated_duration": "2w",
                    "dependencies": [],
                },
                {
                    "id": "3.2",
                    "level": 2,
                    "parent_id": "3.0",
                    "name": "Identity",
                    "description": "Dedup",
                    "deliverables": ["Module"],
                    "owner_role": "DE",
                    "estimated_duration": "2w",
                    "dependencies": [],
                },
            ],
        }
    )
    md = render_wbs_markdown(wbs, parsed_brief)
    assert "Work Breakdown Structure" in md
    assert "Northwind Retail Group" in md
    assert "1.0" in md
