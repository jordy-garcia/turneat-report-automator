"""PDF report layout for monthly activity reports."""

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from tra.dates import month_name_es
from tra.types import EnvLabel, ExtraTaskLine, ReportSection

_PDF_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}
HOURS_GRAY = (120, 120, 120)
# Fixed right column for per-task hours (mm). Keeps text from colliding with hours.
_HOURS_COL_W = 18.0


def format_hours(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def bullet_line(text: str, env: EnvLabel, *, tag_environment: bool) -> str:
    t = text.strip()
    if t.startswith(("•", "·", "-", "*")):
        t = t[1:].lstrip(" \t").strip()
    if tag_environment:
        return f"- **{env}** {t}"
    return f"- {t}"


def _draw_hours_at(
    pdf: FPDF,
    *,
    hours: float,
    x: float,
    y: float,
    width: float,
    body_pt: int,
    line_h: float,
) -> None:
    """Draw gray hours in the reserved column at the first line of the item."""
    pdf.set_xy(x, y)
    pdf.set_text_color(*HOURS_GRAY)
    pdf.set_font("Helvetica", "", max(body_pt - 1, 7))
    pdf.cell(width, line_h, f"{format_hours(hours)} h", align="R")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", body_pt)


def _write_text_block_with_optional_hours(
    pdf: FPDF,
    text: str,
    hours: float | None,
    *,
    body_pt: int,
    line_h: float,
    text_width: float,
    x_left: float,
    markdown: bool = False,
    gap_after: float = 2.0,
) -> None:
    """
    Write a wrapping text block; if hours are set, pin them to the top-right
    of the block without moving the cursor back into the text.
    """
    y0 = pdf.get_y()
    hours_w = _HOURS_COL_W if hours is not None else 0.0
    content_w = text_width - hours_w

    pdf.set_xy(x_left, y0)
    pdf.multi_cell(
        content_w,
        line_h,
        text,
        markdown=markdown,
        **_PDF_NEXT_LINE,
    )
    y_after = pdf.get_y()

    if hours is not None:
        hours_x = x_left + content_w
        _draw_hours_at(
            pdf,
            hours=hours,
            x=hours_x,
            y=y0,
            width=hours_w,
            body_pt=body_pt,
            line_h=line_h,
        )
        pdf.set_y(y_after)

    if gap_after:
        pdf.ln(gap_after)


def write_report_hierarchy(
    pdf: FPDF,
    sections: list[ReportSection],
    *,
    tag_environment: bool = True,
    main_pt: int = 12,
    sub_pt: int = 10,
    body_pt: int = 9,
    indent: float = 6,
) -> None:
    line_h = body_pt * 0.65
    for sec_idx, sec in enumerate(sections):
        if sec_idx > 0:
            pdf.ln(5)
        main_title = sec["title"].strip()
        if main_title:
            pdf.set_font("Helvetica", "B", main_pt)
            pdf.multi_cell(0, main_pt * 0.62, main_title, **_PDF_NEXT_LINE)
            pdf.ln(2.5)

        for sub in sec["subsections"]:
            sub_title = sub["title"].strip()
            if sub_title and not sub_title.endswith(":"):
                sub_title = f"{sub_title}:"
            pdf.set_font("Helvetica", "B", sub_pt)
            pdf.multi_cell(0, sub_pt * 0.6, sub_title, **_PDF_NEXT_LINE)
            pdf.ln(1.6)

            pdf.set_font("Helvetica", "", body_pt)
            x_left = pdf.l_margin + indent
            text_width = pdf.epw - indent
            for bullet in sub["bullets"]:
                hours = bullet.get("hours")
                _write_text_block_with_optional_hours(
                    pdf,
                    bullet_line(
                        bullet["text"],
                        bullet["env"],
                        tag_environment=tag_environment,
                    ),
                    hours,
                    body_pt=body_pt,
                    line_h=line_h,
                    text_width=text_width,
                    x_left=x_left,
                    markdown=True,
                    gap_after=2.2,
                )
            pdf.ln(1.5)


def write_extra_task_lines(
    pdf: FPDF,
    lines: list[ExtraTaskLine],
    *,
    title_pt: int = 10,
    body_pt: int = 9,
) -> None:
    line_h = body_pt * 0.62
    for line in lines:
        text = line["text"]
        hours = line.get("hours")
        sep = ": "
        if sep in text:
            title, body = text.split(sep, 1)
            pdf.set_font("Helvetica", "B", title_pt)
            pdf.multi_cell(0, title_pt * 0.58, title.strip(), **_PDF_NEXT_LINE)
            pdf.ln(0.8)
            pdf.set_font("Helvetica", "", body_pt)
            _write_text_block_with_optional_hours(
                pdf,
                body.strip(),
                hours,
                body_pt=body_pt,
                line_h=line_h,
                text_width=pdf.epw,
                x_left=pdf.l_margin,
                gap_after=3.0,
            )
        else:
            pdf.set_font("Helvetica", "", body_pt)
            _write_text_block_with_optional_hours(
                pdf,
                text,
                hours,
                body_pt=body_pt,
                line_h=line_h,
                text_width=pdf.epw,
                x_left=pdf.l_margin,
                gap_after=3.0,
            )


def build_project_pdf(
    *,
    project_name: str,
    responsible_name: str,
    month: int,
    year: int,
    assigned_hours: int | None,
    sections: list[ReportSection],
    extra_lines: list[ExtraTaskLine],
    output_path: str,
    tag_environment: bool = True,
) -> None:
    month_label = month_name_es(month)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, f"Informe de actividad: {project_name}", **_PDF_NEXT_LINE)
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6.5, f"Período: {month_label} {year}", **_PDF_NEXT_LINE)
    pdf.cell(0, 6.5, responsible_name, **_PDF_NEXT_LINE)
    if assigned_hours is not None:
        pdf.cell(0, 6.5, f"Horas: {assigned_hours}", **_PDF_NEXT_LINE)
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Desarrollo y soporte técnico", **_PDF_NEXT_LINE)
    pdf.ln(2)
    write_report_hierarchy(pdf, sections, tag_environment=tag_environment)
    pdf.ln(4)

    if extra_lines:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Gestión administrativa y soporte adicional", **_PDF_NEXT_LINE)
        pdf.ln(2)
        write_extra_task_lines(pdf, extra_lines)

    pdf.output(output_path)
