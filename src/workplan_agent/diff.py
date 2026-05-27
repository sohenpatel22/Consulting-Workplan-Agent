import difflib


def unified_text_diff(before: str, after: str, label: str) -> str:
    """Return a unified diff between two text blobs (empty string if identical)."""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    if before_lines == after_lines:
        return ""

    diff_lines = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"{label} (before)",
        tofile=f"{label} (after)",
        lineterm="",
    )
    return "\n".join(diff_lines)
