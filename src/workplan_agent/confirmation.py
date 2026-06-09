"""Planner sign-off questions shown before WBS/RAID generation."""

from __future__ import annotations

from workplan_agent.brief_quotes import (
    build_derivation_rationale,
    build_risk_appetite_rationale,
    extract_brief_quotes,
    extract_risk_appetite_quotes,
)
from workplan_agent.models.brief import ConfirmationQuestion, ParsedBrief

MAX_CONFIRMATION_QUESTIONS = 5

RISK_APPETITE_QUESTION_TEXT = (
    "What is your overall risk appetite for this engagement "
    "(how much delivery uncertainty and trade-off are you willing to accept)?"
)

RISK_APPETITE_SUGGESTIONS = [
    "Conservative — prioritize certainty, buffers, and escalation paths",
    "Balanced — accept moderate ambiguity with clear RAID tracking",
    "Aggressive — favor speed and innovation; tolerate higher delivery risk",
]

GENERIC_SUGGESTIONS = [
    "Proceed with the approach implied in the brief",
    "Choose the lower-risk / phased option",
    "Choose the faster or more ambitious option",
    "Other — I will specify below",
]


def risk_appetite_question(brief_text: str = "") -> ConfirmationQuestion:
    quotes = extract_risk_appetite_quotes(brief_text)
    return ConfirmationQuestion(
        question=RISK_APPETITE_QUESTION_TEXT,
        suggested_answers=list(RISK_APPETITE_SUGGESTIONS),
        brief_quotes=quotes,
        derivation_rationale=build_risk_appetite_rationale(quotes),
    )


def _is_risk_appetite_question(text: str) -> bool:
    lowered = text.lower()
    return "risk appetite" in lowered or (
        "risk" in lowered and "appetite" in lowered
    )


def _resolve_derivation_rationale(
    question: str,
    quotes: list[str],
    explicit: str,
) -> str:
    rationale = explicit.strip()
    if rationale:
        return rationale
    return build_derivation_rationale(question, quotes)


def _generic_question(text: str, brief_text: str = "") -> ConfirmationQuestion:
    question = text.strip()
    quotes = extract_brief_quotes(question, brief_text)
    return ConfirmationQuestion(
        question=question,
        suggested_answers=list(GENERIC_SUGGESTIONS),
        brief_quotes=quotes,
        derivation_rationale=build_derivation_rationale(question, quotes),
    )


def _resolve_brief_quotes(
    question: str,
    explicit_quotes: list[str],
    brief_text: str,
) -> list[str]:
    cleaned = [quote.strip() for quote in explicit_quotes if quote.strip()]
    if cleaned:
        return cleaned[:2]
    return extract_brief_quotes(question, brief_text)


def build_confirmation_questions(
    parsed: ParsedBrief,
    *,
    brief_text: str = "",
) -> list[ConfirmationQuestion]:
    """Up to five planner sign-off questions, always including risk appetite."""
    brief_slots = MAX_CONFIRMATION_QUESTIONS - 1
    by_question: dict[str, ConfirmationQuestion] = {}

    for item in parsed.planner_confirmations:
        question = item.question.strip()
        if not question or _is_risk_appetite_question(question):
            continue
        answers = [a.strip() for a in item.suggested_answers if a.strip()]
        if len(answers) < 2:
            answers = list(GENERIC_SUGGESTIONS)
        quotes = _resolve_brief_quotes(question, item.brief_quotes, brief_text)
        by_question[question] = ConfirmationQuestion(
            question=question,
            suggested_answers=answers[:6],
            brief_quotes=quotes,
            derivation_rationale=_resolve_derivation_rationale(
                question,
                quotes,
                item.derivation_rationale,
            ),
        )

    for text in parsed.open_questions:
        question = text.strip()
        if not question or _is_risk_appetite_question(question):
            continue
        if question not in by_question:
            by_question[question] = _generic_question(question, brief_text)

    brief_questions = list(by_question.values())[:brief_slots]
    return [*brief_questions, risk_appetite_question(brief_text)]
