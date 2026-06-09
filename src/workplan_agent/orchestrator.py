import uuid
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.table import Table

from workplan_agent.agents.brief_parser import BriefParserAgent
from workplan_agent.models.brief import ResolvedQuestion
from workplan_agent.prompts import build_generation_guidance
from workplan_agent.agents.raid_generator import RAIDGeneratorAgent
from workplan_agent.agents.wbs_generator import WBSGeneratorAgent
from workplan_agent.agents.raci_generator import RaciMatrixGeneratorAgent
from workplan_agent.agents.status_generator import StatusReportGeneratorAgent
from workplan_agent.agents.revision import RevisionAgent, RevisionTarget
from workplan_agent.config import get_settings
from workplan_agent.llm.base import LLMProvider
from workplan_agent.models.artifact_versions import init_after_generation
from workplan_agent.models.session import SessionStatus, WorkplanSession
from workplan_agent.render import (
    save_artifacts,
    save_status,
    save_version_snapshot,
)

console = Console()


class OrchestratorAgent:
    def __init__(
        self,
        provider: LLMProvider,
        output_dir: Path,
        max_revisions: int | None = None,
        verbose: bool = True,
    ) -> None:
        self.provider = provider
        self.output_dir = output_dir
        self.max_revisions = max_revisions or get_settings().max_revisions
        self.verbose = verbose

        self.brief_parser = BriefParserAgent(provider)
        self.wbs_generator = WBSGeneratorAgent(provider)
        self.raid_generator = RAIDGeneratorAgent(provider)
        self.raci_generator = RaciMatrixGeneratorAgent(provider)
        self.status_generator = StatusReportGeneratorAgent(provider)
        self.revision_agent = RevisionAgent(provider)

    def _log(self, message: str) -> None:
        if self.verbose:
            console.print(message)

    def run_pipeline(
        self,
        brief_path: Path,
        *,
        user_prompt: str = "",
    ) -> WorkplanSession:
        brief_text = brief_path.read_text(encoding="utf-8")
        return self.run_pipeline_from_text(
            brief_text,
            brief_label=str(brief_path),
            user_prompt=user_prompt,
        )

    def run_pipeline_from_text(
        self,
        brief_text: str,
        brief_label: str = "web-upload",
        session_id: str | None = None,
        user_prompt: str = "",
    ) -> WorkplanSession:
        session = WorkplanSession(
            session_id=session_id or str(uuid.uuid4())[:8],
            brief_path=brief_label,
        )
        self.generate_artifacts(session, brief_text, user_prompt=user_prompt)
        self._log("[bold]Done:[/bold] Artifacts ready for review in the web UI.")
        session.status = SessionStatus.UNDER_REVIEW
        self._display_summary(session)
        save_status(self.output_dir, session)
        return session

    def _warm_raid_build_cache(self, session: WorkplanSession) -> None:
        parsed = session.parsed_brief
        if parsed is None or session.wbs is None or session.raci_matrix is None:
            return
        warm_raid = getattr(self.provider, "warm_raid_build_prefix", None)
        if not callable(warm_raid):
            return
        warm_raid(
            parsed.model_dump_json(indent=2),
            session.wbs.model_dump_json(indent=2),
            session.raci_matrix.model_dump_json(indent=2),
        )

    def _generation_guidance(self, session: WorkplanSession, user_prompt: str) -> str:
        parsed = session.parsed_brief
        confirmed: list[tuple[str, str]] | None = None
        if parsed and parsed.resolved_open_questions:
            confirmed = [(r.question, r.answer) for r in parsed.resolved_open_questions]
        return build_generation_guidance(user_prompt, confirmed_answers=confirmed)

    def parse_brief_only(
        self,
        session: WorkplanSession,
        brief_text: str,
        *,
        user_prompt: str = "",
    ) -> None:
        self._log("[bold]Step 1:[/bold] Parsing client brief...")
        session.parsed_brief = self.brief_parser.run_and_validate(
            brief_text,
            user_prompt=user_prompt,
        )
        session.status = SessionStatus.PARSED
        save_artifacts(self.output_dir, session)

        if session.parsed_brief.open_questions:
            self._log("[yellow]Open questions from brief:[/yellow]")
            for q in session.parsed_brief.open_questions:
                self._log(f"  • {q}")

    def _auto_resolve_open_questions(self, session: WorkplanSession) -> None:
        assert session.parsed_brief is not None
        resolutions = [
            ResolvedQuestion(
                question=question,
                answer=(
                    "Proceed using reasonable assumptions stated or implied in the brief."
                ),
            )
            for question in session.parsed_brief.open_questions
        ]
        session.parsed_brief.apply_open_question_resolutions(resolutions)

    def generate_workplan_artifacts(
        self,
        session: WorkplanSession,
        *,
        user_prompt: str = "",
        on_artifact_ready: Callable[[str], None] | None = None,
    ) -> None:
        if session.parsed_brief is None:
            raise ValueError("Brief must be parsed before generating artifacts.")

        guidance = self._generation_guidance(session, user_prompt)

        def _notify(artifact: str) -> None:
            if on_artifact_ready is not None:
                on_artifact_ready(artifact)

        self._log("[bold]Step 2:[/bold] Generating WBS...")
        session.wbs = self.wbs_generator.run(
            parsed_brief=session.parsed_brief,
            user_prompt=guidance,
        )
        _notify("wbs")

        self._log("[bold]Step 3:[/bold] Generating RACI matrix...")
        session.raci_matrix = self.raci_generator.run(
            parsed_brief=session.parsed_brief,
            wbs=session.wbs,
            user_prompt=guidance,
        )
        _notify("raci")
        self._warm_raid_build_cache(session)

        self._log("[bold]Step 4:[/bold] Generating RAID log...")
        session.raid = self.raid_generator.run(
            parsed_brief=session.parsed_brief,
            wbs=session.wbs,
            raci_matrix=session.raci_matrix,
            user_prompt=guidance,
        )
        _notify("raid")

        self._log("[bold]Step 5:[/bold] Generating Weekly Status Report...")
        session.status_report = self.status_generator.run(
            parsed_brief=session.parsed_brief,
            wbs=session.wbs,
            raci_matrix=session.raci_matrix,
            raid=session.raid,
            user_prompt=guidance,
        )
        _notify("status")

        session.status = SessionStatus.RAID_GENERATED
        init_after_generation(session)
        session.snapshot("initial_generation")
        save_artifacts(self.output_dir, session)
        save_version_snapshot(self.output_dir, session, 1)

    def generate_artifacts(
        self,
        session: WorkplanSession,
        brief_text: str,
        *,
        user_prompt: str = "",
    ) -> None:
        self.parse_brief_only(session, brief_text, user_prompt=user_prompt)

        if session.parsed_brief:
            from workplan_agent.confirmation import build_confirmation_questions

            pending = build_confirmation_questions(
                session.parsed_brief,
                brief_text=brief_text,
            )
            session.parsed_brief.open_questions = [item.question for item in pending]
            self._auto_resolve_open_questions(session)
            save_artifacts(self.output_dir, session)

        self.generate_workplan_artifacts(session, user_prompt=user_prompt)

    def approve_session(self, session: WorkplanSession) -> WorkplanSession:
        session.status = SessionStatus.APPROVED
        save_artifacts(self.output_dir, session)
        save_status(self.output_dir, session)
        return session

    def apply_revision(
        self,
        session: WorkplanSession,
        target: RevisionTarget,
        feedback: str,
    ) -> WorkplanSession:
        if self.max_revisions > 0 and session.revision_count >= self.max_revisions:
            raise ValueError("Maximum revision count reached.")
        if session.parsed_brief is None or session.wbs is None or session.raid is None:
            raise ValueError("Session is missing generated artifacts.")
        if not feedback.strip():
            raise ValueError("Feedback cannot be empty.")

        result = self.revision_agent.run(
            parsed_brief=session.parsed_brief,
            wbs=session.wbs,
            raid=session.raid,
            raci_matrix=session.raci_matrix,
            status_report=session.status_report,
            feedback=feedback.strip(),
            target=target,
        )
        if result.wbs is not None:
            session.wbs = result.wbs
        if result.raid is not None:
            session.raid = result.raid
        if result.raci_matrix is not None:
            session.raci_matrix = result.raci_matrix
        if result.status_report is not None:
            session.status_report = result.status_report

        session.revision_count += 1
        session.snapshot(f"revision_{session.revision_count}")
        save_artifacts(self.output_dir, session, refresh_quality_gates=False)
        save_version_snapshot(
            self.output_dir,
            session,
            len(session.versions),
        )
        save_status(self.output_dir, session)
        return session

    def _display_summary(self, session: WorkplanSession) -> None:
        if not self.verbose:
            return
        parsed = session.parsed_brief
        assert parsed is not None and session.wbs is not None and session.raid is not None

        table = Table(title="Workplan Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Objectives", str(len(parsed.objectives)))
        table.add_row("WBS work packages", str(len(session.wbs.work_packages)))
        table.add_row("Risks", str(len(session.raid.risks)))
        table.add_row("Actions", str(len(session.raid.actions)))
        table.add_row("Issues", str(len(session.raid.issues)))
        table.add_row("Decisions", str(len(session.raid.decisions)))
        if session.raci_matrix is not None:
            table.add_row("RACI activities", str(len(session.raci_matrix.rows)))
        if session.status_report is not None:
            table.add_row("Status report milestones", str(len(session.status_report.milestones)))
        console.print(table)
