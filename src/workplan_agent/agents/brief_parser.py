from workplan_agent.agents.base import BaseAgent
from workplan_agent.models.brief import ParsedBrief

SYSTEM_PROMPT = """You are a consulting engagement analyst. Extract structured information from client briefs.

Rules:
- Do not invent scope, objectives, or constraints not implied by the brief.
- Put ambiguities, missing information, and unclear items in open_questions.
- Preserve client naming and terminology from the brief.
- Extract all objectives with clear success criteria where stated.
- Separate in-scope and out-of-scope items explicitly.
- Identify stakeholders mentioned or implied in the brief."""


class BriefParserAgent(BaseAgent[ParsedBrief]):
    system_prompt = SYSTEM_PROMPT
    profile = "balanced"

    @property
    def response_model(self) -> type[ParsedBrief]:
        return ParsedBrief

    def build_user_prompt(self, **kwargs: object) -> str:
        brief_text = kwargs.get("brief_text")
        if not isinstance(brief_text, str):
            raise TypeError("brief_text must be a string")
        return f"Parse the following client brief:\n\n{brief_text}"

    def run_and_validate(self, brief_text: str) -> ParsedBrief:
        parsed = self.run(brief_text=brief_text)
        errors = parsed.validate_required()
        if errors:
            raise ValueError(f"Brief validation failed: {'; '.join(errors)}")
        return parsed
