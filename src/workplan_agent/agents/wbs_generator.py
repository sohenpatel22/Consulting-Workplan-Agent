from workplan_agent.agents.base import BaseAgent
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.wbs import WBS

SYSTEM_PROMPT = """You are a consulting project planner. Generate a Work Breakdown Structure (WBS) from a parsed client brief.

Rules:
- Use consulting phases: Discovery, Design, Build, Transition (map work packages accordingly).
- Create a 3-level hierarchy: L1 phases, L2 work streams, L3 tasks where appropriate.
- Minimum: 3 level-1 work packages, each with at least 2 level-2 children.
- Use hierarchical IDs (e.g., 1.0, 1.1, 1.2, 2.0, 2.1).
- Each work package must have deliverables, owner_role, and estimated_duration.
- Link dependencies using work package IDs.
- Align work packages to stated objectives and in-scope items.
- Do not include out-of-scope work."""


class WBSGeneratorAgent(BaseAgent[WBS]):
    system_prompt = SYSTEM_PROMPT
    profile = "accurate"

    @property
    def response_model(self) -> type[WBS]:
        return WBS

    def build_user_prompt(self, **kwargs: object) -> str:
        parsed_brief = kwargs.get("parsed_brief")
        if not isinstance(parsed_brief, ParsedBrief):
            raise TypeError("parsed_brief must be a ParsedBrief")
        brief_json = parsed_brief.model_dump_json(indent=2)
        return f"Generate a WBS from this parsed brief:\n\n{brief_json}"
