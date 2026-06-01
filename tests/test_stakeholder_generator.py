import pytest

from workplan_agent.agents.stakeholder_generator import StakeholderMapGeneratorAgent
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, WBS_FIXTURE, RAID_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.stakeholder import StakeholderMap
from workplan_agent.render import render_stakeholder_markdown


@pytest.fixture
def parsed_brief() -> ParsedBrief:
    return ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)


@pytest.fixture
def wbs() -> WBS:
    return WBS.model_validate(WBS_FIXTURE)


@pytest.fixture
def raid() -> RAIDLog:
    return RAIDLog.model_validate(RAID_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_stakeholder_generator_returns_valid_map(
    provider: MockLLMProvider, parsed_brief: ParsedBrief, wbs: WBS, raid: RAIDLog
) -> None:
    agent = StakeholderMapGeneratorAgent(provider)
    st_map = agent.run(parsed_brief=parsed_brief, wbs=wbs, raid=raid)
    assert isinstance(st_map, StakeholderMap)
    assert len(st_map.stakeholders) >= 2
    for stakeholder in st_map.stakeholders:
        assert stakeholder.name
        assert stakeholder.role


def test_stakeholder_markdown_render(parsed_brief: ParsedBrief) -> None:
    st_map = StakeholderMap.model_validate(
        {
            "stakeholders": [
                {
                    "name": "Elena Vasquez",
                    "role": "CMO",
                    "influence": "High",
                    "interest": "High",
                    "engagement_strategy": "Manage Closely",
                    "key_concerns": "Campaign launch speed",
                    "communication_channel": "Monthly dashboard",
                    "frequency": "Monthly",
                }
            ]
        }
    )
    md = render_stakeholder_markdown(st_map, parsed_brief)
    assert "Stakeholder Map" in md
    assert "Elena Vasquez" in md
    assert "CMO" in md
