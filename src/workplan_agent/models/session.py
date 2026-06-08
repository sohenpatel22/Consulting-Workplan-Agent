from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.models.quality_gates import QualityGates


class SessionStatus(str, Enum):
    PARSED = "parsed"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    WBS_GENERATED = "wbs_generated"
    RAID_GENERATED = "raid_generated"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"


class ArtifactVersion(BaseModel):
    version: int
    label: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    wbs: WBS | None = None
    raid: RAIDLog | None = None
    raci_matrix: RaciMatrix | None = None
    status_report: WeeklyStatusReport | None = None
    quality_gates: QualityGates | None = None


class WorkplanSession(BaseModel):
    session_id: str
    brief_path: str
    parsed_brief: ParsedBrief | None = None
    wbs: WBS | None = None
    raid: RAIDLog | None = None
    raci_matrix: RaciMatrix | None = None
    status_report: WeeklyStatusReport | None = None
    quality_gates: QualityGates | None = None
    versions: list[ArtifactVersion] = Field(default_factory=list)
    artifact_versions: dict[str, int] = Field(default_factory=dict)
    artifact_based_on: dict[str, dict[str, int]] = Field(default_factory=dict)
    status: SessionStatus = SessionStatus.PARSED
    revision_count: int = 0

    def snapshot(self, label: str) -> None:
        version_num = len(self.versions) + 1
        self.versions.append(
            ArtifactVersion(
                version=version_num,
                label=label,
                wbs=self.wbs,
                raid=self.raid,
                raci_matrix=self.raci_matrix,
                status_report=self.status_report,
                quality_gates=self.quality_gates,
            )
        )
