import pytest

from workplan_agent.agents.revision import RevisionAgent, RevisionTarget
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, RAID_FIXTURE, WBS_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS


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


def test_revision_wbs_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        feedback="Add a UAT work package under Build.",
        target=RevisionTarget.WBS,
    )
    assert result.wbs is not None
    assert result.raid is None


def test_revision_raid_only(
    provider: MockLLMProvider,
    parsed_brief: ParsedBrief,
    wbs: WBS,
    raid: RAIDLog,
) -> None:
    agent = RevisionAgent(provider)
    result = agent.run(
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        feedback="Add a GDPR compliance risk.",
        target=RevisionTarget.RAID,
    )
    assert result.wbs is None
    assert result.raid is not None

