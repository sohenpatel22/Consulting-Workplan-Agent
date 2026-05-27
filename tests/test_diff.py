from workplan_agent.diff import unified_text_diff


def test_unified_text_diff_detects_changes() -> None:
    before = "line one\nline two\n"
    after = "line one\nline two changed\nline three\n"
    diff = unified_text_diff(before, after, "WBS")
    assert "---" in diff
    assert "+++" in diff
    assert "-line two" in diff
    assert "+line two changed" in diff


def test_unified_text_diff_empty_when_identical() -> None:
    text = "same\ncontent\n"
    assert unified_text_diff(text, text, "RAID") == ""
