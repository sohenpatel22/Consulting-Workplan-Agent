from typing import Literal

from pydantic import BaseModel, Field

from workplan_agent.models.session import SessionStatus

JobStatus = Literal["queued", "running", "complete", "failed"]
ReviewActionName = Literal["approve", "wbs", "raid", "both"]


class CreateSessionRequest(BaseModel):
    brief_text: str = Field(min_length=10)
    user_prompt: str = Field(
        default="",
        description="Optional planner guidance to apply alongside the brief during generation.",
    )
    mock: bool = False


class CreateSessionResponse(BaseModel):
    session_id: str
    job_status: JobStatus


class QuestionAnswer(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class ConfirmQuestionsRequest(BaseModel):
    answers: list[QuestionAnswer] = Field(min_length=1)


class ConfirmQuestionsResponse(BaseModel):
    session_id: str
    status: Literal["accepted"] = "accepted"
    message: str


class ParsePreview(BaseModel):
    client: str = ""
    project: str = ""
    objectives_count: int = 0
    scope_in_count: int = 0


class SessionSummary(BaseModel):
    client: str = ""
    project: str = ""
    objectives_count: int = 0
    wbs_items: int = 0
    raid_risks: int = 0
    raid_actions: int = 0
    raid_issues: int = 0
    raid_decisions: int = 0
    # Deprecated aliases (kept for older clients)
    raid_assumptions: int = 0
    raid_dependencies: int = 0
    open_questions: list[str] = Field(default_factory=list)


class RevisionDiff(BaseModel):
    wbs: str | None = None
    raid: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    job_status: JobStatus
    phase: str
    awaiting_confirmation: bool = False
    confirmation_questions: list[str] = Field(default_factory=list)
    parse_preview: ParsePreview | None = None
    status: SessionStatus | None = None
    revision_count: int = 0
    unlimited_revisions: bool = True
    revisions_remaining: int | None = None
    review_in_progress: bool = False
    review_error: str | None = None
    last_review_message: str | None = None
    last_diff: RevisionDiff | None = None
    error: str | None = None
    summary: SessionSummary | None = None
    parsed_brief: dict | None = None
    wbs: dict | None = None
    raid: dict | None = None
    wbs_markdown: str | None = None
    raid_markdown: str | None = None
    wbs_html: str | None = None
    raid_html: str | None = None


class ReviewRequest(BaseModel):
    action: ReviewActionName
    feedback: str = ""


class ReviewAcceptedResponse(BaseModel):
    session_id: str
    status: Literal["accepted"] = "accepted"
    message: str


class ReviewResponse(BaseModel):
    session_id: str
    status: SessionStatus
    revision_count: int
    unlimited_revisions: bool = True
    revisions_remaining: int | None = None
    message: str
    diff: RevisionDiff | None = None
