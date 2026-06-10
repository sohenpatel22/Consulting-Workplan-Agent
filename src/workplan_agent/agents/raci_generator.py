from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.base import build_messages
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS
from workplan_agent.models.raci import RaciMatrix
from workplan_agent.prompts import (
    RACI_GENERATOR_SYSTEM,
    RACI_GENERATOR_USER,
    append_generation_context,
    normalize_user_prompt,
    raci_generator_system_blocks,
    raci_generator_user_blocks,
)


class RaciMatrixGeneratorAgent(BaseAgent[RaciMatrix]):
    system_prompt = RACI_GENERATOR_SYSTEM

    @property
    def response_model(self) -> type[RaciMatrix]:
        return RaciMatrix

    def build_user_prompt(self, **kwargs: object) -> str:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")

        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        body = RACI_GENERATOR_USER.format(
            brief_json=parsed_brief.model_dump_json(indent=2),
            wbs_json=wbs.model_dump_json(indent=2),
        )
        return append_generation_context(body, user_prompt or None)

    def build_system_blocks(self) -> list[ContentBlock]:
        return raci_generator_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        parsed_brief = kwargs.get("parsed_brief")
        wbs = kwargs.get("wbs")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        if not isinstance(wbs, WBS):
            raise TypeError("wbs must be a WBS")
        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        return raci_generator_user_blocks(
            parsed_brief.model_dump_json(indent=2),
            wbs.model_dump_json(indent=2),
            user_prompt or None,
        )

    def build_messages(self, **kwargs: object):
        if self._caching_enabled():
            return super().build_messages(**kwargs)
        return build_messages(self.system_prompt, self.build_user_prompt(**kwargs))
