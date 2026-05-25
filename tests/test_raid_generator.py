import pytest

from workplan_agent.agents.raid_generator import RAIDGeneratorAgent
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, WBS_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.render import render_raid_markdown


@pytest.fixture
def parsed_brief() -> ParsedBrief:
    return ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)


@pytest.fixture
def wbs() -> WBS:
    return WBS.model_validate(WBS_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_raid_generator_returns_valid_raid(
    provider: MockLLMProvider, parsed_brief: ParsedBrief, wbs: WBS
) -> None:
    agent = RAIDGeneratorAgent(provider)
    raid = agent.run(parsed_brief=parsed_brief, wbs=wbs)
    assert isinstance(raid, RAIDLog)
    assert len(raid.risks) >= 3
    assert len(raid.assumptions) >= 2


def test_raid_items_link_to_wbs(wbs: WBS) -> None:
    raid = RAIDLog.model_validate(
        {
            "items": [
                {
                    "id": "R1",
                    "category": "R",
                    "title": "Risk",
                    "related_wbs_ids": ["1.1"],
                },
                {
                    "id": "R2",
                    "category": "R",
                    "title": "Risk 2",
                    "related_wbs_ids": ["2.1"],
                },
                {
                    "id": "R3",
                    "category": "R",
                    "title": "Risk 3",
                    "related_wbs_ids": ["3.1"],
                },
                {"id": "A1", "category": "A", "title": "Assumption 1"},
                {"id": "A2", "category": "A", "title": "Assumption 2"},
            ]
        }
    )
    wbs_ids = {wp.id for wp in wbs.work_packages}
    for item in raid.items:
        for ref in item.related_wbs_ids:
            assert ref in wbs_ids


def test_raid_markdown_render(parsed_brief: ParsedBrief) -> None:
    raid = RAIDLog.model_validate(
        {
            "items": [
                {
                    "id": "R1",
                    "category": "R",
                    "title": "Test risk",
                    "severity": "High",
                    "related_wbs_ids": ["1.0"],
                    "mitigation": "Monitor",
                },
                {
                    "id": "R2",
                    "category": "R",
                    "title": "Risk 2",
                    "related_wbs_ids": ["1.0"],
                },
                {
                    "id": "R3",
                    "category": "R",
                    "title": "Risk 3",
                    "related_wbs_ids": ["1.0"],
                },
                {"id": "A1", "category": "A", "title": "Assumption 1"},
                {"id": "A2", "category": "A", "title": "Assumption 2"},
            ]
        }
    )
    md = render_raid_markdown(raid, parsed_brief)
    assert "RAID Log" in md
    assert "R1" in md
    assert "Assumptions" in md
