from workplan_agent.brief_quotes import extract_brief_quotes, extract_risk_appetite_quotes
from workplan_agent.confirmation import build_confirmation_questions
from workplan_agent.models.brief import ConfirmationQuestion, Objective, ParsedBrief


def test_extract_brief_quotes_matches_question_terms() -> None:
    brief = (
        "The client has not selected an identity resolution vendor yet. "
        "Delivery should start in June 2026."
    )
    quotes = extract_brief_quotes(
        "Which identity resolution vendor should we standardize on?",
        brief,
    )
    assert quotes
    assert "identity resolution vendor" in quotes[0].lower()


def test_build_confirmation_questions_includes_brief_quotes() -> None:
    brief_text = (
        "Identity resolution vendor decision pending before architecture sign-off. "
        "Budget is capped at 1.2M."
    )
    parsed = ParsedBrief(
        client_name="Acme",
        project_title="Rollout",
        objectives=[Objective(id="1", description="Go live")],
        scope_in=["Build"],
        open_questions=["Identity resolution vendor decision pending"],
        planner_confirmations=[
            ConfirmationQuestion(
                question="Identity resolution vendor decision pending",
                suggested_answers=["Vendor A", "Vendor B"],
                brief_quotes=["Identity resolution vendor decision pending before architecture sign-off."],
            )
        ],
    )
    questions = build_confirmation_questions(parsed, brief_text=brief_text)
    assert questions[0].brief_quotes
    assert "identity resolution vendor" in questions[0].brief_quotes[0].lower()
    assert questions[-1].brief_quotes


def test_risk_appetite_quotes_fallback_message() -> None:
    quotes = extract_risk_appetite_quotes("")
    assert quotes
    assert "planning question" in quotes[0].lower()
