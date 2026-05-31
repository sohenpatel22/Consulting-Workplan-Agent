from workplan_agent.agents.base import BaseAgent
from workplan_agent.llm.caching import ContentBlock
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.prompts import (
    BRIEF_PARSER_SYSTEM,
    _append_user_instructions,
    BRIEF_PARSER_USER,
    brief_parser_system_blocks,
    brief_parser_user_blocks,
    normalize_user_prompt,
)


class BriefParserAgent(BaseAgent[ParsedBrief]):
    system_prompt = BRIEF_PARSER_SYSTEM
    @property
    def response_model(self) -> type[ParsedBrief]:
        return ParsedBrief

    def build_user_prompt(self, **kwargs: object) -> str:
        brief_text = kwargs.get("brief_text")
        if not isinstance(brief_text, str):
            raise TypeError("brief_text must be a string")
        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        body = BRIEF_PARSER_USER.format(brief_text=brief_text)
        return _append_user_instructions(body, user_prompt or None)

    def build_system_blocks(self) -> list[ContentBlock]:
        return brief_parser_system_blocks(self.response_model)

    def build_user_blocks(self, **kwargs: object) -> list[ContentBlock]:
        brief_text = kwargs.get("brief_text")
        if not isinstance(brief_text, str):
            raise TypeError("brief_text must be a string")
        user_prompt = normalize_user_prompt(kwargs.get("user_prompt"))
        return brief_parser_user_blocks(brief_text, user_prompt or None)

    def run_and_validate(
        self,
        brief_text: str,
        *,
        user_prompt: str = "",
    ) -> ParsedBrief:
        parsed = self.run(brief_text=brief_text, user_prompt=user_prompt)
        errors = parsed.validate_required()
        if errors:
            raise ValueError(f"Brief validation failed: {'; '.join(errors)}")
        return parsed
