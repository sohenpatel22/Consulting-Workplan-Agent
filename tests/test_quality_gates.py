import pytest

from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.models.session import WorkplanSession
from workplan_agent.render import generate_quality_gates, render_quality_gates_markdown
from workplan_agent.llm.fixtures import (
    PARSED_BRIEF_FIXTURE,
    RAID_FIXTURE,
    WBS_FIXTURE,
    RACI_MATRIX_FIXTURE,
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
        raci_matrix=RaciMatrix.model_validate(RACI_MATRIX_FIXTURE),
        status_report=WeeklyStatusReport.model_validate(STATUS_REPORT_FIXTURE),
    )


def test_generate_quality_gates_passed(session: WorkplanSession) -> None:
    gates = generate_quality_gates(session)
    assert len(gates.items) == 13
    
    # Assert specific checks
    wbs_hier = next(i for i in gates.items if i.title == "Hierarchical Code Validity")
    assert wbs_hier.passed is True
    
    wbs_deliv = next(i for i in gates.items if i.title == "Deliverable Completeness")
    assert wbs_deliv.passed is True

    wbs_dep = next(i for i in gates.items if i.title == "Dependency Alignment")
    assert wbs_dep.passed is True

    raid_map = next(i for i in gates.items if i.title == "WBS Link Mapping")
    assert raid_map.passed is True

    raid_owner = next(i for i in gates.items if i.title == "Owner Assignment")
    assert raid_owner.passed is True

    raci_align = next(i for i in gates.items if i.title == "Accountability Coverage")
    assert raci_align.passed is True

    raci_coverage = next(i for i in gates.items if i.title == "RACI Task Coverage")
    assert raci_coverage.passed is True

    raci_role = next(i for i in gates.items if i.title == "RACI Role Alignment")
    assert raci_role.passed is True


def test_generate_quality_gates_failed_hier_code(session: WorkplanSession) -> None:
    # Break WBS parent linkage
    assert session.wbs is not None
    session.wbs.work_packages[1].parent_wbs_code = "99.0"  # Invalid parent
    
    gates = generate_quality_gates(session)
    wbs_hier = next(i for i in gates.items if i.title == "Hierarchical Code Validity")
    assert wbs_hier.passed is False
    assert "99.0" in wbs_hier.message


def test_generate_quality_gates_failed_deliverable_completeness(session: WorkplanSession) -> None:
    assert session.wbs is not None
    # 1.1.1 is a leaf package
    session.wbs.work_packages[2].key_deliverable = ""
    
    gates = generate_quality_gates(session)
    wbs_deliv = next(i for i in gates.items if i.title == "Deliverable Completeness")
    assert wbs_deliv.passed is False
    assert "1.1.1" in wbs_deliv.message


def test_generate_quality_gates_failed_dependency_alignment(session: WorkplanSession) -> None:
    assert session.wbs is not None
    # Create a dependency cycle: 1.1 depends on 1.2, and 1.2 depends on 1.1
    session.wbs.work_packages[1].dependencies = ["1.2"]
    session.wbs.work_packages[3].dependencies = ["1.1"]
    
    gates = generate_quality_gates(session)
    wbs_dep = next(i for i in gates.items if i.title == "Dependency Alignment")
    assert wbs_dep.passed is False
    assert "Dependency loop detected" in wbs_dep.message


def test_generate_quality_gates_failed_raid_links(session: WorkplanSession) -> None:
    # Break RAID mapping links
    assert session.raid is not None
    session.raid.risks[0].wbs_links = ["9.9"]  # Invalid link
    
    gates = generate_quality_gates(session)
    raid_map = next(i for i in gates.items if i.title == "WBS Link Mapping")
    assert raid_map.passed is False
    assert "9.9" in raid_map.message


def test_generate_quality_gates_failed_raid_owner_assignment(session: WorkplanSession) -> None:
    assert session.raid is not None
    session.raid.risks[0].owner = "TBD"
    
    gates = generate_quality_gates(session)
    raid_owner = next(i for i in gates.items if i.title == "Owner Assignment")
    assert raid_owner.passed is False
    assert "Risk R1" in raid_owner.message


def test_generate_quality_gates_failed_raci_task_coverage(session: WorkplanSession) -> None:
    assert session.raci_matrix is not None
    # Remove 1.1 row from RACI
    session.raci_matrix.rows = [row for row in session.raci_matrix.rows if row.wbs_code != "1.1"]
    
    gates = generate_quality_gates(session)
    raci_coverage = next(i for i in gates.items if i.title == "RACI Task Coverage")
    assert raci_coverage.passed is False
    assert "1.1" in raci_coverage.message


def test_generate_quality_gates_failed_raci_role_alignment(session: WorkplanSession) -> None:
    assert session.wbs is not None
    assert session.raci_matrix is not None
    # WBS owner is Deloitte Delivery Lead, RACI assign is Informed (I) instead of R or A
    row = next(r for r in session.raci_matrix.rows if r.wbs_code == "1.1")
    row.assignments["Deloitte Delivery Lead"] = "I"
    
    gates = generate_quality_gates(session)
    raci_role = next(i for i in gates.items if i.title == "RACI Role Alignment")
    assert raci_role.passed is False
    assert "lacks R or A in RACI" in raci_role.message


def test_render_quality_gates_markdown(session: WorkplanSession) -> None:
    gates = generate_quality_gates(session)
    md = render_quality_gates_markdown(gates, session.parsed_brief)
    
    assert "# Quality Gates & Verification Checklist" in md
    assert "## WBS Quality Gates" in md
    assert "## RAID Quality Gates" in md
    assert "Hierarchical Code Validity" in md
