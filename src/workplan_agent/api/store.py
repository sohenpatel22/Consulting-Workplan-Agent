from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from workplan_agent.api.schemas import JobStatus, ReviewResponse
from workplan_agent.models.brief import ConfirmationQuestion
from workplan_agent.models.session import WorkplanSession


@dataclass
class SessionRecord:
    session: WorkplanSession
    output_dir: Path
    job_status: JobStatus = "queued"
    phase: str = "queued"
    error: str | None = None
    mock: bool = False
    brief_text: str = ""
    user_prompt: str = ""
    revisions_in_progress: set[str] = field(default_factory=set)
    quality_gates_stale: bool = False
    review_error: str | None = None
    last_review_result: ReviewResponse | None = None
    pending_confirmation: list[ConfirmationQuestion] = field(default_factory=list)

    @property
    def review_in_progress(self) -> bool:
        return bool(self.revisions_in_progress)


class SessionStore:
    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create(self, record: SessionRecord) -> None:
        with self._lock:
            self._records[record.session.session_id] = record

    def get(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self._records.get(session_id)

    def update(self, session_id: str, **kwargs: object) -> SessionRecord | None:
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                return None
            for key, value in kwargs.items():
                setattr(record, key, value)
            return record

    def add_revision_in_progress(self, session_id: str, artifact: str) -> None:
        with self._lock:
            record = self._records.get(session_id)
            if record is not None:
                record.revisions_in_progress.add(artifact)

    def remove_revision_in_progress(self, session_id: str, artifact: str) -> None:
        with self._lock:
            record = self._records.get(session_id)
            if record is not None:
                record.revisions_in_progress.discard(artifact)


_store: SessionStore | None = None


def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store


def reset_store() -> None:
    global _store
    _store = SessionStore()
