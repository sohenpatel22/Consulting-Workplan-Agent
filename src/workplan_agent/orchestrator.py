import uuid
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from workplan_agent.agents.brief_parser import BriefParserAgent
from workplan_agent.agents.raid_generator import RAIDGeneratorAgent
from workplan_agent.agents.revision import RevisionAgent, RevisionTarget
from workplan_agent.agents.wbs_generator import WBSGeneratorAgent
from workplan_agent.config import get_settings
from workplan_agent.llm.base import LLMProvider
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
        interactive: bool = True,
    ) -> None:
        self.provider = provider
        self.output_dir = output_dir
        self.max_revisions = max_revisions or get_settings().max_revisions
        self.interactive = interactive

        self.brief_parser = BriefParserAgent(provider)
        self.wbs_generator = WBSGeneratorAgent(provider)
        self.raid_generator = RAIDGeneratorAgent(provider)
        self.revision_agent = RevisionAgent(provider)

    def run_pipeline(self, brief_path: Path) -> WorkplanSession:
        session = WorkplanSession(
            session_id=str(uuid.uuid4())[:8],
            brief_path=str(brief_path),
        )

        brief_text = brief_path.read_text(encoding="utf-8")
        console.print("[bold]Step 1:[/bold] Parsing client brief...")
        session.parsed_brief = self.brief_parser.run_and_validate(brief_text)
        session.status = SessionStatus.PARSED
        save_artifacts(self.output_dir, session)

        if session.parsed_brief.open_questions:
            console.print("[yellow]Open questions from brief:[/yellow]")
            for q in session.parsed_brief.open_questions:
                console.print(f"  • {q}")

        console.print("[bold]Step 2:[/bold] Generating WBS...")
        session.wbs = self.wbs_generator.run(parsed_brief=session.parsed_brief)
        session.status = SessionStatus.WBS_GENERATED
        session.snapshot("initial_wbs")
        save_artifacts(self.output_dir, session)
        save_version_snapshot(self.output_dir, session, 1)

        console.print("[bold]Step 3:[/bold] Generating RAID log...")
        session.raid = self.raid_generator.run(
            parsed_brief=session.parsed_brief,
            wbs=session.wbs,
        )
        session.status = SessionStatus.RAID_GENERATED
        session.snapshot("initial_raid")
        save_artifacts(self.output_dir, session)

        console.print("[bold]Step 4:[/bold] Review generated artifacts...")
        session.status = SessionStatus.UNDER_REVIEW
        self._display_summary(session)

        if self.interactive:
            self._revision_loop(session)
        else:
            session.status = SessionStatus.APPROVED
            save_status(self.output_dir, session)

        return session

    def _display_summary(self, session: WorkplanSession) -> None:
        parsed = session.parsed_brief
        assert parsed is not None and session.wbs is not None and session.raid is not None

        table = Table(title="Workplan Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_row("Objectives", str(len(parsed.objectives)))
        table.add_row("WBS work packages", str(len(session.wbs.work_packages)))
        table.add_row("Risks", str(len(session.raid.risks)))
        table.add_row("Assumptions", str(len(session.raid.assumptions)))
        table.add_row("Issues", str(len(session.raid.issues)))
        table.add_row("Dependencies", str(len(session.raid.dependencies)))
        console.print(table)

    def _revision_loop(self, session: WorkplanSession) -> None:
        assert session.parsed_brief is not None
        assert session.wbs is not None
        assert session.raid is not None

        while session.revision_count < self.max_revisions:
            console.print(
                Panel(
                    "[a] Approve  [w] WBS feedback  [r] RAID feedback  "
                    "[b] Both  [q] Quit without approving",
                    title="Review",
                )
            )
            choice = console.input("[bold]Your choice:[/bold] ").strip().lower()

            if choice == "a":
                session.status = SessionStatus.APPROVED
                save_artifacts(self.output_dir, session)
                save_status(self.output_dir, session)
                console.print("[green]Workplan approved![/green]")
                return

            if choice == "q":
                console.print("[yellow]Exiting without approval.[/yellow]")
                save_status(self.output_dir, session)
                return

            target_map = {
                "w": RevisionTarget.WBS,
                "r": RevisionTarget.RAID,
                "b": RevisionTarget.BOTH,
            }
            target = target_map.get(choice)
            if target is None:
                console.print("[red]Invalid choice. Try again.[/red]")
                continue

            feedback = console.input("[bold]Enter feedback:[/bold] ").strip()
            if not feedback:
                console.print("[red]Feedback cannot be empty.[/red]")
                continue

            console.print("[bold]Applying revision...[/bold]")
            result = self.revision_agent.run(
                parsed_brief=session.parsed_brief,
                wbs=session.wbs,
                raid=session.raid,
                feedback=feedback,
                target=target,
            )

            if result.wbs is not None:
                session.wbs = result.wbs
            if result.raid is not None:
                session.raid = result.raid

            session.revision_count += 1
            session.snapshot(f"revision_{session.revision_count}")
            save_artifacts(self.output_dir, session)
            save_version_snapshot(
                self.output_dir,
                session,
                len(session.versions),
            )
            self._display_summary(session)
            console.print(
                f"[green]Revision {session.revision_count} applied "
                f"({self.max_revisions - session.revision_count} remaining).[/green]"
            )

        console.print("[yellow]Max revisions reached. Saving current state.[/yellow]")
        save_artifacts(self.output_dir, session)
        save_status(self.output_dir, session)
