import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from workplan_agent.llm.fixtures import PARSED_BRIEF_FIXTURE
from workplan_agent.llm.mock_provider import MockLLMProvider
from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.session import SessionStatus, WorkplanSession
from workplan_agent.orchestrator import OrchestratorAgent

runner = CliRunner()
SAMPLES = Path(__file__).parent.parent / "samples" / "client_brief.md"


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    return tmp_path / "out"


def test_generate_workplan_artifacts_notifies_per_step(output_dir: Path) -> None:
    provider = MockLLMProvider()
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=output_dir,
        verbose=False,
    )
    session = WorkplanSession(session_id="t1", brief_path="test")
    session.parsed_brief = ParsedBrief.model_validate(PARSED_BRIEF_FIXTURE)
    ready: list[str] = []
    orchestrator.generate_workplan_artifacts(
        session,
        on_artifact_ready=ready.append,
    )
    assert ready == ["wbs", "raid", "raci", "status"]


def test_orchestrator_pipeline(output_dir: Path) -> None:
    provider = MockLLMProvider()
    orchestrator = OrchestratorAgent(
        provider=provider,
        output_dir=output_dir,
    )
    session = orchestrator.run_pipeline(SAMPLES)

    assert session.parsed_brief is not None
    assert session.wbs is not None
    assert session.raid is not None
    assert session.status == SessionStatus.UNDER_REVIEW

    assert (output_dir / "parsed_brief.json").exists()
    assert (output_dir / "wbs.json").exists()
    assert (output_dir / "wbs.md").exists()
    assert (output_dir / "raid.json").exists()
    assert (output_dir / "raid.md").exists()
    assert (output_dir / "status.json").exists()
    assert (output_dir / "versions" / "v1").exists()


def test_cli_run_mock(output_dir: Path) -> None:
    from workplan_agent.cli import app

    result = runner.invoke(
        app,
        [
            "run",
            "--brief",
            str(SAMPLES),
            "--output",
            str(output_dir),
            "--mock",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (output_dir / "status.json").exists()

    status = json.loads((output_dir / "status.json").read_text())
    assert status["status"] == "under_review"
    assert status["summary"]["wbs_items"] > 0
    assert status["summary"]["raid_risks"] >= 3
