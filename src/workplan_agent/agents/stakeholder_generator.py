from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.base import build_messages
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.stakeholder import StakeholderMap
from workplan_agent.prompts import (
    STAKEHOLDER_GENERATOR_SYSTEM,
    STAKEHOLDER_GENERATOR_USER,
    append_generation_context,
    normalize_user_prompt,
)


class StakeholderMapGeneratorAgent(BaseAgent[StakeholderMap]):
    system_prompt = STAKEHOLDER_GENERATOR_SYSTEM
    use_prompt_cache = False

    @property
    def response_model(self) -> type[StakeholderMap]:
        return StakeholderMap

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
        body = STAKEHOLDER_GENERATOR_USER.format(
            brief_json=parsed_brief.model_dump_json(indent=2),
            wbs_json=wbs.model_dump_json(indent=2),
            raid_json=raid.model_dump_json(indent=2),
        )
        return append_generation_context(body, user_prompt or None)

    def build_messages(self, **kwargs: object):
        return build_messages(self.system_prompt, self.build_user_prompt(**kwargs))
