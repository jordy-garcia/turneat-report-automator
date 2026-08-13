from fpdf import FPDF
from fpdf.enums import XPos, YPos

from tra.dates import month_name_es
from tra.types import EnvLabel, ExtraTaskLine, ReportSection

_PDF_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}
HOURS_GRAY = (140, 140, 140)


def format_hours(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _append_hours(
    pdf: FPDF,
    hours: float,
    *,
    body_pt: int,
) -> None:
    pdf.set_text_color(*HOURS_GRAY)
    pdf.set_font("Helvetica", "", body_pt - 1)
    hours_h = (body_pt - 1) * 0.52
    pdf.cell(
        0,
        hours_h,
        f"  {format_hours(hours)} h",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", body_pt)


def bullet_line(text: str, env: EnvLabel, *, tag_environment: bool) -> str:
    t = text.strip()
    if t.startswith(("•", "·", "-", "*")):
        t = t[1:].lstrip(" \t").strip()
    if tag_environment:
        return f"- **{env}** {t}"
    return f"- {t}"


def write_report_hierarchy(
    pdf: FPDF,
    sections: list[ReportSection],
    *,
    tag_environment: bool = True,
    main_pt: int = 12,
    sub_pt: int = 10,
    body_pt: int = 9,
    indent: float = 5,
) -> None:
    for sec in sections:
        main_title = sec["title"].strip()
        if main_title:
            pdf.set_font("Helvetica", "B", main_pt)
            pdf.multi_cell(0, main_pt * 0.55, main_title, **_PDF_NEXT_LINE)
            pdf.ln(1.5)
        for sub in sec["subsections"]:
            sub_title = sub["title"].strip()
            if sub_title and not sub_title.endswith(":"):
                sub_title = f"{sub_title}:"
            pdf.set_font("Helvetica", "B", sub_pt)
            pdf.multi_cell(0, sub_pt * 0.52, sub_title, **_PDF_NEXT_LINE)
            pdf.ln(0.5)
            pdf.set_font("Helvetica", "", body_pt)
            inner_w = pdf.epw - indent
            line_h = body_pt * 0.52
            for bullet in sub["bullets"]:
                pdf.set_x(pdf.l_margin + indent)
                hours = bullet.get("hours")
                next_line = (
                    {"new_x": XPos.RIGHT, "new_y": YPos.TOP}
                    if hours is not None
                    else _PDF_NEXT_LINE
                )
                pdf.multi_cell(
                    inner_w,
                    line_h,
                    bullet_line(
                        bullet["text"], bullet["env"], tag_environment=tag_environment
                    ),
                    markdown=True,
                    **next_line,
                )
                if hours is not None:
                    _append_hours(pdf, hours, body_pt=body_pt)
            pdf.ln(2)


def _write_body_with_hours(
    pdf: FPDF,
    text: str,
    hours: float | None,
    *,
    body_pt: int,
    markdown: bool = False,
) -> None:
    line_h = body_pt * 0.52
    next_line = (
        {"new_x": XPos.RIGHT, "new_y": YPos.TOP}
        if hours is not None
        else _PDF_NEXT_LINE
    )
    pdf.multi_cell(0, line_h, text, markdown=markdown, **next_line)
    if hours is not None:
        _append_hours(pdf, hours, body_pt=body_pt)


def write_extra_task_lines(
    pdf: FPDF,
    lines: list[ExtraTaskLine],
    *,
    title_pt: int = 10,
    body_pt: int = 9,
) -> None:
    for line in lines:
        text = line["text"]
        hours = line.get("hours")
        sep = ": "
        if sep in text:
            title, body = text.split(sep, 1)
            pdf.set_font("Helvetica", "B", title_pt)
            pdf.multi_cell(0, title_pt * 0.55, title.strip(), **_PDF_NEXT_LINE)
            pdf.set_font("Helvetica", "", body_pt)
            _write_body_with_hours(pdf, body.strip(), hours, body_pt=body_pt)
        else:
            pdf.set_font("Helvetica", "", body_pt)
            _write_body_with_hours(pdf, text, hours, body_pt=body_pt)
        pdf.ln(2.5)


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
    pdf.cell(0, 10, f"Informe de actividad: {project_name}", **_PDF_NEXT_LINE)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Período: {month_label} {year}", **_PDF_NEXT_LINE)
    pdf.cell(0, 7, responsible_name, **_PDF_NEXT_LINE)
    if assigned_hours is not None:
        pdf.cell(0, 7, f"Horas: {assigned_hours}", **_PDF_NEXT_LINE)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Desarrollo y soporte técnico", **_PDF_NEXT_LINE)
    write_report_hierarchy(pdf, sections, tag_environment=tag_environment)
    pdf.ln(3)

    if extra_lines:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Gestión administrativa y soporte adicional", **_PDF_NEXT_LINE)
        write_extra_task_lines(pdf, extra_lines)

    pdf.output(output_path)
