import logging
import uuid
from pathlib import Path

from workplan_agent.agents.revision import RevisionTarget
from workplan_agent.api.schemas import (
    ConfirmationQuestionItem,
    ConfirmQuestionsRequest,
    CreateSessionRequest,
    ParsePreview,
    ReviewRequest,
    ReviewResponse,
    RevisionDiff,
    SessionResponse,
    SessionSummary,
)
from workplan_agent.confirmation import build_confirmation_questions
from workplan_agent.models.artifact_versions import (
    REVISION_ARTIFACTS,
    after_multi_revision,
    after_quality_check,
    after_revision,
    compute_stale_artifacts,
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
    render_stakeholder_markdown,
    render_status_markdown,
    render_quality_gates_markdown,
    generate_quality_gates,
    save_artifacts,
    save_quality_gates,
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
    if (
        session.quality_gates is None
        and session.wbs is not None
        and session.raid is not None
        and session.stakeholder_map is not None
        and session.status_report is not None
    ):
        session.quality_gates = generate_quality_gates(session)
    return SessionSummary(
        client=parsed.client_name if parsed else "",
        project=parsed.project_title if parsed else "",
        objectives_count=len(parsed.objectives) if parsed else 0,
        wbs_items=len(session.wbs.work_packages) if session.wbs else 0,
        raid_risks=len(session.raid.risks) if session.raid else 0,
        raid_actions=len(session.raid.actions) if session.raid else 0,
        raid_issues=len(session.raid.issues) if session.raid else 0,
        raid_decisions=len(session.raid.decisions) if session.raid else 0,
        stakeholders_count=len(session.stakeholder_map.stakeholders) if session.stakeholder_map else 0,
        status_milestones_count=len(session.status_report.milestones) if session.status_report else 0,
        quality_gates_passed=sum(1 for i in session.quality_gates.items if i.passed) if session.quality_gates else 0,
        quality_gates_total=len(session.quality_gates.items) if session.quality_gates else 0,
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
    stakeholder_map = None
    status_report = None
    quality_gates = None
    wbs_markdown = None
    raid_markdown = None
    stakeholder_markdown = None
    status_markdown = None
    quality_gates_markdown = None
    wbs_html = None
    raid_html = None
    stakeholder_html = None
    status_html = None
    quality_gates_html = None
    summary = None

    parsed = session.parsed_brief
    if parsed is not None:
        parsed_brief = parsed.model_dump(mode="json")
    if session.wbs is not None:
        wbs = session.wbs.model_dump(mode="json")
    if session.raid is not None:
        raid = session.raid.model_dump(mode="json")
    if session.stakeholder_map is not None:
        stakeholder_map = session.stakeholder_map.model_dump(mode="json")
    if session.status_report is not None:
        status_report = session.status_report.model_dump(mode="json")

    if (
        session.wbs is not None
        and session.raid is not None
        and session.stakeholder_map is not None
        and session.status_report is not None
        and session.quality_gates is None
    ):
        session.quality_gates = generate_quality_gates(session)

    if session.quality_gates is not None and parsed is not None:
        quality_gates = session.quality_gates.model_dump(mode="json")
        quality_gates_markdown = render_quality_gates_markdown(session.quality_gates, parsed)
        quality_gates_html = markdown_to_html_body(quality_gates_markdown)

    has_artifacts = any(
        (
            session.wbs is not None,
            session.raid is not None,
            session.stakeholder_map is not None,
            session.status_report is not None,
        )
    )
    if parsed is not None and has_artifacts:
        summary = _build_summary(session)
        if session.wbs is not None:
            wbs_markdown = render_wbs_markdown(session.wbs, parsed)
            wbs_html = markdown_to_html_body(wbs_markdown)
        if session.raid is not None:
            raid_markdown = render_raid_markdown(session.raid, parsed)
            raid_html = markdown_to_html_body(raid_markdown)
        if session.stakeholder_map is not None:
            stakeholder_markdown = render_stakeholder_markdown(session.stakeholder_map, parsed)
            stakeholder_html = markdown_to_html_body(stakeholder_markdown)
        if session.status_report is not None:
            status_markdown = render_status_markdown(session.status_report, parsed)
            status_html = markdown_to_html_body(status_markdown)

    awaiting_confirmation = record.phase == "awaiting_confirmation"
    confirmation_questions: list[ConfirmationQuestionItem] = []
    parse_preview = None
    if session.parsed_brief is not None:
        parse_preview = _parse_preview(session)
        if awaiting_confirmation and record.pending_confirmation:
            confirmation_questions = [
                ConfirmationQuestionItem(
                    question=item.question,
                    suggested_answers=list(item.suggested_answers),
                )
                for item in record.pending_confirmation
            ]

    last_review = record.last_review_result
    stale = compute_stale_artifacts(session)
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
        revisions_in_progress=sorted(record.revisions_in_progress),
        quality_gates_stale=record.quality_gates_stale,
        artifact_versions=dict(session.artifact_versions),
        artifact_based_on={k: dict(v) for k, v in session.artifact_based_on.items()},
        stale_artifacts=stale,
        review_error=record.review_error,
        last_review_message=last_review.message if last_review else None,
        last_diff=last_review.diff if last_review else None,
        error=record.error,
        summary=summary,
        parsed_brief=parsed_brief,
        wbs=wbs,
        raid=raid,
        stakeholder_map=stakeholder_map,
        status_report=status_report,
        quality_gates=quality_gates,
        wbs_markdown=wbs_markdown,
        raid_markdown=raid_markdown,
        stakeholder_markdown=stakeholder_markdown,
        status_markdown=status_markdown,
        quality_gates_markdown=quality_gates_markdown,
        wbs_html=wbs_html,
        raid_html=raid_html,
        stakeholder_html=stakeholder_html,
        status_html=status_html,
        quality_gates_html=quality_gates_html,
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


_BUILD_PHASE_AFTER_ARTIFACT = {
    "wbs": "generating_raid",
    "raid": "generating_stakeholder",
    "stakeholder": "generating_status",
    "status": "ready_for_review",
}


def _publish_build_progress(
    session_id: str,
    record: SessionRecord,
    *,
    artifact: str,
) -> None:
    save_artifacts(record.output_dir, record.session, refresh_quality_gates=False)
    get_store().update(
        session_id,
        phase=_BUILD_PHASE_AFTER_ARTIFACT[artifact],
        session=record.session,
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

        def on_artifact_ready(artifact: str) -> None:
            _publish_build_progress(session_id, record, artifact=artifact)

        orchestrator.generate_workplan_artifacts(
            record.session,
            user_prompt=record.user_prompt,
            on_artifact_ready=on_artifact_ready,
        )
        record.session.status = SessionStatus.UNDER_REVIEW
        save_artifacts(record.output_dir, record.session)
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

        parsed = record.session.parsed_brief
        assert parsed is not None
        pending = build_confirmation_questions(parsed)
        parsed.open_questions = [item.question for item in pending]
        record.session.status = SessionStatus.AWAITING_CONFIRMATION
        save_status(record.output_dir, record.session)
        store.update(
            session_id,
            job_status="running",
            phase="awaiting_confirmation",
            session=record.session,
            pending_confirmation=pending,
            error=None,
        )
        warm_build_prompt_cache_for_record(record)
        return
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
    store.update(
        session_id,
        session=record.session,
        pending_confirmation=[],
    )


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
    before_stakeholder_md: str,
    before_status_md: str,
) -> RevisionDiff | None:
    assert session.parsed_brief is not None
    if session.wbs is None or session.raid is None:
        return None

    wbs_diff: str | None = None
    raid_diff: str | None = None
    stakeholder_diff: str | None = None
    status_diff: str | None = None

    after_wbs_md = render_wbs_markdown(session.wbs, session.parsed_brief)
    after_raid_md = render_raid_markdown(session.raid, session.parsed_brief)
    after_stakeholder_md = render_stakeholder_markdown(session.stakeholder_map, session.parsed_brief) if session.stakeholder_map else ""
    after_status_md = render_status_markdown(session.status_report, session.parsed_brief) if session.status_report else ""

    if target in (RevisionTarget.WBS, RevisionTarget.BOTH, RevisionTarget.ALL):
        wbs_diff = unified_text_diff(before_wbs_md, after_wbs_md, "WBS") or None
    if target in (RevisionTarget.RAID, RevisionTarget.BOTH, RevisionTarget.ALL):
        raid_diff = unified_text_diff(before_raid_md, after_raid_md, "RAID") or None
    if target in (RevisionTarget.STAKEHOLDER, RevisionTarget.ALL):
        stakeholder_diff = unified_text_diff(before_stakeholder_md, after_stakeholder_md, "Stakeholder Map") or None
    if target in (RevisionTarget.STATUS, RevisionTarget.ALL):
        status_diff = unified_text_diff(before_status_md, after_status_md, "Weekly Status Report") or None

    if not wbs_diff and not raid_diff and not stakeholder_diff and not status_diff:
        return None
    return RevisionDiff(
        wbs=wbs_diff,
        raid=raid_diff,
        stakeholder_map=stakeholder_diff,
        status_report=status_diff,
    )


def _validate_review(
    record: SessionRecord,
    request: ReviewRequest,
    *,
    allow_in_progress: bool = False,
) -> None:
    if record.job_status != "complete":
        raise ValueError("Session is not ready for review.")
    if record.session.status == SessionStatus.APPROVED:
        raise ValueError("Session is already approved.")

    if request.action == "quality_check":
        return

    if request.action == "approve":
        return

    if request.action in REVISION_ARTIFACTS:
        if request.action in record.revisions_in_progress and not allow_in_progress:
            raise ValueError(
                f"A revision for {request.action} is already in progress."
            )
        unlimited, _ = _revision_limits()
        remaining = _revisions_remaining(record.session.revision_count)
        if not unlimited and remaining == 0:
            raise ValueError("Maximum revision count reached.")
        if not request.feedback.strip():
            raise ValueError("Feedback is required for revisions.")
        return

    if request.action in ("both", "all"):
        if not allow_in_progress and record.revisions_in_progress:
            raise ValueError("A revision action is already in progress.")
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

    if request.action == "quality_check":
        save_quality_gates(record.output_dir, session)
        after_quality_check(session)
        save_status(record.output_dir, session)
        store.update(
            session_id,
            session=session,
            quality_gates_stale=False,
            review_error=None,
        )
        return ReviewResponse(
            session_id=session_id,
            status=session.status,
            revision_count=session.revision_count,
            unlimited_revisions=unlimited,
            revisions_remaining=_revisions_remaining(session.revision_count),
            message="Quality gates updated.",
        )

    target_map = {
        "wbs": RevisionTarget.WBS,
        "raid": RevisionTarget.RAID,
        "stakeholder": RevisionTarget.STAKEHOLDER,
        "status": RevisionTarget.STATUS,
        "both": RevisionTarget.BOTH,
        "all": RevisionTarget.ALL,
    }
    target = target_map[request.action]

    assert session.parsed_brief is not None and session.wbs is not None and session.raid is not None
    before_wbs_md = render_wbs_markdown(session.wbs, session.parsed_brief)
    before_raid_md = render_raid_markdown(session.raid, session.parsed_brief)
    before_stakeholder_md = render_stakeholder_markdown(session.stakeholder_map, session.parsed_brief) if session.stakeholder_map else ""
    before_status_md = render_status_markdown(session.status_report, session.parsed_brief) if session.status_report else ""

    upstream_snapshot = {
        key: session.artifact_versions.get(key, 0) for key in REVISION_ARTIFACTS
    }

    provider = get_provider(use_mock=record.mock)
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=record.output_dir,
        interactive=False,
        auto_approve=False,
        verbose=False,
    )
    orchestrator.apply_revision(session, target, request.feedback)
    if request.action in REVISION_ARTIFACTS:
        after_revision(session, request.action, upstream_snapshot)
    elif request.action == "both":
        after_multi_revision(session, ["wbs", "raid"], upstream_snapshot)
    elif request.action == "all":
        after_multi_revision(
            session,
            list(REVISION_ARTIFACTS),
            upstream_snapshot,
        )
    revision_diff = _compute_revision_diff(
        session,
        target,
        before_wbs_md,
        before_raid_md,
        before_stakeholder_md,
        before_status_md,
    )
    result = ReviewResponse(
        session_id=session_id,
        status=session.status,
        revision_count=session.revision_count,
        unlimited_revisions=unlimited,
        revisions_remaining=_revisions_remaining(session.revision_count),
        message=f"Revision {session.revision_count} applied ({request.action}).",
        diff=revision_diff,
    )
    store.update(
        session_id,
        session=session,
        last_review_result=result,
        review_error=None,
        quality_gates_stale=True,
    )
    return result


def _revision_artifact(request: ReviewRequest) -> str:
    if request.action in REVISION_ARTIFACTS:
        return request.action
    if request.action == "both":
        return "both"
    if request.action == "all":
        return "all"
    raise ValueError(f"Not a revision action: {request.action}")


def start_revision(session_id: str, request: ReviewRequest) -> str:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    _validate_review(record, request)
    artifact = _revision_artifact(request)
    store.add_revision_in_progress(session_id, artifact)
    store.update(
        session_id,
        phase="revising",
        review_error=None,
    )
    return session_id


def run_revision_job(session_id: str, payload: dict) -> None:
    request = ReviewRequest.model_validate(payload)
    artifact = _revision_artifact(request)
    store = get_store()
    try:
        apply_review_work(session_id, request)
    except Exception as exc:
        store.update(session_id, review_error=str(exc))
    finally:
        store.remove_revision_in_progress(session_id, artifact)
        record = store.get(session_id)
        if record is not None and not record.revisions_in_progress:
            store.update(session_id, phase="ready_for_review")


def apply_approve(session_id: str, request: ReviewRequest) -> ReviewResponse:
    store = get_store()
    record = store.get(session_id)
    if record is None:
        raise KeyError(f"Session {session_id} not found.")
    _validate_review(record, request)
    store.update(session_id, phase="approving", review_error=None)
    try:
        return apply_review_work(session_id, request)
    finally:
        store.update(session_id, phase="ready_for_review")
