import pytest

from workplan_agent.agents.revision import RevisionAgent, RevisionTarget
from workplan_agent.llm.fixtures import (
    PARSED_BRIEF_FIXTURE,
    RAID_FIXTURE,
    WBS_FIXTURE,
    RACI_MATRIX_FIXTURE,
    STATUS_REPORT_FIXTURE,
)
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
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
def raci_matrix() -> RaciMatrix:
    return RaciMatrix.model_validate(RACI_MATRIX_FIXTURE)


@pytest.fixture
def status_report() -> WeeklyStatusReport:
    return WeeklyStatusReport.model_validate(STATUS_REPORT_FIXTURE)


@pytest.fixture
def provider() -> MockLLMProvider:
    return MockLLMProvider()


def test_revision_raci_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
    raci_matrix: RaciMatrix,
    status_report: WeeklyStatusReport,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        raci_matrix=raci_matrix,
        status_report=status_report,
        feedback="Add a new RACI row for change management.",
        target=RevisionTarget.RACI,
    )
    assert result.raci_matrix is not None
    assert result.status_report is None
    assert result.wbs is None
    assert result.raid is None


def test_revision_status_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
    raci_matrix: RaciMatrix,
    status_report: WeeklyStatusReport,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        raci_matrix=raci_matrix,
        status_report=status_report,
        feedback="Change overall project status to Red.",
        target=RevisionTarget.STATUS,
    )
    assert result.status_report is not None
    assert result.raci_matrix is None
    assert result.wbs is None
    assert result.raid is None
