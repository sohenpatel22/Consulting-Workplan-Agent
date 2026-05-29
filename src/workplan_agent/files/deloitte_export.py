"""Export WBS and RAID artifacts using APS1049 Deloitte deliverable templates."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from workplan_agent.models.brief import ParsedBrief
from workplan_agent.models.raid import ActionEntry, DecisionEntry, IssueEntry, RAIDLog, RiskEntry
from workplan_agent.models.wbs import WBS, WorkPackage

_PACKAGE_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "deloitte"
RAID_TEMPLATE_PATH = _PACKAGE_TEMPLATES / "raid_log_template.xlsx"

_DETAIL_SHEET = "RAID Log - Detail"
_SIMPLE_SHEET = "RAID Log - simple"
_DETAIL_DATA_START_ROW = 7
_SIMPLE_DATA_START_ROW = 6


def resolve_raid_template(path: Path | None = None) -> Path:
    if path is not None:
        if not path.is_file():
            raise FileNotFoundError(f"RAID template not found: {path}")
        return path
    if RAID_TEMPLATE_PATH.is_file():
        return RAID_TEMPLATE_PATH
    repo_root = Path.cwd()
    for candidate in (
        repo_root / "APS1049_Team 2-RAID Log-Template .xlsx",
        repo_root / "templates" / "deloitte" / "raid_log_template.xlsx",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "RAID Excel template not found. Expected bundled template or "
        "APS1049_Team 2-RAID Log-Template .xlsx in the project root."
    )


def export_wbs_deloitte_docx(wbs: WBS, parsed_brief: ParsedBrief) -> bytes:
    """Build a WBS Word document matching the Deloitte table layout."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        raise RuntimeError("DOCX export is not installed.") from exc

    document = Document()
    document.add_heading("Work Breakdown Structure", level=0)
    document.add_paragraph(f"Project: {parsed_brief.project_title}")
    document.add_paragraph(f"Client: {parsed_brief.client_name}")

    headers = [
        "Level",
        "WBS Code",
        "WBS Element Title",
        "Description / Scope of Work",
        "Key Deliverable",
        "Owner",
        "Duration",
        "Dependencies",
    ]
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for col_idx, header in enumerate(headers):
        table.rows[0].cells[col_idx].text = header

    for wp in sorted(wbs.work_packages, key=_wbs_sort_key):
        row = table.add_row().cells
        row[0].text = str(wp.level)
        row[1].text = wp.wbs_code
        row[2].text = wp.wbs_element_title
        row[3].text = wp.description_scope
        row[4].text = wp.key_deliverable
        row[5].text = wp.owner
        row[6].text = wp.estimated_duration
        row[7].text = ", ".join(wp.dependencies)

    for para in document.paragraphs:
        for run in para.runs:
            run.font.size = Pt(11)

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def export_raid_deloitte_xlsx(
    raid: RAIDLog,
    parsed_brief: ParsedBrief,
    template_path: Path | None = None,
) -> bytes:
    """Fill the Deloitte RAID Excel template (detail + simple sheets)."""
    path = resolve_raid_template(template_path)
    workbook = load_workbook(path)
    project = parsed_brief.project_title or "Project"
    today = date.today().strftime("%Y-%m-%d")

    if _DETAIL_SHEET in workbook.sheetnames:
        _fill_raid_detail_sheet(workbook[_DETAIL_SHEET], raid, project, today)
    if _SIMPLE_SHEET in workbook.sheetnames:
        _fill_raid_simple_sheet(workbook[_SIMPLE_SHEET], raid, project, today)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _wbs_sort_key(wp: WorkPackage) -> tuple[int, ...]:
    parts: list[int] = []
    for segment in wp.wbs_code.replace("-", ".").split("."):
        if segment.isdigit():
            parts.append(int(segment))
        else:
            parts.append(0)
    return tuple(parts)


def _set_cell(ws: Worksheet, row: int, col: int, value: object) -> None:
    ws.cell(row=row, column=col, value=value)


def _clear_row_range(ws: Worksheet, start_row: int, end_row: int, max_col: int) -> None:
    for row in range(start_row, end_row + 1):
        for col in range(1, max_col + 1):
            ws.cell(row=row, column=col, value=None)


def _fill_raid_detail_sheet(
    ws: Worksheet,
    raid: RAIDLog,
    project: str,
    today: str,
) -> None:
    _set_cell(ws, 4, 3, project)
    _set_cell(ws, 1, 9, today)

    max_items = max(
        len(raid.risks),
        len(raid.actions),
        len(raid.issues),
        len(raid.decisions),
        1,
    )
    end_row = _DETAIL_DATA_START_ROW + max(max_items, 6) + 5
    _clear_row_range(ws, _DETAIL_DATA_START_ROW, end_row, 32)

    for index in range(max_items):
        row = _DETAIL_DATA_START_ROW + index
        if index < len(raid.risks):
            _write_detail_risk(ws, row, raid.risks[index])
        if index < len(raid.actions):
            _write_detail_action(ws, row, raid.actions[index])
        if index < len(raid.issues):
            _write_detail_issue(ws, row, raid.issues[index])
        if index < len(raid.decisions):
            _write_detail_decision(ws, row, raid.decisions[index])


def _write_detail_risk(ws: Worksheet, row: int, item: RiskEntry) -> None:
    _set_cell(ws, row, 1, item.id)
    _set_cell(ws, row, 2, item.title)
    _set_cell(ws, row, 3, item.description)
    _set_cell(ws, row, 4, item.status)
    _set_cell(ws, row, 5, item.mitigation)
    _set_cell(ws, row, 6, item.owner)
    _set_cell(ws, row, 7, ", ".join(item.wbs_links))
    _set_cell(ws, row, 8, item.probability)
    _set_cell(ws, row, 9, item.priority)


def _write_detail_action(ws: Worksheet, row: int, item: ActionEntry) -> None:
    _set_cell(ws, row, 11, item.id)
    _set_cell(ws, row, 12, item.title)
    _set_cell(ws, row, 13, item.description)
    _set_cell(ws, row, 14, item.status_update)
    _set_cell(ws, row, 15, item.status)
    _set_cell(ws, row, 16, item.owner)
    _set_cell(ws, row, 17, ", ".join(item.wbs_links))
    _set_cell(ws, row, 18, item.priority)


def _write_detail_issue(ws: Worksheet, row: int, item: IssueEntry) -> None:
    _set_cell(ws, row, 20, item.id)
    _set_cell(ws, row, 21, item.title)
    _set_cell(ws, row, 22, item.description)
    _set_cell(ws, row, 23, item.resolution)
    _set_cell(ws, row, 24, item.owner)
    _set_cell(ws, row, 25, item.priority)


def _write_detail_decision(ws: Worksheet, row: int, item: DecisionEntry) -> None:
    _set_cell(ws, row, 27, item.id)
    _set_cell(ws, row, 28, item.title)
    _set_cell(ws, row, 29, item.description_justification)
    _set_cell(ws, row, 30, item.resolution)
    _set_cell(ws, row, 31, item.owner)
    _set_cell(ws, row, 32, item.priority)


def _fill_raid_simple_sheet(
    ws: Worksheet,
    raid: RAIDLog,
    project: str,
    today: str,
) -> None:
    _set_cell(ws, 4, 3, project)
    _set_cell(ws, 1, 6, today)

    rows: list[tuple[str, RiskEntry | ActionEntry | IssueEntry | DecisionEntry]] = []
    for item in raid.risks:
        rows.append(("Risk", item))
    for item in raid.actions:
        rows.append(("Action", item))
    for item in raid.issues:
        rows.append(("Issue", item))
    for item in raid.decisions:
        rows.append(("Decision", item))

    end_row = _SIMPLE_DATA_START_ROW + max(len(rows), 6) + 5
    _clear_row_range(ws, _SIMPLE_DATA_START_ROW, end_row, 14)

    for index, (category, item) in enumerate(rows):
        row = _SIMPLE_DATA_START_ROW + index
        _set_cell(ws, row, 1, index + 1)
        _set_cell(ws, row, 2, category)
        _set_cell(ws, row, 3, item.title)
        description = getattr(item, "description", None) or getattr(
            item, "description_justification", ""
        )
        _set_cell(ws, row, 4, description)
        priority = getattr(item, "priority", "")
        _set_cell(ws, row, 5, priority)
        status = getattr(item, "status", "Open")
        _set_cell(ws, row, 6, status)
        _set_cell(ws, row, 7, item.owner)
        _set_cell(ws, row, 8, priority)
        if isinstance(item, RiskEntry) and item.mitigation:
            _set_cell(ws, row, 14, item.mitigation)
