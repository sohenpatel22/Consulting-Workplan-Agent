from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS
from workplan_agent.prompts import (
    RAID_GENERATOR_SYSTEM,
    RAID_GENERATOR_USER,
    raid_generator_system_blocks,
    raid_generator_user_blocks,
)


class RAIDGeneratorAgent(BaseAgent[RAIDLog]):
    system_prompt = RAID_GENERATOR_SYSTEM
    @property
    def response_model(self) -> type[RAIDLog]:
        return RAIDLog

    def build_user_prompt(self, **kwargs: object) -> str:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        return RAID_GENERATOR_USER.format(
            brief_json=parsed_brief.model_dump_json(indent=2),
            wbs_json=wbs.model_dump_json(indent=2),
        )

    def build_system_blocks(self) -> list[ContentBlock]:
        return raid_generator_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        return raid_generator_user_blocks(
            parsed_brief.model_dump_json(indent=2),
            wbs.model_dump_json(indent=2),
        )
