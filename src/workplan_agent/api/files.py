"""File upload and artifact download endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from workplan_agent.api.service import get_session
from workplan_agent.files.export import CONTENT_TYPES, ArtifactKind, ExportFormat, export_artifact
from workplan_agent.files.extract import BriefExtractError, extract_text_from_upload

router = APIRouter(prefix="/api", tags=["files"])


class BriefUploadResponse(BaseModel):
    text: str
    filename: str
    char_count: int


@router.post("/brief/upload", response_model=BriefUploadResponse)
async def upload_brief(file: UploadFile = File(...)) -> BriefUploadResponse:
    """Extract text from an uploaded brief (PDF, DOCX, MD, or TXT)."""
    try:
        text, filename = await extract_text_from_upload(file)
    except BriefExtractError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BriefUploadResponse(text=text, filename=filename, char_count=len(text))


@router.get("/sessions/{session_id}/download/{artifact}/{fmt}")
def download_artifact(
    session_id: str,
    artifact: ArtifactKind,
    fmt: ExportFormat,
) -> Response:
    """Download WBS or RAID as MD, HTML, DOCX, or PDF."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.job_status != "complete":
        raise HTTPException(status_code=409, detail="Session artifacts are not ready yet.")

    markdown = session.wbs_markdown if artifact == "wbs" else session.raid_markdown
    if not markdown:
        raise HTTPException(status_code=404, detail=f"{artifact.upper()} content not available.")

    try:
        content, filename = export_artifact(markdown, artifact, fmt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type: str = CONTENT_TYPES[fmt]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
