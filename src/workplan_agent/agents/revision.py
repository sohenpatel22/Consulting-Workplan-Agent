from enum import Enum

from pydantic import BaseModel, Field

from workplan_agent.agents.base import BaseAgent
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS


class RevisionTarget(str, Enum):
    WBS = "wbs"
    RAID = "raid"
    BOTH = "both"


class RevisionResult(BaseModel):
    wbs: WBS | None = None
    raid: RAIDLog | None = None


SYSTEM_PROMPT = """You are a consulting workplan reviewer. Apply reviewer feedback to WBS and/or RAID artifacts.

Rules:
- Apply ONLY the requested changes from the feedback.
- Preserve unaffected items and IDs where possible.
- Maintain WBS hierarchy rules: 3+ L1 items, each with 2+ L2 children.
- Maintain RAID rules: 3+ risks, 2+ assumptions, valid WBS cross-references.
- Do not remove work packages or RAID items unless feedback explicitly asks.
- Return the complete updated artifact(s) in the response."""


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
    system_prompt = SYSTEM_PROMPT
    profile = "balanced"

    @property
    def response_model(self) -> type[WBS]:
        return WBS

    def build_user_prompt(self, **kwargs: object) -> str:
        return (
            "Revise the WBS based on reviewer feedback.\n\n"
            f"## Parsed Brief\n{kwargs['parsed_brief_json']}\n\n"
            f"## Current WBS\n{kwargs['wbs'].model_dump_json(indent=2)}\n\n"
            f"## Current RAID (for context)\n{kwargs['raid'].model_dump_json(indent=2)}\n\n"
            f"## Reviewer Feedback\n{kwargs['feedback']}"
        )

    def run(self, **kwargs: object) -> WBS:
        user_prompt = self.build_user_prompt(**kwargs)
        from workplan_agent.llm.base import build_messages, schema_instruction

        system = f"{self.system_prompt}\n\n{schema_instruction(self.response_model)}"
        messages = build_messages(system, user_prompt)
        return self.provider.call_structured(messages, self.response_model, profile=self.profile)


class _RAIDRevisionHelper(BaseAgent[RAIDLog]):
    system_prompt = SYSTEM_PROMPT
    profile = "balanced"

    @property
    def response_model(self) -> type[RAIDLog]:
        return RAIDLog

    def build_user_prompt(self, **kwargs: object) -> str:
        return (
            "Revise the RAID log based on reviewer feedback.\n\n"
            f"## Parsed Brief\n{kwargs['parsed_brief_json']}\n\n"
            f"## Current WBS\n{kwargs['wbs'].model_dump_json(indent=2)}\n\n"
            f"## Current RAID\n{kwargs['raid'].model_dump_json(indent=2)}\n\n"
            f"## Reviewer Feedback\n{kwargs['feedback']}"
        )

    def run(self, **kwargs: object) -> RAIDLog:
        user_prompt = self.build_user_prompt(**kwargs)
        from workplan_agent.llm.base import build_messages, schema_instruction

        system = f"{self.system_prompt}\n\n{schema_instruction(self.response_model)}"
        messages = build_messages(system, user_prompt)
        return self.provider.call_structured(messages, self.response_model, profile=self.profile)
