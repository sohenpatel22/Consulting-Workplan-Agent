import pytest

from workplan_agent.models.brief import Objective, ParsedBrief, ResolvedQuestion


def test_apply_open_question_resolutions() -> None:
    brief = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=["Vendor choice?", "Timeline?"],
    )
    brief.apply_open_question_resolutions(
        [
            ResolvedQuestion(question="Vendor choice?", answer="Vendor A"),
            ResolvedQuestion(question="Timeline?", answer="6 months"),
        ]
    )
    assert brief.open_questions == []
    assert len(brief.resolved_open_questions) == 2
    assert any("Vendor A" in item for item in brief.assumptions_from_brief)


def test_apply_resolutions_requires_all_answers() -> None:
    brief = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=["Vendor choice?"],
    )
    with pytest.raises(ValueError, match="Expected 1"):
        brief.apply_open_question_resolutions([])
