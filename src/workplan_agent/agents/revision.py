from enum import Enum

from pydantic import BaseModel

from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.prompts import (
    REVISION_RAID_USER,
    REVISION_SYSTEM,
    REVISION_WBS_USER,
    revision_system_blocks,
    revision_user_blocks,
)


class RevisionTarget(str, Enum):
    WBS = "wbs"
    RAID = "raid"
    BOTH = "both"


class RevisionResult(BaseModel):
    wbs: WBS | None = None
    raid: RAIDLog | None = None


class RevisionAgent:
    profile = "balanced"

    def __init__(self, provider) -> None:
        self.provider = provider
        self._wbs_agent = _WBSRevisionHelper(provider)
        self._raid_agent = _RAIDRevisionHelper(provider)

    def run(
        self,
        parsed_brief: ParsedBrief,
        wbs: WBS,
        raid: RAIDLog,
        feedback: str,
        target: RevisionTarget,
    ) -> RevisionResult:
        result = RevisionResult()
        brief_json = parsed_brief.model_dump_json(indent=2)

        if target in (RevisionTarget.WBS, RevisionTarget.BOTH):
            result.wbs = self._wbs_agent.run(
                parsed_brief_json=brief_json,
                wbs=wbs,
                raid=raid,
                feedback=feedback,
            )

        if target in (RevisionTarget.RAID, RevisionTarget.BOTH):
            current_wbs = result.wbs or wbs
            result.raid = self._raid_agent.run(
                parsed_brief_json=brief_json,
                wbs=current_wbs,
                raid=raid,
                feedback=feedback,
            )

        return result


class _WBSRevisionHelper(BaseAgent[WBS]):
    system_prompt = REVISION_SYSTEM
    profile = "balanced"

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
        return revision_user_blocks(
            task="Revise the WBS based on reviewer feedback.",
            parsed_brief_json=str(kwargs["parsed_brief_json"]),
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=str(kwargs["feedback"]),
        )


class _RAIDRevisionHelper(BaseAgent[RAIDLog]):
    system_prompt = REVISION_SYSTEM
    profile = "balanced"

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
        return revision_user_blocks(
            task="Revise the RAID log based on reviewer feedback.",
            parsed_brief_json=str(kwargs["parsed_brief_json"]),
            wbs_json=kwargs["wbs"].model_dump_json(indent=2),
            raid_json=kwargs["raid"].model_dump_json(indent=2),
            feedback=str(kwargs["feedback"]),
        )
