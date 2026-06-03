"""Format table and export cell values; blank fields show n/a with a short reason."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum

NA = "n/a"


class Notes:
    """Short explanations for empty cells in exports and reports."""

    SIGNOFF = "not confirmed at sign-off"
    SIGNOFF_DETAIL = "not detailed at sign-off"
    SIGNOFF_ASSIGNED = "not assigned at sign-off"
    SIGNOFF_ESTIMATE = "not estimated at sign-off"
    NONE_IDENTIFIED = "none identified"
    NOT_LINKED_WBS = "not linked to WBS"
    NOT_YET_DEFINED = "not yet defined"
    NO_UPDATE = "no update recorded yet"
    PENDING_RESOLUTION = "pending resolution"
    NOT_YET_REACHED = "not yet reached"
    EXPLICIT_RATIONALE = "not required (named in brief)"


def is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value) == 0
    return False


def display_cell(value: object, *, note: str | None = None) -> str:
    """Return a display string; empty values become n/a with an optional explanation."""
    if isinstance(value, Enum):
        value = value.value

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parts = [str(part).strip() for part in value if str(part).strip()]
        if parts:
            return ", ".join(parts)
        return _empty_label(note)

    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
        return _empty_label(note)

    if value is None:
        return _empty_label(note)

    text = str(value).strip()
    if text:
        return text
    return _empty_label(note)


def _empty_label(note: str | None) -> str:
    if note:
        return f"{NA} ({note})"
    return NA


def display_stakeholder_rationale(source: str, rationale: str | None) -> str:
    if rationale and rationale.strip():
        return rationale.strip()
    if source == "explicit":
        return display_cell(None, note=Notes.EXPLICIT_RATIONALE)
    return display_cell(None, note=Notes.SIGNOFF)
