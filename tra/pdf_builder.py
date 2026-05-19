from fpdf import FPDF
from fpdf.enums import XPos, YPos

from tra.dates import month_name_es
from tra.types import EnvLabel, ReportSection

_PDF_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


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
            for bullet in sub["bullets"]:
                pdf.set_x(pdf.l_margin + indent)
                pdf.multi_cell(
                    inner_w,
                    body_pt * 0.52,
                    bullet_line(
                        bullet["text"], bullet["env"], tag_environment=tag_environment
                    ),
                    markdown=True,
                    **_PDF_NEXT_LINE,
                )
            pdf.ln(2)


def write_extra_task_lines(
    pdf: FPDF,
    lines: list[str],
    *,
    title_pt: int = 10,
    body_pt: int = 9,
) -> None:
    for line in lines:
        sep = ": "
        if sep in line:
            title, body = line.split(sep, 1)
            pdf.set_font("Helvetica", "B", title_pt)
            pdf.multi_cell(0, title_pt * 0.55, title.strip(), **_PDF_NEXT_LINE)
            pdf.set_font("Helvetica", "", body_pt)
            pdf.multi_cell(0, body_pt * 0.52, body.strip(), **_PDF_NEXT_LINE)
        else:
            pdf.set_font("Helvetica", "", body_pt)
            pdf.multi_cell(0, body_pt * 0.52, line, **_PDF_NEXT_LINE)
        pdf.ln(2.5)


def build_project_pdf(
    *,
    project_name: str,
    responsible_name: str,
    month: int,
    year: int,
    assigned_hours: int | None,
    sections: list[ReportSection],
    extra_lines: list[str],
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
