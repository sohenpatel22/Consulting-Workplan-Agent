"""File upload and artifact download endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from workplan_agent.api.service import get_session
from workplan_agent.api.store import get_store
from workplan_agent.files.export import CONTENT_TYPES, ArtifactKind, ExportFormat, export_artifact
from workplan_agent.files.extract import BriefExtractError, extract_text_from_upload
from workplan_agent.render import (
    render_raid_markdown,
    render_wbs_markdown,
    render_raci_markdown,
    render_status_markdown,
)

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
    """Download WBS or RAID as MD, HTML, DOCX, PDF, or RAID as XLSX (Deloitte template)."""
    response = get_session(session_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if response.job_status != "complete":
        raise HTTPException(status_code=409, detail="Session artifacts are not ready yet.")

    record = get_store().get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    workplan = record.session
    parsed = workplan.parsed_brief
    markdown = None
    if parsed and workplan.wbs and artifact == "wbs":
        markdown = render_wbs_markdown(workplan.wbs, parsed)
    elif parsed and workplan.raid and artifact == "raid":
        markdown = render_raid_markdown(workplan.raid, parsed)
    elif parsed and workplan.raci_matrix and artifact == "raci":
        markdown = render_raci_markdown(workplan.raci_matrix, parsed)
    elif parsed and workplan.status_report and artifact == "status":
        markdown = render_status_markdown(workplan.status_report, parsed)

    if fmt != "xlsx" and not markdown:
        raise HTTPException(status_code=404, detail=f"{artifact.upper()} content not available.")

    if fmt == "xlsx" and parsed is None:
        raise HTTPException(status_code=404, detail="Structured content not available.")
    if fmt == "xlsx" and artifact == "raid" and workplan.raid is None:
        raise HTTPException(status_code=404, detail="RAID content not available.")
    if fmt == "xlsx" and artifact == "raci" and workplan.raci_matrix is None:
        raise HTTPException(status_code=404, detail="RACI content not available.")
    if artifact == "wbs" and fmt == "docx" and workplan.wbs is None:
        raise HTTPException(status_code=404, detail="WBS content not available.")

    try:
        content, filename = export_artifact(
            markdown or "",
            artifact,
            fmt,
            wbs=workplan.wbs,
            raid=workplan.raid,
            raci_matrix=workplan.raci_matrix,
            status_report=workplan.status_report,
            parsed_brief=parsed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    media_type: str = CONTENT_TYPES[fmt]
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
