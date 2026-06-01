import pytest

from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.stakeholder import StakeholderMap
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.models.session import WorkplanSession
from workplan_agent.render import generate_quality_gates, render_quality_gates_markdown
from workplan_agent.llm.fixtures import (
    PARSED_BRIEF_FIXTURE,
    RAID_FIXTURE,
    WBS_FIXTURE,
    STAKEHOLDER_MAP_FIXTURE,
    STATUS_REPORT_FIXTURE,
)


@pytest.fixture
def session() -> WorkplanSession:
    return WorkplanSession(
        session_id="test_id",
        brief_path="test_brief.md",
        parsed_brief=ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE),
        wbs=WBS.model_validate(WBS_FIXTURE),
        raid=RAIDLog.model_validate(RAID_FIXTURE),
        stakeholder_map=StakeholderMap.model_validate(STAKEHOLDER_MAP_FIXTURE),
        status_report=WeeklyStatusReport.model_validate(STATUS_REPORT_FIXTURE),
    )


def test_generate_quality_gates_passed(session: WorkplanSession) -> None:
    gates = generate_quality_gates(session)
    assert len(gates.items) == 8
    
    # Assert specific checks
    wbs_hier = next(i for i in gates.items if i.title == "Hierarchical Code Validity")
    assert wbs_hier.passed is True
    
    raid_map = next(i for i in gates.items if i.title == "WBS Link Mapping")
    assert raid_map.passed is True

    sponsor_align = next(i for i in gates.items if i.title == "Sponsor Strategy Alignment")
    assert sponsor_align.passed is True


def test_generate_quality_gates_failed_hier_code(session: WorkplanSession) -> None:
    # Break WBS parent linkage
    assert session.wbs is not None
    session.wbs.work_packages[1].parent_wbs_code = "99.0"  # Invalid parent
    
    gates = generate_quality_gates(session)
    wbs_hier = next(i for i in gates.items if i.title == "Hierarchical Code Validity")
    assert wbs_hier.passed is False
    assert "99.0" in wbs_hier.message


def test_generate_quality_gates_failed_raid_links(session: WorkplanSession) -> None:
    # Break RAID mapping links
    assert session.raid is not None
    session.raid.risks[0].wbs_links = ["9.9"]  # Invalid link
    
    gates = generate_quality_gates(session)
    raid_map = next(i for i in gates.items if i.title == "WBS Link Mapping")
    assert raid_map.passed is False
    assert "9.9" in raid_map.message


def test_render_quality_gates_markdown(session: WorkplanSession) -> None:
    gates = generate_quality_gates(session)
    md = render_quality_gates_markdown(gates, session.parsed_brief)
    
    assert "# Quality Gates & Verification Checklist" in md
    assert "## WBS Quality Gates" in md
    assert "## RAID Quality Gates" in md
    assert "Hierarchical Code Validity" in md
