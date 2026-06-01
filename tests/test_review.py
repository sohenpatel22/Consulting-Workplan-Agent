import pytest

from workplan_agent.review import ReviewAction, parse_review_choice


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", ReviewAction.APPROVE),
        ("a", ReviewAction.APPROVE),
        ("approve", ReviewAction.APPROVE),
        ("Approve", ReviewAction.APPROVE),
        ("2", ReviewAction.WBS),
        ("w", ReviewAction.WBS),
        ("wbs feedback", ReviewAction.WBS),
        ("3", ReviewAction.RAID),
        ("raid", ReviewAction.RAID),
        ("4", ReviewAction.STAKEHOLDER),
        ("stakeholder", ReviewAction.STAKEHOLDER),
        ("stakeholder feedback", ReviewAction.STAKEHOLDER),
        ("5", ReviewAction.STATUS),
        ("status", ReviewAction.STATUS),
        ("status report", ReviewAction.STATUS),
        ("status feedback", ReviewAction.STATUS),
        ("6", ReviewAction.BOTH),
        ("both", ReviewAction.BOTH),
        ("Both", ReviewAction.BOTH),
        ("7", ReviewAction.ALL),
        ("all", ReviewAction.ALL),
        ("8", ReviewAction.QUIT),
        ("quit", ReviewAction.QUIT),
        ("q", ReviewAction.QUIT),
        ("exit", ReviewAction.QUIT),
    ],
)
def test_parse_review_choice_accepts_numbers_and_words(raw: str, expected: ReviewAction) -> None:
    assert parse_review_choice(raw) == expected


def test_parse_review_choice_rejects_unknown() -> None:
    assert parse_review_choice("invalid") is None
    assert parse_review_choice("") is None
