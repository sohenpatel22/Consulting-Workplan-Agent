from workplan_agent.confirmation import (
    MAX_CONFIRMATION_QUESTIONS,
    RISK_APPETITE_QUESTION_TEXT,
    build_confirmation_questions,
    risk_appetite_question,
)
from workplan_agent.models.brief import ConfirmationQuestion, Objective, ParsedBrief


def test_build_confirmation_always_includes_risk_appetite() -> None:
    brief = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=[],
    )
    questions = build_confirmation_questions(brief)
    assert len(questions) == 1
    assert questions[-1].question == RISK_APPETITE_QUESTION_TEXT
    assert len(questions[-1].suggested_answers) >= 2


def test_build_confirmation_caps_at_five_and_puts_risk_last() -> None:
    brief = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=[f"Question {index}?" for index in range(1, 8)],
    )
    questions = build_confirmation_questions(brief)
    assert len(questions) == MAX_CONFIRMATION_QUESTIONS
    assert questions[-1] == risk_appetite_question()
    assert all("risk appetite" not in q.question.lower() for q in questions[:-1])


def test_build_confirmation_uses_planner_suggestions() -> None:
    brief = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=["Vendor?"],
        planner_confirmations=[
            ConfirmationQuestion(
                question="Vendor?",
                suggested_answers=["A", "B", "C"],
            )
        ],
    )
    questions = build_confirmation_questions(brief)
    assert questions[0].suggested_answers == ["A", "B", "C"]
