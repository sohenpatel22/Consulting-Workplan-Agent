from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from workplan_agent.api.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    ReviewAcceptedResponse,
    ReviewRequest,
    ReviewResponse,
    SessionResponse,
)
from workplan_agent.api.files import router as files_router
from workplan_agent.api.service import (
    STATIC_DIR,
    apply_approve,
    create_session,
    get_session,
    run_generation,
    run_revision_job,
    start_revision,
    warm_session_prompt_cache,
)

app = FastAPI(
    title="Workplan Agent",
    description="Brief → WBS + RAID with human-in-the-loop review",
    version="0.1.0",
)

app.include_router(files_router)

if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=CreateSessionResponse, status_code=202)
def start_session(
    request: CreateSessionRequest,
    background_tasks: BackgroundTasks,
) -> CreateSessionResponse:
    record = create_session(request)
    background_tasks.add_task(warm_session_prompt_cache, request.mock)
    background_tasks.add_task(run_generation, record)
    return CreateSessionResponse(
        session_id=record.session.session_id,
        job_status=record.job_status,
    )


@app.get("/api/sessions/{session_id}", response_model=SessionResponse)
def read_session(session_id: str) -> SessionResponse:
    response = get_session(session_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return response


@app.post(
    "/api/sessions/{session_id}/review",
    responses={
        200: {"model": ReviewResponse},
        202: {"model": ReviewAcceptedResponse},
    },
)
def review_session(
    session_id: str,
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
) -> ReviewResponse | ReviewAcceptedResponse:
    try:
        if request.action == "approve":
            return apply_approve(session_id, request)

        start_revision(session_id, request)
        background_tasks.add_task(run_revision_job, session_id, request.model_dump())
        body = ReviewAcceptedResponse(
            session_id=session_id,
            message="Revision in progress. Poll the session until complete.",
        )
        return JSONResponse(status_code=202, content=body.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        if "already in progress" in detail:
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc
