from workplan_agent.prompts import build_generation_guidance, format_confirmed_answers


def test_format_confirmed_answers_mentions_marker_field() -> None:
    text = format_confirmed_answers([("Q1?", "Answer 1")])
    assert "from_confirmed_answer" in text


def test_format_confirmed_answers() -> None:
    text = format_confirmed_answers([("Q1?", "Answer 1")])
    assert "Confirmed open questions" in text
    assert "Q1?" in text
    assert "Answer 1" in text


def test_build_generation_guidance_combines_sections() -> None:
    text = build_generation_guidance(
        "Use agile names.",
        confirmed_answers=[("Timeline?", "6 months")],
    )
    assert "Planner instructions" in text
    assert "Use agile names." in text
    assert "Confirmed open questions" in text
    assert "6 months" in text
