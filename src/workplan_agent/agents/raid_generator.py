from workplan_agent.agents.base import BaseAgent
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.wbs import WBS

SYSTEM_PROMPT = """You are a consulting risk manager. Generate a RAID log (Risks, Assumptions, Issues, Dependencies) from a parsed brief and WBS.

Rules:
- Minimum 3 risks, 2 assumptions. Include issues only if implied by the brief.
- Every item must link to related_wbs_ids from the provided WBS.
- Risks must include mitigation strategies.
- Derive assumptions from the brief's stated assumptions and implicit dependencies.
- Dependencies should capture cross-work-package or external dependencies.
- Use severity: High, Medium, or Low. Status defaults to Open.
- Assign realistic owners based on stakeholder roles from the brief.
- Use IDs: R1, R2... for risks; A1, A2... for assumptions; I1... for issues; D1... for dependencies."""


class RAIDGeneratorAgent(BaseAgent[RAIDLog]):
    system_prompt = SYSTEM_PROMPT
    profile = "accurate"

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
        return (
            "Generate a RAID log from this parsed brief and WBS.\n\n"
            f"## Parsed Brief\n{parsed_brief.model_dump_json(indent=2)}\n\n"
            f"## WBS\n{wbs.model_dump_json(indent=2)}"
        )
