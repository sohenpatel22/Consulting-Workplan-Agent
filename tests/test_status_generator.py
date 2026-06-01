import pytest

from workplan_agent.agents.status_generator import StatusReportGeneratorAgent
from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE, WBS_FIXTURE, RAID_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.render import render_status_markdown


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


def test_status_generator_returns_valid_report(
    provider: MockLLMProvider, parsed_brief: ParsedBrief, wbs: WBS, raid: RAIDLog
) -> None:
    agent = StatusReportGeneratorAgent(provider)
    report = agent.run(parsed_brief=parsed_brief, wbs=wbs, raid=raid)
    assert isinstance(report, WeeklyStatusReport)
    assert report.project_title
    assert report.overall_status in ["Green", "Amber", "Red"]
    assert len(report.milestones) >= 2


def test_status_markdown_render(parsed_brief: ParsedBrief) -> None:
    report = WeeklyStatusReport.model_validate(
        {
            "project_title": "Modernization",
            "client_name": "Northwind",
            "reporting_period": "Week 1",
            "overall_status": "Green",
            "executive_summary": "Ongoing progress",
            "key_achievements": ["Completed Kickoff"],
            "planned_activities": ["Workshops"],
            "milestones": [
                {
                    "milestone": "Kickoff",
                    "target_date": "2026-06-02",
                    "status": "Completed"
                }
            ]
        }
    )
    md = render_status_markdown(report, parsed_brief)
    assert "Weekly Status Report" in md
    assert "Modernization" in md
    assert "Kickoff" in md
