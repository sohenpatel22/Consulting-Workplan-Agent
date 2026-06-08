"""Remove RAID actions that duplicate risk mitigation plans."""

from __future__ import annotations

import re
from typing import Protocol

_TBD_MARKERS = (
    "tbd",
    "to be determined",
    "not yet defined",
    "not yet known",
    "mitigation approach to be defined",
)

class _ActionLike(Protocol):
    title: str
    description: str


class _RiskLike(Protocol):
    title: str
    mitigation: str


_MITIGATION_ACTION_PREFIXES = (
    "mitigate",
    "mitigation for",
    "mitigation plan",
    "address risk",
    "reduce risk",
)


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _token_set(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _is_tbd_mitigation(mitigation: str) -> bool:
    normalized = _normalize(mitigation)
    if not normalized:
        return True
    return any(marker in normalized for marker in _TBD_MARKERS)


def _text_overlap(left: str, right: str, *, threshold: float = 0.55) -> bool:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if not left_norm or not right_norm:
        return False
    if left_norm in right_norm or right_norm in left_norm:
        return True
    return _jaccard(_token_set(left_norm), _token_set(right_norm)) >= threshold


def action_duplicates_risk_mitigation(action: _ActionLike, risks: list[_RiskLike]) -> bool:
    """True when an action restates a risk mitigation instead of separate follow-up work."""
    action_text = f"{action.title} {action.description}".strip()
    action_title = _normalize(action.title)

    for risk in risks:
        mitigation = risk.mitigation.strip()
        risk_title = risk.title.strip()

        if mitigation and not _is_tbd_mitigation(mitigation):
            if _text_overlap(mitigation, action_text):
                return True

        if risk_title:
            if _text_overlap(risk_title, action.title, threshold=0.65):
                if mitigation and not _is_tbd_mitigation(mitigation):
                    if _text_overlap(mitigation, action_text, threshold=0.35):
                        return True
                if any(action_title.startswith(prefix) for prefix in _MITIGATION_ACTION_PREFIXES):
                    return True

    return False


def strip_mitigation_duplicate_actions[T: _ActionLike](
    actions: list[T],
    risks: list[_RiskLike],
) -> list[T]:
    return [action for action in actions if not action_duplicates_risk_mitigation(action, risks)]
