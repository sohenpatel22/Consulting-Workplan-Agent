from workplan_agent.display_values import Notes, display_cell, display_stakeholder_rationale


def test_display_cell_empty_with_note() -> None:
    assert display_cell("", note=Notes.SIGNOFF) == "n/a (not confirmed at sign-off)"


def test_display_cell_list_joined() -> None:
    assert display_cell(["1.1", "1.2"]) == "1.1, 1.2"
    assert display_cell([], note=Notes.NONE_IDENTIFIED) == "n/a (none identified)"


def test_display_stakeholder_rationale_explicit() -> None:
    assert display_stakeholder_rationale("explicit", None) == (
        "n/a (not required (named in brief))"
    )


def test_display_stakeholder_rationale_inferred() -> None:
    assert display_stakeholder_rationale("inferred", "  ") == (
        "n/a (not confirmed at sign-off)"
    )
    assert display_stakeholder_rationale("inferred", "From steering committee") == (
        "From steering committee"
    )
