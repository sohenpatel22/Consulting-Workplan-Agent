"""Extract plain text from uploaded brief files."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import UploadFile

ALLOWED_UPLOAD_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx"}
MIN_EXTRACTED_LENGTH = 10


class BriefExtractError(ValueError):
    """Raised when a brief file cannot be parsed."""


def _extension(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    ext = _extension(filename)
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise BriefExtractError(f"Unsupported file type '{ext or '(none)'}'. Use: {allowed}.")

    if ext in {".md", ".markdown", ".txt"}:
        text = content.decode("utf-8", errors="replace").strip()
    elif ext == ".pdf":
        text = _extract_pdf(content)
    elif ext == ".docx":
        text = _extract_docx(content)
    else:
        raise BriefExtractError(f"Unsupported file type '{ext}'.")

    if len(text) < MIN_EXTRACTED_LENGTH:
        raise BriefExtractError(
            f"Extracted text is too short ({len(text)} chars). "
            f"Need at least {MIN_EXTRACTED_LENGTH} characters."
        )
    return text


async def extract_text_from_upload(file: UploadFile) -> tuple[str, str]:
    """Read an upload and return (text, original filename)."""
    filename = file.filename or "upload"
    content = await file.read()
    if not content:
        raise BriefExtractError("Uploaded file is empty.")
    text = extract_text_from_bytes(content, filename)
    return text, filename


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise BriefExtractError("PDF support is not installed.") from exc

    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            parts.append(page_text.strip())
    return "\n\n".join(parts).strip()


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise BriefExtractError("DOCX support is not installed.") from exc

    document = Document(io.BytesIO(content))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs).strip()
