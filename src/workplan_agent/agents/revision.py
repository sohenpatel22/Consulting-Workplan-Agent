from enum import Enum

from pydantic import BaseModel

from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.models.stakeholder import StakeholderMap
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.prompts import (
    REVISION_RAID_USER,
    REVISION_SYSTEM,
    REVISION_WBS_USER,
    REVISION_STAKEHOLDER_SYSTEM,
    REVISION_STAKEHOLDER_USER,
    REVISION_STATUS_SYSTEM,
    REVISION_STATUS_USER,
    revision_system_blocks,
    revision_user_blocks,
)


class RevisionTarget(str, Enum):
    WBS = "wbs"
    RAID = "raid"
    STAKEHOLDER = "stakeholder"
    STATUS = "status"


class RevisionResult(BaseModel):
    wbs: WBS | None = None
    raid: RAIDLog | None = None
    stakeholder_map: StakeholderMap | None = None
    status_report: WeeklyStatusReport | None = None


class RevisionAgent:
    def __init__(self, provider) -> None:
        self.provider = provider
        self._wbs_agent = _WBSRevisionHelper(provider)
        self._raid_agent = _RAIDRevisionHelper(provider)
        self._stakeholder_agent = _StakeholderRevisionHelper(provider)
        self._status_agent = _StatusRevisionHelper(provider)

    def run(
        self,
        parsed_brief: ParsedBrief,
        wbs: WBS,
        raid: RAIDLog,
        feedback: str,
        target: RevisionTarget,
        stakeholder_map: StakeholderMap | None = None,
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
                stakeholder_map=stakeholder_map,
                status_report=status_report,
            )

        elif target == RevisionTarget.RAID:
            result.raid = self._raid_agent.run(
                parsed_brief_json=brief_json,
                wbs=wbs,
                raid=raid,
                feedback=feedback,
                stakeholder_map=stakeholder_map,
                status_report=status_report,
            )

        elif target == RevisionTarget.STAKEHOLDER:
            if stakeholder_map is None:
                raise ValueError("stakeholder_map is required for stakeholder map revision")
            result.stakeholder_map = self._stakeholder_agent.run(
                parsed_brief_json=brief_json,
                stakeholder_map=stakeholder_map,
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
        stakeholder_map = kwargs.get("stakeholder_map")
        status_report = kwargs.get("status_report")
        stakeholder_map_json = (
            stakeholder_map.model_dump_json(indent=2)
            if isinstance(stakeholder_map, StakeholderMap)
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
            stakeholder_map_json=stakeholder_map_json,
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
        stakeholder_map = kwargs.get("stakeholder_map")
        status_report = kwargs.get("status_report")
        stakeholder_map_json = (
            stakeholder_map.model_dump_json(indent=2)
            if isinstance(stakeholder_map, StakeholderMap)
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
            stakeholder_map_json=stakeholder_map_json,
            status_report_json=status_report_json,
        )


class _StakeholderRevisionHelper(BaseAgent[StakeholderMap]):
    system_prompt = REVISION_STAKEHOLDER_SYSTEM

    @property
    def response_model(self) -> type[StakeholderMap]:
        return StakeholderMap

    def build_user_prompt(self, **kwargs: object) -> str:
        stakeholder_map = kwargs.get("stakeholder_map")
        if not isinstance(stakeholder_map, StakeholderMap):
            raise TypeError("stakeholder_map must be a StakeholderMap")
        return REVISION_STAKEHOLDER_USER.format(
            parsed_brief_json=kwargs["parsed_brief_json"],
            stakeholder_map_json=stakeholder_map.model_dump_json(indent=2),
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
