import logging
import uuid
from pathlib import Path

from workplan_agent.agents.revision import RevisionTarget
from workplan_agent.api.schemas import (
    ConfirmQuestionsRequest,
    CreateSessionRequest,
    ParsePreview,
    ReviewRequest,
    ReviewResponse,
    RevisionDiff,
    SessionResponse,
    SessionSummary,
)
from workplan_agent.models.brief import ResolvedQuestion
from workplan_agent.diff import unified_text_diff
from workplan_agent.api.store import SessionRecord, get_store
from workplan_agent.config import get_settings
from workplan_agent.llm import get_provider, warm_build_prompt_cache, warm_prompt_cache
from workplan_agent.models.session import SessionStatus, WorkplanSession
from workplan_agent.orchestrator import OrchestratorAgent
from workplan_agent.files.export import markdown_to_html_body
from workplan_agent.render import (
    render_raid_markdown,
    render_wbs_markdown,
    save_artifacts,
    save_status,
)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
DATA_ROOT = Path.cwd() / "data" / "sessions"
logger = logging.getLogger(__name__)


def _session_dir(session_id: str) -> Path:
    return DATA_ROOT / session_id


def _revision_limits() -> tuple[bool, int | None]:
    settings = get_settings()
    unlimited = settings.max_revisions <= 0
    remaining = None if unlimited else max(0, settings.max_revisions)
    return unlimited, remaining


def _revisions_remaining(session_revision_count: int) -> int | None:
    settings = get_settings()
    if settings.max_revisions <= 0:
        return None
    return max(0, settings.max_revisions - session_revision_count)


def _parse_preview(session: WorkplanSession) -> ParsePreview | None:
    parsed = session.parsed_brief
    if parsed is None:
        return None
    return ParsePreview(
        client=parsed.client_name,
        project=parsed.project_title,
        objectives_count=len(parsed.objectives),
        scope_in_count=len(parsed.scope_in),
    )


def _build_summary(session: WorkplanSession) -> SessionSummary:
    parsed = session.parsed_brief
    return SessionSummary(
        client=parsed.client_name if parsed else "",
        project=parsed.project_title if parsed else "",
        objectives_count=len(parsed.objectives) if parsed else 0,
        wbs_items=len(session.wbs.work_packages) if session.wbs else 0,
        raid_risks=len(session.raid.risks) if session.raid else 0,
        raid_actions=len(session.raid.actions) if session.raid else 0,
        raid_issues=len(session.raid.issues) if session.raid else 0,
        raid_decisions=len(session.raid.decisions) if session.raid else 0,
        raid_assumptions=len(session.raid.actions) if session.raid else 0,
        raid_dependencies=len(session.raid.decisions) if session.raid else 0,
        open_questions=parsed.open_questions if parsed else [],
    )


def session_to_response(record: SessionRecord) -> SessionResponse:
    session = record.session
    unlimited, _ = _revision_limits()
    revisions_remaining = _revisions_remaining(session.revision_count)

    parsed_brief = None
    wbs = None
    raid = None
    wbs_markdown = None
    raid_markdown = None
    wbs_html = None
    raid_html = None
    summary = None

    if session.parsed_brief is not None:
        parsed_brief = session.parsed_brief.model_dump(mode="json")
    if session.wbs is not None:
        wbs = session.wbs.model_dump(mode="json")
    if session.raid is not None:
        raid = session.raid.model_dump(mode="json")
    if (
        session.parsed_brief is not None
        and session.wbs is not None
        and session.raid is not None
    ):
        summary = _build_summary(session)
        wbs_markdown = render_wbs_markdown(session.wbs, session.parsed_brief)
        raid_markdown = render_raid_markdown(session.raid, session.parsed_brief)
        wbs_html = markdown_to_html_body(wbs_markdown)
        raid_html = markdown_to_html_body(raid_markdown)

    awaiting_confirmation = record.phase == "awaiting_confirmation"
    confirmation_questions: list[str] = []
    parse_preview = None
    if session.parsed_brief is not None:
        parse_preview = _parse_preview(session)
        if awaiting_confirmation:
            confirmation_questions = list(session.parsed_brief.open_questions)

    last_review = record.last_review_result
    return SessionResponse(
        session_id=session.session_id,
        job_status=record.job_status,
        phase=record.phase,
        awaiting_confirmation=awaiting_confirmation,
        confirmation_questions=confirmation_questions,
        parse_preview=parse_preview,
        status=session.status,
        revision_count=session.revision_count,
        unlimited_revisions=unlimited,
        revisions_remaining=revisions_remaining,
        review_in_progress=record.review_in_progress,
        review_error=record.review_error,
        last_review_message=last_review.message if last_review else None,
        last_diff=last_review.diff if last_review else None,
        error=record.error,
        summary=summary,
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        wbs_markdown=wbs_markdown,
        raid_markdown=raid_markdown,
        wbs_html=wbs_html,
        raid_html=raid_html,
    )


def warm_session_prompt_cache(mock: bool) -> None:
    if mock:
        return
    try:
        warm_prompt_cache()
    except Exception as exc:
        logger.debug("Session prompt cache warmup skipped: %s", exc)


def warm_build_prompt_cache_for_record(
    record: SessionRecord,
    *,
    wbs_json: str | None = None,
) -> None:
    """Prime Anthropic cache for WBS/RAID build (templates + parsed brief [+ WBS])."""
    if record.mock:
        return
    parsed = record.session.parsed_brief
    if parsed is None:
        return
    try:
        warm_build_prompt_cache(
            parsed.model_dump_json(indent=2),
            wbs_json=wbs_json,
            use_mock=record.mock,
        )
    except Exception as exc:
        logger.debug("Build prompt cache warmup skipped: %s", exc)


def run_warm_build_cache_job(session_id: str, *, wbs_json: str | None = None) -> None:
    record = get_store().get(session_id)
    if record is None:
        return
    warm_build_prompt_cache_for_record(record, wbs_json=wbs_json)


def create_session(request: CreateSessionRequest) -> SessionRecord:
    session_id = str(uuid.uuid4())[:8]
    output_dir = _session_dir(session_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    session = WorkplanSession(
        session_id=session_id,
        brief_path="web-upload",
    )
    record = SessionRecord(
        session=session,
        output_dir=output_dir,
        mock=request.mock,
        brief_text=request.brief_text,
        user_prompt=request.user_prompt.strip(),
    )
    get_store().create(record)
    return record


def _make_orchestrator(record: SessionRecord) -> OrchestratorAgent:
    provider = get_provider(use_mock=record.mock)
    return OrchestratorAgent(
        provider=provider,
        output_dir=record.output_dir,
        interactive=False,
        auto_approve=False,
        verbose=False,
    )


def run_build_artifacts(session_id: str) -> None:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        return

    store.update(session_id, job_status="running", phase="generating_wbs", error=None)
    try:
        warm_build_prompt_cache_for_record(record)
        orchestrator = _make_orchestrator(record)
        orchestrator.generate_workplan_artifacts(
            record.session,
            user_prompt=record.user_prompt,
        )
        record.session.status = SessionStatus.UNDER_REVIEW
        save_status(record.output_dir, record.session)
        store.update(
            session_id,
            job_status="complete",
            phase="ready_for_review",
            session=record.session,
            error=None,
        )
    except Exception as exc:
        store.update(
            session_id,
            job_status="failed",
            phase="failed",
            error=str(exc),
        )


def run_generation(record: SessionRecord) -> None:
    store = get_store()
    session_id = record.session.session_id
    store.update(session_id, job_status="running", phase="parsing")

    try:
        orchestrator = _make_orchestrator(record)
        orchestrator.parse_brief_only(
            record.session,
            record.brief_text,
            user_prompt=record.user_prompt,
        )
        store.update(session_id, session=record.session)

        open_questions = record.session.parsed_brief.open_questions if record.session.parsed_brief else []
        if open_questions:
            record.session.status = SessionStatus.AWAITING_CONFIRMATION
            save_status(record.output_dir, record.session)
            store.update(
                session_id,
                job_status="running",
                phase="awaiting_confirmation",
                session=record.session,
                error=None,
            )
            warm_build_prompt_cache_for_record(record)
            return

        run_build_artifacts(session_id)
    except Exception as exc:
        store.update(
            session_id,
            job_status="failed",
            phase="failed",
            error=str(exc),
        )


def confirm_open_questions(session_id: str, request: ConfirmQuestionsRequest) -> None:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    if record.phase != "awaiting_confirmation":
        raise ValueError("Session is not awaiting open-question confirmation.")
    if record.session.parsed_brief is None:
        raise ValueError("Parsed brief is not available.")

    resolutions = [
        ResolvedQuestion(question=item.question, answer=item.answer.strip())
        for item in request.answers
    ]
    record.session.parsed_brief.apply_open_question_resolutions(resolutions)
    record.session.status = SessionStatus.PARSED
    save_artifacts(record.output_dir, record.session)
    store.update(session_id, session=record.session)


def get_session(session_id: str) -> SessionResponse | None:
    record = get_store().get(session_id)
    if record is None:
        return None
    return session_to_response(record)


def _compute_revision_diff(
    session: WorkplanSession,
    target: RevisionTarget,
    before_wbs_md: str,
    before_raid_md: str,
) -> RevisionDiff | None:
    assert session.parsed_brief is not None
    if session.wbs is None or session.raid is None:
        return None

    wbs_diff: str | None = None
    raid_diff: str | None = None
    after_wbs_md = render_wbs_markdown(session.wbs, session.parsed_brief)
    after_raid_md = render_raid_markdown(session.raid, session.parsed_brief)

    if target in (RevisionTarget.WBS, RevisionTarget.BOTH):
        wbs_diff = unified_text_diff(before_wbs_md, after_wbs_md, "WBS") or None
    if target in (RevisionTarget.RAID, RevisionTarget.BOTH):
        raid_diff = unified_text_diff(before_raid_md, after_raid_md, "RAID") or None

    if not wbs_diff and not raid_diff:
        return None
    return RevisionDiff(wbs=wbs_diff, raid=raid_diff)


def _validate_review(
    record: SessionRecord,
    request: ReviewRequest,
    *,
    allow_in_progress: bool = False,
) -> None:
    if record.job_status != "complete":
        raise ValueError("Session is not ready for review.")
    if record.review_in_progress and not allow_in_progress:
        raise ValueError("A review action is already in progress.")
    if record.session.status == SessionStatus.APPROVED:
        raise ValueError("Session is already approved.")

    if request.action != "approve":
        unlimited, _ = _revision_limits()
        remaining = _revisions_remaining(record.session.revision_count)
        if not unlimited and remaining == 0:
            raise ValueError("Maximum revision count reached.")
        if not request.feedback.strip():
            raise ValueError("Feedback is required for revisions.")


def apply_review_work(session_id: str, request: ReviewRequest) -> ReviewResponse:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    _validate_review(record, request, allow_in_progress=True)

    session = record.session
    unlimited, _ = _revision_limits()

    if request.action == "approve":
        session.status = SessionStatus.APPROVED
        save_status(record.output_dir, session)
        store.update(session_id, session=session)
        return ReviewResponse(
            session_id=session_id,
            status=session.status,
            revision_count=session.revision_count,
            unlimited_revisions=unlimited,
            revisions_remaining=_revisions_remaining(session.revision_count),
            message="Workplan approved.",
        )

    target_map = {
        "wbs": RevisionTarget.WBS,
        "raid": RevisionTarget.RAID,
        "both": RevisionTarget.BOTH,
    }
    target = target_map[request.action]

    assert session.parsed_brief is not None and session.wbs is not None and session.raid is not None
    before_wbs_md = render_wbs_markdown(session.wbs, session.parsed_brief)
    before_raid_md = render_raid_markdown(session.raid, session.parsed_brief)

    provider = get_provider(use_mock=record.mock)
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=record.output_dir,
        interactive=False,
        auto_approve=False,
        verbose=False,
    )
    orchestrator.apply_revision(session, target, request.feedback)
    revision_diff = _compute_revision_diff(session, target, before_wbs_md, before_raid_md)
    result = ReviewResponse(
        session_id=session_id,
        status=session.status,
        revision_count=session.revision_count,
        unlimited_revisions=unlimited,
        revisions_remaining=_revisions_remaining(session.revision_count),
        message=f"Revision {session.revision_count} applied ({request.action}).",
        diff=revision_diff,
    )
    store.update(session_id, session=session, last_review_result=result, review_error=None)
    return result


def start_revision(session_id: str, request: ReviewRequest) -> str:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    _validate_review(record, request)
    store.update(
        session_id,
        review_in_progress=True,
        phase="revising",
        review_error=None,
    )
    return session_id


def run_revision_job(session_id: str, payload: dict) -> None:
    request = ReviewRequest.model_validate(payload)
    store = get_store()
    try:
        apply_review_work(session_id, request)
    except Exception as exc:
        store.update(session_id, review_error=str(exc))
    finally:
        store.update(
            session_id,
            review_in_progress=False,
            phase="ready_for_review",
        )


def apply_approve(session_id: str, request: ReviewRequest) -> ReviewResponse:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    _validate_review(record, request)
    store.update(session_id, review_in_progress=True, phase="approving", review_error=None)
    try:
        return apply_review_work(session_id, request)
    finally:
        store.update(
            session_id,
            review_in_progress=False,
            phase="ready_for_review",
        )
