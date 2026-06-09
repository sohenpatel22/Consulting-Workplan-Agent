from enum import Enum

from pydantic import BaseModel

from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.prompts import (
    REVISION_RAID_USER,
    REVISION_SYSTEM,
    REVISION_WBS_USER,
    REVISION_RACI_SYSTEM,
    REVISION_RACI_USER,
    REVISION_STATUS_SYSTEM,
    REVISION_STATUS_USER,
    revision_system_blocks,
    revision_user_blocks,
)


class RevisionTarget(str, Enum):
    WBS = "wbs"
    RAID = "raid"
    RACI = "raci"
    STATUS = "status"


class RevisionResult(BaseModel):
    wbs: WBS | None = None
    raid: RAIDLog | None = None
    raci_matrix: RaciMatrix | None = None
    status_report: WeeklyStatusReport | None = None


class RevisionAgent:
    def __init__(self, provider) -> None:
        self.provider = provider
        self._wbs_agent = _WBSRevisionHelper(provider)
        self._raid_agent = _RAIDRevisionHelper(provider)
        self._raci_agent = _RaciRevisionHelper(provider)
        self._status_agent = _StatusRevisionHelper(provider)

    def run(
        self,
        parsed_brief: ParsedBrief,
        wbs: WBS,
        raid: RAIDLog,
        feedback: str,
        target: RevisionTarget,
        raci_matrix: RaciMatrix | None = None,
        status_report: WeeklyStatusReport | None = None,
    ) -> RevisionResult:
        result = RevisionResult()
        brief_json = parsed_brief.model_dump_json(indent=2)

        if target == RevisionTarget.WBS:
            result.wbs = self._wbs_agent.run(
                parsed_brief_json=brief_json,
                wbs=wbs,
                raid=raid,
                feedback=feedback,
                raci_matrix=raci_matrix,
                status_report=status_report,
            )

        elif target == RevisionTarget.RAID:
            result.raid = self._raid_agent.run(
                parsed_brief_json=brief_json,
                wbs=wbs,
                raid=raid,
                feedback=feedback,
                raci_matrix=raci_matrix,
                status_report=status_report,
            )

        elif target == RevisionTarget.RACI:
            if raci_matrix is None:
                raise ValueError("raci_matrix is required for RACI revision")
            result.raci_matrix = self._raci_agent.run(
                parsed_brief_json=brief_json,
                wbs=wbs,
                raci_matrix=raci_matrix,
                feedback=feedback,
            )

        elif target == RevisionTarget.STATUS:
            if status_report is None:
                raise ValueError("status_report is required for status report revision")
            result.status_report = self._status_agent.run(
                parsed_brief_json=brief_json,
                status_report=status_report,
                feedback=feedback,
            )

        return result


class _WBSRevisionHelper(BaseAgent[WBS]):
    system_prompt = REVISION_SYSTEM

    @property
    def response_model(self) -> type[WBS]:
        return WBS

    def build_user_prompt(self, **kwargs: object) -> str:
        return REVISION_WBS_USER.format(
            parsed_brief_json=kwargs["parsed_brief_json"],
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=kwargs["feedback"],
        )

    def build_system_blocks(self) -> list[ContentBlock]:
        return revision_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        raci_matrix = kwargs.get("raci_matrix")
        status_report = kwargs.get("status_report")
        raci_matrix_json = (
            raci_matrix.model_dump_json(indent=2)
            if isinstance(raci_matrix, RaciMatrix)
            else "{}"
        )
        status_report_json = (
            status_report.model_dump_json(indent=2)
            if isinstance(status_report, WeeklyStatusReport)
            else "{}"
        )
        return revision_user_blocks(
            task="Revise the WBS based on reviewer feedback.",
            parsed_brief_json=str(kwargs["parsed_brief_json"]),
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=str(kwargs["feedback"]),
            raci_matrix_json=raci_matrix_json,
            status_report_json=status_report_json,
        )


class _RAIDRevisionHelper(BaseAgent[RAIDLog]):
    system_prompt = REVISION_SYSTEM

    @property
    def response_model(self) -> type[RAIDLog]:
        return RAIDLog

    def build_user_prompt(self, **kwargs: object) -> str:
        return REVISION_RAID_USER.format(
            parsed_brief_json=kwargs["parsed_brief_json"],
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=kwargs["feedback"],
        )

    def build_system_blocks(self) -> list[ContentBlock]:
        return revision_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        raci_matrix = kwargs.get("raci_matrix")
        status_report = kwargs.get("status_report")
        raci_matrix_json = (
            raci_matrix.model_dump_json(indent=2)
            if isinstance(raci_matrix, RaciMatrix)
            else "{}"
        )
        status_report_json = (
            status_report.model_dump_json(indent=2)
            if isinstance(status_report, WeeklyStatusReport)
            else "{}"
        )
        return revision_user_blocks(
            task="Revise the RAID log based on reviewer feedback.",
            parsed_brief_json=str(kwargs["parsed_brief_json"]),
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=str(kwargs["feedback"]),
            raci_matrix_json=raci_matrix_json,
            status_report_json=status_report_json,
        )


class _RaciRevisionHelper(BaseAgent[RaciMatrix]):
    system_prompt = REVISION_RACI_SYSTEM

    @property
    def response_model(self) -> type[RaciMatrix]:
        return RaciMatrix

    def build_user_prompt(self, **kwargs: object) -> str:
        wbs = kwargs.get("wbs")
        raci_matrix = kwargs.get("raci_matrix")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        if not isinstance(raci_matrix, RaciMatrix):
            raise TypeError("raci_matrix must be a RaciMatrix")
        return REVISION_RACI_USER.format(
            parsed_brief_json=kwargs["parsed_brief_json"],
            wbs_json=wbs.model_dump_json(indent=2),
            raci_matrix_json=raci_matrix.model_dump_json(indent=2),
            feedback=kwargs["feedback"],
        )


class _StatusRevisionHelper(BaseAgent[WeeklyStatusReport]):
    system_prompt = REVISION_STATUS_SYSTEM

    @property
    def response_model(self) -> type[WeeklyStatusReport]:
        return WeeklyStatusReport

    def build_user_prompt(self, **kwargs: object) -> str:
        status_report = kwargs.get("status_report")
        if not isinstance(status_report, WeeklyStatusReport):
            raise TypeError("status_report must be a WeeklyStatusReport")
        return REVISION_STATUS_USER.format(
            parsed_brief_json=kwargs["parsed_brief_json"],
            status_report_json=status_report.model_dump_json(indent=2),
            feedback=kwargs["feedback"],
        )
