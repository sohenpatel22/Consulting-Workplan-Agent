import io

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from workplan_agent.api.app import app
from workplan_agent.api.store import reset_store
from workplan_agent.files.export import export_artifact
from workplan_agent.files.extract import BriefExtractError, extract_text_from_bytes

BRIEF = """# Test Brief

**Client:** Acme Corp
**Project:** Platform Rollout

## Objectives

1. Deliver MVP
2. Train operations team
"""

SAMPLE_MD = """# Sample

## Section

Some body text for extraction testing purposes.
"""


@pytest.fixture
def client() -> TestClient:
    reset_store()
    return TestClient(app)


def test_extract_markdown_bytes() -> None:
    text = extract_text_from_bytes(SAMPLE_MD.encode(), "brief.md")
    assert "Sample" in text
    assert len(text) >= 10


def test_extract_rejects_unknown_extension() -> None:
    with pytest.raises(BriefExtractError, match="Unsupported"):
        extract_text_from_bytes(b"data", "file.exe")


def test_extract_docx_bytes() -> None:
    buffer = io.BytesIO()
    doc = Document()
    doc.add_paragraph("Client brief paragraph for upload testing here.")
    doc.save(buffer)
    text = extract_text_from_bytes(buffer.getvalue(), "brief.docx")
    assert "Client brief paragraph" in text


def test_extract_pdf_bytes() -> None:
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(buffer)
    with pytest.raises(BriefExtractError, match="too short"):
        extract_text_from_bytes(buffer.getvalue(), "brief.pdf")


def test_export_formats() -> None:
    md = "# WBS\n\n## Phase 1\n\n| ID | Task |\n| --- | --- |\n| 1.1 | Setup |\n"
    for fmt in ("md", "html", "docx", "pdf"):
        content, name = export_artifact(md, "wbs", fmt)
        assert content
        assert name.endswith(f".{fmt}")


def test_upload_endpoint_md(client: TestClient) -> None:
    response = client.post(
        "/api/brief/upload",
        files={"file": ("brief.md", SAMPLE_MD.encode(), "text/markdown")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "brief.md"
    assert "Sample" in data["text"]


def test_download_requires_session(client: TestClient) -> None:
    response = client.get("/api/sessions/missing/download/wbs/md")
    assert response.status_code == 404


def test_download_after_generation(client: TestClient) -> None:
    import time

    create = client.post("/api/sessions", json={"brief_text": BRIEF, "mock": True})
    session_id = create.json()["session_id"]

    for _ in range(120):
        session = client.get(f"/api/sessions/{session_id}").json()
        if session["job_status"] in ("complete", "failed"):
            break
        time.sleep(0.05)

    assert session["job_status"] == "complete"

    for fmt, content_prefix in (
        ("md", b"#"),
        ("html", b"<!DOCTYPE html>"),
        ("docx", b"PK"),
        ("pdf", b"%PDF"),
    ):
        response = client.get(f"/api/sessions/{session_id}/download/wbs/{fmt}")
        assert response.status_code == 200, (fmt, response.text)
        assert response.content.startswith(content_prefix)
