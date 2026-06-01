"""Per-artifact version counters and dependency-based staleness tracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workplan_agent.models.session import WorkplanSession

REVISION_ARTIFACTS = ("wbs", "raid", "stakeholder", "status")

DEPENDENCIES: dict[str, list[str]] = {
    "raid": ["wbs"],
    "stakeholder": ["wbs", "raid"],
    "status": ["wbs", "raid"],
    "quality_gates": ["wbs", "raid", "stakeholder", "status"],
}

ARTIFACT_LABELS: dict[str, str] = {
    "wbs": "WBS",
    "raid": "RAID",
    "stakeholder": "Stakeholder Map",
    "status": "Status Report",
    "quality_gates": "Quality Gates",
}


def init_after_generation(session: WorkplanSession) -> None:
    """Set all artifact versions to 1 after initial generation."""
    session.artifact_versions = {
        "wbs": 1,
        "raid": 1,
        "stakeholder": 1,
        "status": 1,
        "quality_gates": 1,
    }
    session.artifact_based_on = {
        "wbs": {},
        "raid": {"wbs": 1},
        "stakeholder": {"wbs": 1, "raid": 1},
        "status": {"wbs": 1, "raid": 1},
        "quality_gates": {
            "wbs": 1,
            "raid": 1,
            "stakeholder": 1,
            "status": 1,
        },
    }


def _current_upstream(session: WorkplanSession) -> dict[str, int]:
    return {key: session.artifact_versions.get(key, 0) for key in REVISION_ARTIFACTS}


def _bump(session: WorkplanSession, artifact: str) -> int:
    next_version = session.artifact_versions.get(artifact, 0) + 1
    session.artifact_versions[artifact] = next_version
    return next_version


def after_revision(
    session: WorkplanSession,
    target: str,
    upstream_snapshot: dict[str, int],
) -> None:
    """Record a version bump after a single-artifact revision."""
    if target == "wbs":
        _bump(session, "wbs")
        return

    if target == "raid":
        _bump(session, "raid")
        session.artifact_based_on["raid"] = {
            "wbs": upstream_snapshot.get("wbs", session.artifact_versions.get("wbs", 0)),
        }
        return

    if target == "stakeholder":
        _bump(session, "stakeholder")
        session.artifact_based_on["stakeholder"] = {
            "wbs": upstream_snapshot.get("wbs", session.artifact_versions.get("wbs", 0)),
            "raid": upstream_snapshot.get("raid", session.artifact_versions.get("raid", 0)),
        }
        return

    if target == "status":
        _bump(session, "status")
        session.artifact_based_on["status"] = {
            "wbs": upstream_snapshot.get("wbs", session.artifact_versions.get("wbs", 0)),
            "raid": upstream_snapshot.get("raid", session.artifact_versions.get("raid", 0)),
        }


def after_multi_revision(
    session: WorkplanSession,
    targets: list[str],
    upstream_snapshot: dict[str, int],
) -> None:
    for target in targets:
        after_revision(session, target, upstream_snapshot)


def after_quality_check(session: WorkplanSession) -> None:
    _bump(session, "quality_gates")
    upstream = _current_upstream(session)
    session.artifact_based_on["quality_gates"] = upstream


def compute_stale_artifacts(session: WorkplanSession) -> dict[str, list[str]]:
    """Return artifacts that may be outdated vs upstream dependencies."""
    stale: dict[str, list[str]] = {}
    for artifact, deps in DEPENDENCIES.items():
        based_on = session.artifact_based_on.get(artifact, {})
        behind: list[str] = []
        for dep in deps:
            current = session.artifact_versions.get(dep, 0)
            recorded = based_on.get(dep, 0)
            if current > 0 and recorded < current:
                behind.append(dep)
        if behind:
            stale[artifact] = behind
    return stale
