import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import RAIDLog
from workplan_agent.models.session import SessionStatus, WorkplanSession
from workplan_agent.models.wbs import WBS

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(default=False),
    )


def render_wbs_markdown(wbs: WBS, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("wbs.md.j2")
    return template.render(
        wbs=wbs,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
    )


def render_raid_markdown(raid: RAIDLog, parsed_brief: ParsedBrief) -> str:
    template = _env().get_template("raid.md.j2")
    return template.render(
        raid=raid,
        client_name=parsed_brief.client_name,
        project_title=parsed_brief.project_title,
    )


def save_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(data, "model_dump"):
        content = data.model_dump(mode="json")
    else:
        content = data
    path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_artifacts(
    output_dir: Path,
    session: WorkplanSession,
) -> None:
    if session.parsed_brief is None:
        raise ValueError("Session has no parsed brief.")

    save_json(output_dir / "parsed_brief.json", session.parsed_brief)

    if session.wbs is not None:
        save_json(output_dir / "wbs.json", session.wbs)
        save_text(
            output_dir / "wbs.md",
            render_wbs_markdown(session.wbs, session.parsed_brief),
        )
        try:
            from workplan_agent.files.deloitte_export import export_wbs_deloitte_docx

            docx_path = output_dir / "wbs.docx"
            docx_path.parent.mkdir(parents=True, exist_ok=True)
            docx_path.write_bytes(
                export_wbs_deloitte_docx(session.wbs, session.parsed_brief)
            )
        except RuntimeError:
            pass

    if session.raid is not None:
        save_json(output_dir / "raid.json", session.raid)
        save_text(
            output_dir / "raid.md",
            render_raid_markdown(session.raid, session.parsed_brief),
        )
        try:
            from workplan_agent.files.deloitte_export import export_raid_deloitte_xlsx

            xlsx_path = output_dir / "raid.xlsx"
            xlsx_path.parent.mkdir(parents=True, exist_ok=True)
            xlsx_path.write_bytes(
                export_raid_deloitte_xlsx(session.raid, session.parsed_brief)
            )
        except (FileNotFoundError, RuntimeError):
            pass


def save_version_snapshot(output_dir: Path, session: WorkplanSession, version: int) -> None:
    if session.parsed_brief is None:
        return
    version_dir = output_dir / "versions" / f"v{version}"
    if session.wbs is not None:
        save_json(version_dir / "wbs.json", session.wbs)
        save_text(
            version_dir / "wbs.md",
            render_wbs_markdown(session.wbs, session.parsed_brief),
        )
    if session.raid is not None:
        save_json(version_dir / "raid.json", session.raid)
        save_text(
            version_dir / "raid.md",
            render_raid_markdown(session.raid, session.parsed_brief),
        )


def save_status(output_dir: Path, session: WorkplanSession) -> None:
    parsed = session.parsed_brief
    status = {
        "session_id": session.session_id,
        "brief_path": session.brief_path,
        "status": session.status.value,
        "revision_count": session.revision_count,
        "version_count": len(session.versions),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "client": parsed.client_name if parsed else "",
            "project": parsed.project_title if parsed else "",
            "objectives_count": len(parsed.objectives) if parsed else 0,
            "wbs_items": len(session.wbs.work_packages) if session.wbs else 0,
            "raid_risks": len(session.raid.risks) if session.raid else 0,
            "raid_actions": len(session.raid.actions) if session.raid else 0,
            "raid_issues": len(session.raid.issues) if session.raid else 0,
            "raid_decisions": len(session.raid.decisions) if session.raid else 0,
            "open_questions": parsed.open_questions if parsed else [],
        },
    }
    save_json(output_dir / "status.json", status)
