import pytest

from workplan_agent.agents.revision import RevisionAgent, RevisionTarget
from workplan_agent.llm.fixtures import (
    PARSED_BRIEF_FIXTURE,
    RAID_FIXTURE,
    WBS_FIXTURE,
    STAKEHOLDER_MAP_FIXTURE,
    STATUS_REPORT_FIXTURE,
)
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.stakeholder import StakeholderMap
from workplan_agent.models.status_report import WeeklyStatusReport


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
def stakeholder_map() -> StakeholderMap:
    return StakeholderMap.model_validate(STAKEHOLDER_MAP_FIXTURE)


@pytest.fixture
def status_report() -> WeeklyStatusReport:
    return WeeklyStatusReport.model_validate(STATUS_REPORT_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_revision_stakeholder_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
    stakeholder_map: StakeholderMap,
    status_report: WeeklyStatusReport,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        stakeholder_map=stakeholder_map,
        status_report=status_report,
        feedback="Add stakeholder John Doe as PM.",
        target=RevisionTarget.STAKEHOLDER,
    )
    assert result.stakeholder_map is not None
    assert result.status_report is None
    assert result.wbs is None
    assert result.raid is None


def test_revision_status_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
    stakeholder_map: StakeholderMap,
    status_report: WeeklyStatusReport,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        stakeholder_map=stakeholder_map,
        status_report=status_report,
        feedback="Change overall project status to Red.",
        target=RevisionTarget.STATUS,
    )
    assert result.status_report is not None
    assert result.stakeholder_map is None
    assert result.wbs is None
    assert result.raid is None

