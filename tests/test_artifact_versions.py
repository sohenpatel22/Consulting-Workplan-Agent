from workplan_agent.models.artifact_versions import (
    after_quality_check,
    after_revision,
    compute_stale_artifacts,
    init_after_generation,
)
from workplan_agent.models.session import WorkplanSession


def test_init_and_stale_after_wbs_revision() -> None:
    session = WorkplanSession(session_id="t1", brief_path="test")
    init_after_generation(session)

    upstream = {"wbs": 1, "raid": 1, "stakeholder": 1, "status": 1}
    after_revision(session, "wbs", upstream)

    assert session.artifact_versions["wbs"] == 2
    stale = compute_stale_artifacts(session)
    assert "raid" in stale
    assert stale["raid"] == ["wbs"]
    assert "stakeholder" in stale
    assert "quality_gates" in stale


def test_raid_revision_clears_own_stale_flag() -> None:
    session = WorkplanSession(session_id="t2", brief_path="test")
    init_after_generation(session)

    upstream = {"wbs": 1, "raid": 1, "stakeholder": 1, "status": 1}
    after_revision(session, "wbs", upstream)
    after_revision(session, "raid", {"wbs": 2, "raid": 1, "stakeholder": 1, "status": 1})

    stale = compute_stale_artifacts(session)
    assert "raid" not in stale
    assert session.artifact_based_on["raid"]["wbs"] == 2


def test_quality_check_resets_gate_staleness() -> None:
    session = WorkplanSession(session_id="t3", brief_path="test")
    init_after_generation(session)
    after_revision(session, "wbs", {"wbs": 1, "raid": 1, "stakeholder": 1, "status": 1})

    after_quality_check(session)
    stale = compute_stale_artifacts(session)
    assert "quality_gates" not in stale
    assert session.artifact_versions["quality_gates"] == 2
