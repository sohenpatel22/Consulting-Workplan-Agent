"""Extract verbatim client-brief passages that motivate confirmation questions."""

from __future__ import annotations

import re

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "which",
        "who",
        "will",
        "with",
        "your",
        "you",
    }
)

_RISK_APPETITE_TERMS = frozenset(
    {
        "risk",
        "uncertain",
        "uncertainty",
        "aggressive",
        "conservative",
        "timeline",
        "deadline",
        "buffer",
        "trade-off",
        "tradeoff",
        "ambiguity",
        "contingency",
    }
)


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _question_terms(question: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", question.lower())
    return [word for word in words if word not in _STOPWORDS]


def extract_brief_quotes(
    question: str,
    brief_text: str,
    *,
    max_quotes: int = 2,
) -> list[str]:
    """Return up to ``max_quotes`` brief passages that best match the question."""
    if not brief_text.strip():
        return []

    terms = _question_terms(question)
    if not terms:
        return []

    scored: list[tuple[int, str]] = []
    for sentence in _split_sentences(brief_text):
        lowered = sentence.lower()
        score = sum(1 for term in terms if term in lowered)
        if score > 0:
            scored.append((score, sentence))

    scored.sort(key=lambda item: (-item[0], -len(item[1])))
    quotes: list[str] = []
    seen: set[str] = set()
    for _, sentence in scored:
        if sentence in seen:
            continue
        seen.add(sentence)
        quotes.append(sentence)
        if len(quotes) >= max_quotes:
            break
    return quotes


def _risk_appetite_fallback() -> list[str]:
    return [
        "Standard engagement planning question — sets overall delivery risk tolerance "
        "for RAID ratings (not tied to a specific brief ambiguity)."
    ]


def extract_risk_appetite_quotes(brief_text: str, *, max_quotes: int = 2) -> list[str]:
    """Brief passages about delivery risk, timeline pressure, or uncertainty."""
    if not brief_text.strip():
        return _risk_appetite_fallback()

    scored: list[tuple[int, str]] = []
    for sentence in _split_sentences(brief_text):
        lowered = sentence.lower()
        score = sum(1 for term in _RISK_APPETITE_TERMS if term in lowered)
        if score > 0:
            scored.append((score, sentence))

    scored.sort(key=lambda item: (-item[0], -len(item[1])))
    quotes = [sentence for _, sentence in scored[:max_quotes]]
    if quotes:
        return quotes
    return _risk_appetite_fallback()
