"""Shared fpdf2 helpers for Deloitte artifact PDF export."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fpdf import FPDF

    from workplan_agent.models.brief import ParsedBrief


def pdf_text(text: str) -> str:
    """Helvetica is Latin-1; normalize common Unicode punctuation."""
    if not text:
        return ""
    normalized = (
        text.replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u2022", "*")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return normalized.encode("latin-1", errors="replace").decode("latin-1")


def scale_col_widths(widths: tuple[float, ...], total_width: float) -> tuple[float, ...]:
    base = float(sum(widths))
    if base <= 0:
        return widths
    factor = total_width / base
    return tuple(w * factor for w in widths)


def render_table(
    pdf: FPDF,
    headers: list[str],
    rows: list[list[str]],
    *,
    col_widths: tuple[float, ...] | None = None,
    font_size: int = 7,
    line_height: int = 4,
) -> None:
    from fpdf.fonts import FontFace

    width = pdf.epw
    col_count = len(headers)
    if col_widths is None:
        scaled_widths = tuple(width / col_count for _ in range(col_count))
    else:
        scaled_widths = scale_col_widths(col_widths, width)

    header_style = FontFace(emphasis="BOLD")
    pdf.set_font("Helvetica", size=font_size)
    with pdf.table(
        width=width,
        col_widths=scaled_widths,
        line_height=line_height,
        text_align="LEFT",
    ) as table:
        header_row = table.row()
        for label in headers:
            header_row.cell(pdf_text(label), style=header_style)
        for cells in rows:
            row = table.row()
            for value in cells:
                row.cell(pdf_text(value))


def write_brief_header(pdf: FPDF, title: str, parsed_brief: ParsedBrief) -> None:
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 9, pdf_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(
        0,
        6,
        pdf_text(f"Project: {parsed_brief.project_title}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        6,
        pdf_text(f"Client: {parsed_brief.client_name}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)


def write_section_heading(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 7, pdf_text(title), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def write_body_text(pdf: FPDF, text: str, *, width: float | None = None) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(width or pdf.epw, 5, pdf_text(text))
    pdf.ln(2)


def write_bullet_list(pdf: FPDF, items: list[str], *, width: float | None = None) -> None:
    column_width = width or pdf.epw
    pdf.set_font("Helvetica", size=11)
    for item in items:
        pdf.multi_cell(column_width, 5, pdf_text(f"- {item}"))
    pdf.ln(2)


def add_landscape_table_section(
    pdf: FPDF,
    section_title: str,
    headers: list[str],
    rows: list[list[str]],
    *,
    col_widths: tuple[float, ...] | None = None,
) -> None:
    pdf.add_page(orientation="L")
    pdf.set_margins(10, 12, 10)
    write_section_heading(pdf, section_title)
    render_table(pdf, headers, rows, col_widths=col_widths)
