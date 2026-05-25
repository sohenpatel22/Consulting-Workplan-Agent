from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from workplan_agent.config import ProfileName
from workplan_agent.llm import get_provider
from workplan_agent.orchestrator import OrchestratorAgent

app = typer.Typer(
    name="workplan",
    help="Consulting workplan agent: brief → WBS + RAID with revision loop.",
    no_args_is_help=True,
)
console = Console()


@app.command("info")
def show_version() -> None:
    """Show package version."""
    from workplan_agent import __version__

    console.print(__version__)


@app.command("run")
def run_pipeline(
    brief: Path = typer.Option(
        ...,
        "--brief",
        "-b",
        help="Path to client brief (.md or .txt)",
        exists=True,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("./out"),
        "--output",
        "-o",
        help="Output directory for artifacts",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        help="Use mock LLM provider (offline demo, no API keys)",
    ),
    max_revisions: Optional[int] = typer.Option(
        None,
        "--max-revisions",
        help="Maximum revision iterations (default from env/config)",
    ),
    profile: ProfileName = typer.Option(
        "balanced",
        "--profile",
        help="Model profile: fast | balanced | accurate",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip review loop and save artifacts immediately",
    ),
) -> None:
    """Run the full workplan pipeline: parse brief → WBS → RAID → review."""
    try:
        provider = get_provider(use_mock=mock)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    output.mkdir(parents=True, exist_ok=True)
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=output,
        max_revisions=max_revisions,
        interactive=not non_interactive,
    )

    console.print(f"[bold]Workplan Agent[/bold] — session starting")
    console.print(f"  Brief:  {brief}")
    console.print(f"  Output: {output}")
    console.print(f"  Mode:   {'mock' if mock else profile}")

    session = orchestrator.run_pipeline(brief)
    console.print(f"\n[bold]Done.[/bold] Session {session.session_id} → {session.status.value}")
    console.print(f"Artifacts saved to {output.resolve()}")


if __name__ == "__main__":
    app()
