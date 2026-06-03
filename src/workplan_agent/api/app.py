from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from workplan_agent.api.schemas import (
    ConfirmQuestionsRequest,
    ConfirmQuestionsResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    ReviewAcceptedResponse,
    ReviewRequest,
    ReviewResponse,
    SessionResponse,
)
from workplan_agent.api.files import router as files_router
from workplan_agent.api.store import get_store
from workplan_agent.config import get_settings
from workplan_agent.api.service import (
    STATIC_DIR,
    apply_approve,
    apply_review_work,
    confirm_open_questions,
    create_session,
    get_session,
    run_build_artifacts,
    run_generation,
    run_revision_job,
    run_warm_build_cache_job,
    start_revision,
    warm_build_prompt_cache_for_record,
    warm_session_prompt_cache,
)

app = FastAPI(
    title="Workplan Agent",
    description="Brief → WBS + RAID with human-in-the-loop review",
    version="0.1.0",
)

app.include_router(files_router)

if STATIC_DIR.is_dir():

    class _DevStaticFiles(StaticFiles):
        """Disable long-lived caching for UI assets during local development."""

        async def get_response(self, path: str, scope):  # type: ignore[override]
            response = await super().get_response(path, scope)
            if path.endswith((".css", ".js", ".html")):
                response.headers["Cache-Control"] = "no-cache"
            return response

    app.mount("/assets", _DevStaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {"status": "ok", **get_settings().llm_status()}


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


@app.post(
    "/api/sessions/{session_id}/confirm",
    response_model=ConfirmQuestionsResponse,
    status_code=202,
)
def confirm_session_questions(
    session_id: str,
    request: ConfirmQuestionsRequest,
    background_tasks: BackgroundTasks,
) -> ConfirmQuestionsResponse:
    try:
        confirm_open_questions(session_id, request)
        record = get_store().get(session_id)
        if record is not None:
            warm_build_prompt_cache_for_record(record)
        background_tasks.add_task(run_build_artifacts, session_id)
        return ConfirmQuestionsResponse(
            session_id=session_id,
            message="Answers recorded. Building WBS and RAID…",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/warm-build-cache", status_code=204)
def warm_build_cache(
    session_id: str,
    background_tasks: BackgroundTasks,
) -> None:
    """Prime WBS/RAID template + brief cache while the user confirms open questions."""
    record = get_store().get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if record.phase != "awaiting_confirmation":
        raise HTTPException(
            status_code=400,
            detail="Prompt cache warmup is only available while confirming open questions.",
        )
    background_tasks.add_task(run_warm_build_cache_job, session_id)


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

        if request.action == "quality_check":
            return apply_review_work(session_id, request)

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
