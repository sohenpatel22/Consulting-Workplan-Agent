"""Export markdown artifacts to downloadable formats."""

from __future__ import annotations

import io
import re
from html import escape
from typing import Literal

ExportFormat = Literal["md", "html", "docx", "pdf"]
ArtifactKind = Literal["wbs", "raid"]

CONTENT_TYPES: dict[ExportFormat, str] = {
    "md": "text/markdown; charset=utf-8",
    "html": "text/html; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


class ExportError(ValueError):
    """Raised when export cannot be produced."""


def export_artifact(markdown: str, artifact: ArtifactKind, fmt: ExportFormat) -> tuple[bytes, str]:
    """Return (file_bytes, suggested_filename) for the given markdown and format."""
    if not markdown.strip():
        raise ExportError(f"No {artifact.upper()} content available to export.")

    base_name = artifact
    if fmt == "md":
        return markdown.encode("utf-8"), f"{base_name}.md"
    if fmt == "html":
        return _to_html(markdown).encode("utf-8"), f"{base_name}.html"
    if fmt == "docx":
        return _to_docx(markdown), f"{base_name}.docx"
    if fmt == "pdf":
        return _to_pdf(markdown), f"{base_name}.pdf"
    raise ExportError(f"Unsupported export format: {fmt}")


def _to_html(markdown: str) -> str:
    try:
        import markdown as md_lib
    except ImportError as exc:
        raise ExportError("HTML export is not installed.") from exc

    body = md_lib.markdown(
        markdown,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = escape(title_match.group(1).strip()) if title_match else "Workplan artifact"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.5; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ background: #f4f4f4; }}
    pre {{ background: #f6f8fa; padding: 0.75rem; overflow-x: auto; border-radius: 6px; }}
    code {{ font-family: ui-monospace, monospace; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _parse_table_cells(line: str) -> list[str] | None:
    if not (line.startswith("|") and line.endswith("|")):
        return None
    cells = [c.strip() for c in line.strip("|").split("|")]
    if all(set(c) <= {"-", ":"} for c in cells):
        return None
    return cells


def _to_docx(markdown: str) -> bytes:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        raise ExportError("DOCX export is not installed.") from exc

    document = Document()
    pending_table_rows: list[list[str]] = []

    def flush_table() -> None:
        if not pending_table_rows:
            return
        table = document.add_table(rows=len(pending_table_rows), cols=len(pending_table_rows[0]))
        table.style = "Table Grid"
        for row_idx, row_cells in enumerate(pending_table_rows):
            for col_idx, cell_text in enumerate(row_cells):
                table.rows[row_idx].cells[col_idx].text = cell_text
        pending_table_rows.clear()

    for line in markdown.splitlines():
        stripped = line.rstrip()
        if not stripped:
            flush_table()
            continue

        table_cells = _parse_table_cells(stripped)
        if table_cells is not None:
            pending_table_rows.append(table_cells)
            continue

        flush_table()
        if stripped.startswith("# "):
            document.add_heading(stripped[2:].strip(), level=1)
        elif stripped.startswith("## "):
            document.add_heading(stripped[3:].strip(), level=2)
        elif stripped.startswith("### "):
            document.add_heading(stripped[4:].strip(), level=3)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            document.add_paragraph(stripped[2:].strip(), style="List Bullet")
        else:
            para = document.add_paragraph(stripped)
            for run in para.runs:
                run.font.size = Pt(11)

    flush_table()
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_line_text(line: str) -> str:
    """Normalize markdown lines for simple PDF rendering."""
    stripped = line.rstrip()
    if stripped.startswith("|") and stripped.endswith("|") and _parse_table_cells(stripped) is None:
        return ""
    table_cells = _parse_table_cells(stripped)
    if table_cells is not None:
        return " | ".join(table_cells)
    if stripped.startswith("# "):
        return stripped[2:].strip()
    if stripped.startswith("## "):
        return stripped[3:].strip()
    if stripped.startswith("### "):
        return stripped[4:].strip()
    if stripped.startswith("- ") or stripped.startswith("* "):
        return f"• {stripped[2:].strip()}"
    return stripped


def _to_pdf(markdown: str) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise ExportError("PDF export is not installed.") from exc

    pdf = FPDF()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    width = pdf.epw

    for line in markdown.splitlines():
        stripped = line.rstrip()
        if not stripped:
            pdf.ln(4)
            continue

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", style="B", size=16)
            pdf.multi_cell(width, 8, _pdf_safe(_pdf_line_text(stripped)))
            pdf.set_font("Helvetica", style="", size=11)
            continue
        if stripped.startswith("## "):
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.multi_cell(width, 7, _pdf_safe(_pdf_line_text(stripped)))
            pdf.set_font("Helvetica", style="", size=11)
            continue
        if stripped.startswith("### "):
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.multi_cell(width, 6, _pdf_safe(_pdf_line_text(stripped)))
            pdf.set_font("Helvetica", style="", size=11)
            continue

        text = _pdf_safe(_pdf_line_text(stripped))
        if not text:
            continue
        pdf.multi_cell(width, 5, text)

    return bytes(pdf.output())


def _pdf_safe(text: str) -> str:
    """Helvetica core font is Latin-1; replace unsupported characters."""
    return text.encode("latin-1", errors="replace").decode("latin-1")
