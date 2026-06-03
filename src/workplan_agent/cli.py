from pathlib import Path
import typer
from rich.console import Console

from workplan_agent.config import get_settings
from workplan_agent.llm import get_provider
from workplan_agent.orchestrator import OrchestratorAgent

app = typer.Typer(
    name="workplan",
    help="Consulting workplan agent: generate workplan artifacts from a client brief.",
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
    prompt: str = typer.Option(
        "",
        "--prompt",
        "-p",
        help="Optional planner guidance applied alongside the brief during generation",
    ),
) -> None:
    """Run generation: parse brief → WBS → RAID → stakeholder map → status report."""
    try:
        provider = get_provider(use_mock=mock)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    output.mkdir(parents=True, exist_ok=True)
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=output,
    )

    console.print(f"[bold]Workplan Agent[/bold] — session starting")
    console.print(f"  Brief:  {brief}")
    console.print(f"  Output: {output}")
    model = get_settings().resolve_model() if not mock else "mock"
    console.print(f"  Model:  {model}")

    session = orchestrator.run_pipeline(brief, user_prompt=prompt.strip())
    console.print(f"\n[bold]Done.[/bold] Session {session.session_id} → {session.status.value}")
    console.print(f"Artifacts saved to {output.resolve()}")


@app.command("serve")
def serve_web(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes"),
) -> None:
    """Start the web UI and REST API."""
    import uvicorn

    console.print(f"[bold]Workplan Agent[/bold] — http://{host}:{port}")
    uvicorn.run(
        "workplan_agent.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
