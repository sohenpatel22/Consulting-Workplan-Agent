"""Extract structural specs from Deloitte WBS docx and RAID xlsx templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_wbs_spec(docx_path: Path) -> dict[str, Any]:
    from docx import Document

    document = Document(docx_path)
    if not document.tables:
        raise ValueError(f"No table found in WBS template: {docx_path}")

    table = document.tables[0]
    headers = [cell.text.strip() for cell in table.rows[0].cells]
    field_map = {
        "Level": ("level", "integer", "1=phase, 2=work stream, 3=task"),
        "WBS Code": ("wbs_code", "string", "Hierarchical code e.g. 1.0, 1.1, 1.1.1"),
        "WBS Element Title": ("wbs_element_title", "string", "Short name of the element"),
        "Description / Scope of Work": (
            "description_scope",
            "string",
            "Scope narrative for this element",
        ),
        "Key Deliverable": (
            "key_deliverable",
            "string",
            "Primary deliverable for this element",
        ),
    }
    columns: list[dict[str, str]] = []
    for header in headers:
        if header in field_map:
            field, typ, desc = field_map[header]
            columns.append({"header": header, "field": field, "type": typ, "description": desc})

    example_rows: list[dict[str, Any]] = []
    for row in table.rows[1:8]:
        cells = [cell.text.strip() for cell in row.cells]
        if not any(cells):
            continue
        row_data = dict(zip(headers, cells, strict=False))
        example_rows.append(
            {
                "level": int(row_data.get("Level", "0") or 0),
                "wbs_code": row_data.get("WBS Code", ""),
                "wbs_element_title": row_data.get("WBS Element Title", ""),
                "description_scope": row_data.get("Description / Scope of Work", ""),
                "key_deliverable": row_data.get("Key Deliverable", ""),
            }
        )

    return {
        "source_file": docx_path.name,
        "summary": (
            "Work packages must follow the Deloitte WBS table: a 3-level hierarchy "
            "(levels 1–3) with codes like 1.0, 1.1, 1.1.1. Each row is one element."
        ),
        "columns": columns,
        "hierarchy_rules": [
            "Level 1 = phase / major deliverable (WBS code X.0).",
            "Level 2 = work stream under that phase (X.Y).",
            "Level 3 = task under a work stream (X.Y.Z).",
            "parent_wbs_code must reference an existing wbs_code one level above.",
            "Minimum 3 level-1 elements, each with at least 2 level-2 children.",
            "Also include owner, estimated_duration, and dependencies (list of wbs_codes).",
        ],
        "example_rows": example_rows,
    }


def extract_raid_spec(xlsx_path: Path) -> dict[str, Any]:
    from openpyxl import load_workbook

    workbook = load_workbook(xlsx_path, data_only=True)
    detail = workbook["RAID Log - Detail"]
    simple = workbook["RAID Log - simple"]

    sections = [
        {
            "key": "risks",
            "title": "Risks",
            "minimum": 3,
            "fields": [
                {"name": "id", "type": "string", "required": True, "description": "R1, R2, …"},
                {"name": "title", "type": "string", "required": True, "description": ""},
                {"name": "description", "type": "string", "required": True, "description": ""},
                {"name": "status", "type": "string", "required": True, "description": "e.g. Open"},
                {
                    "name": "mitigation",
                    "type": "string",
                    "required": True,
                    "description": "Mitigation plan",
                },
                {"name": "owner", "type": "string", "required": True, "description": ""},
                {
                    "name": "wbs_links",
                    "type": "array",
                    "required": True,
                    "description": "WBS codes this risk relates to",
                },
                {
                    "name": "probability",
                    "type": "string",
                    "required": True,
                    "description": "High, Moderate, or Low",
                },
                {
                    "name": "priority",
                    "type": "string",
                    "required": True,
                    "description": "Priority/Impact: High, Moderate, or Low",
                },
            ],
            "template_headers": _row_headers(detail, 6, 1, 9),
        },
        {
            "key": "actions",
            "title": "Actions",
            "minimum": 2,
            "fields": [
                {"name": "id", "type": "string", "required": True, "description": "A1, A2, …"},
                {"name": "title", "type": "string", "required": True, "description": ""},
                {"name": "description", "type": "string", "required": True, "description": ""},
                {
                    "name": "status_update",
                    "type": "string",
                    "required": False,
                    "description": "MM-DD-YYYY: update text",
                },
                {"name": "status", "type": "string", "required": True, "description": ""},
                {"name": "owner", "type": "string", "required": True, "description": ""},
                {
                    "name": "wbs_links",
                    "type": "array",
                    "required": True,
                    "description": "WBS codes",
                },
                {
                    "name": "priority",
                    "type": "string",
                    "required": True,
                    "description": "High, Moderate, or Low",
                },
            ],
            "template_headers": _row_headers(detail, 6, 11, 18),
        },
        {
            "key": "issues",
            "title": "Issues",
            "minimum": 0,
            "fields": [
                {"name": "id", "type": "string", "required": True, "description": "I1, I2, …"},
                {"name": "title", "type": "string", "required": True, "description": ""},
                {"name": "description", "type": "string", "required": True, "description": ""},
                {
                    "name": "resolution",
                    "type": "string",
                    "required": False,
                    "description": "Resolution when known",
                },
                {"name": "owner", "type": "string", "required": True, "description": ""},
                {
                    "name": "priority",
                    "type": "string",
                    "required": True,
                    "description": "High, Moderate, or Low",
                },
            ],
            "template_headers": _row_headers(detail, 6, 20, 25),
        },
        {
            "key": "decisions",
            "title": "Decisions",
            "minimum": 0,
            "fields": [
                {"name": "id", "type": "string", "required": True, "description": "D1, D2, …"},
                {"name": "title", "type": "string", "required": True, "description": ""},
                {
                    "name": "description_justification",
                    "type": "string",
                    "required": True,
                    "description": "Description / justification",
                },
                {
                    "name": "resolution",
                    "type": "string",
                    "required": False,
                    "description": "Decision outcome",
                },
                {"name": "owner", "type": "string", "required": True, "description": ""},
                {
                    "name": "priority",
                    "type": "string",
                    "required": True,
                    "description": "High, Moderate, or Low",
                },
            ],
            "template_headers": _row_headers(detail, 6, 27, 32),
        },
    ]

    simple_columns = _row_headers(simple, 5, 1, 8)
    return {
        "source_file": xlsx_path.name,
        "summary": (
            "RAID log follows the Deloitte Excel template: Risks, Actions, Issues, and "
            "Decisions are separate sections (not Assumptions/Dependencies). "
            "Use priority values High, Moderate, or Low."
        ),
        "sections": sections,
        "simple_view": {
            "sheet": "RAID Log - simple",
            "columns": simple_columns,
            "categories": ["Risk", "Action", "Issue", "Decision"],
        },
    }


def _row_headers(ws: object, row: int, start_col: int, end_col: int) -> list[str]:
    from openpyxl.worksheet.worksheet import Worksheet

    assert isinstance(ws, Worksheet)
    headers: list[str] = []
    for col in range(start_col, end_col + 1):
        value = ws.cell(row=row, column=col).value
        if value is not None and str(value).strip():
            headers.append(str(value).strip())
    return headers
