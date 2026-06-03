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
    assert len(raid.actions) >= 2


def test_raid_items_link_to_wbs(wbs: WBS) -> None:
    raid = RAIDLog.model_validate(
        {
            "risks": [
                {"id": "R1", "title": "Risk", "wbs_links": ["1.1"]},
                {"id": "R2", "title": "Risk 2", "wbs_links": ["2.1"]},
                {"id": "R3", "title": "Risk 3", "wbs_links": ["3.1"]},
            ],
            "actions": [
                {"id": "A1", "title": "Action 1", "wbs_links": ["1.0"]},
                {"id": "A2", "title": "Action 2", "wbs_links": ["2.0"]},
            ],
        }
    )
    wbs_codes = {wp.wbs_code for wp in wbs.work_packages}
    for item in raid.risks + raid.actions:
        for ref in item.wbs_links:
            assert ref in wbs_codes


def test_raid_legacy_items_migrate() -> None:
    raid = RAIDLog.model_validate(
        {
            "items": [
                {"id": "R1", "category": "R", "title": "R1"},
                {"id": "R2", "category": "R", "title": "R2"},
                {"id": "R3", "category": "R", "title": "R3"},
                {"id": "A1", "category": "A", "title": "A1"},
                {"id": "A2", "category": "A", "title": "A2"},
            ]
        }
    )
    assert len(raid.risks) == 3
    assert len(raid.actions) == 2


def test_raid_markdown_render(parsed_brief: ParsedBrief) -> None:
    raid = RAIDLog.model_validate(
        {
            "risks": [
                {
                    "id": "R1",
                    "title": "Test risk",
                    "priority": "High",
                    "probability": "High",
                    "wbs_links": ["1.0"],
                    "mitigation": "Monitor",
                },
                {"id": "R2", "title": "Risk 2", "wbs_links": ["1.0"]},
                {"id": "R3", "title": "Risk 3", "wbs_links": ["1.0"]},
            ],
            "actions": [
                {"id": "A1", "title": "Action 1", "wbs_links": ["1.0"]},
                {"id": "A2", "title": "Action 2", "wbs_links": ["2.0"]},
            ],
        }
    )
    md = render_raid_markdown(raid, parsed_brief)
    assert "RAID Log" in md
    assert "R1" in md
    assert "Owner Side" in md
    assert "## Actions" in md
