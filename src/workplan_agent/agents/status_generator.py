from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.base import build_messages
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.status_report import WeeklyStatusReport
from workplan_agent.prompts import (
    STATUS_GENERATOR_SYSTEM,
    STATUS_GENERATOR_USER,
    append_generation_context,
    normalize_user_prompt,
    status_generator_system_blocks,
    status_generator_user_blocks,
)


class StatusReportGeneratorAgent(BaseAgent[WeeklyStatusReport]):
    system_prompt = STATUS_GENERATOR_SYSTEM

    @property
    def response_model(self) -> type[WeeklyStatusReport]:
        return WeeklyStatusReport

    def build_user_prompt(self, **kwargs: object) -> str:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        raid = kwargs.get("raid")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        if not isinstance(raid, RAIDLog):
            raise TypeError("raid must be a RAIDLog")

        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        body = STATUS_GENERATOR_USER.format(
            brief_json=parsed_brief.model_dump_json(indent=2),
            wbs_json=wbs.model_dump_json(indent=2),
            raid_json=raid.model_dump_json(indent=2),
        )
        return append_generation_context(body, user_prompt or None)

    def build_system_blocks(self) -> list[ContentBlock]:
        return status_generator_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        raid = kwargs.get("raid")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        if not isinstance(raid, RAIDLog):
            raise TypeError("raid must be a RAIDLog")
        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        return status_generator_user_blocks(
            parsed_brief.model_dump_json(indent=2),
            wbs.model_dump_json(indent=2),
            raid.model_dump_json(indent=2),
            user_prompt or None,
        )

    def build_messages(self, **kwargs: object):
        if self._caching_enabled():
            return super().build_messages(**kwargs)
        return build_messages(self.system_prompt, self.build_user_prompt(**kwargs))
