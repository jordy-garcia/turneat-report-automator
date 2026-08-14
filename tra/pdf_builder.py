"""PDF report layout for monthly activity reports."""

from __future__ import annotations

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from tra.dates import month_name_es
from tra.types import EnvLabel, ExtraTaskLine, ReportSection

_PDF_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

# Palette — navy + teal (professional, not purple/cream defaults)
_NAVY = (18, 48, 78)
_TEAL = (26, 148, 138)
_TEAL_SOFT = (232, 245, 243)
_INK = (28, 34, 42)
_MUTED = (105, 115, 128)
_RULE = (210, 218, 224)
_HOURS = (120, 128, 138)
_WHITE = (255, 255, 255)

_ENV_CHIP: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "prod": ((196, 72, 72), _WHITE),
    "stage": ((196, 138, 42), _WHITE),
    "dev": ((42, 118, 178), _WHITE),
}
_ENV_CHIP_FALLBACK = ((110, 120, 132), _WHITE)

_HOURS_COL_W = 18.0
_CHIP_H = 4.6


def format_hours(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _clean_bullet_text(text: str) -> str:
    t = text.strip()
    if t.startswith(("•", "·", "-", "*")):
        t = t[1:].lstrip(" \t").strip()
    return t


def _env_colors(env: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    return _ENV_CHIP.get(env.strip().lower(), _ENV_CHIP_FALLBACK)


class ReportPDF(FPDF):
    """FPDF with a thin teal footer rule + page number."""

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*_TEAL)
        self.set_line_width(0.35)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_MUTED)
        self.cell(0, 5, f"{self.page_no()}", align="R")
        self.set_text_color(*_INK)


def _ensure_space(pdf: FPDF, height: float) -> None:
    """Start a new page if the remaining space cannot fit `height` mm."""
    if pdf.get_y() + height > pdf.page_break_trigger:
        pdf.add_page()


def _draw_top_band(pdf: FPDF) -> None:
    pdf.set_fill_color(*_NAVY)
    pdf.rect(0, 0, pdf.w, 8, style="F")
    pdf.set_fill_color(*_TEAL)
    pdf.rect(0, 8, pdf.w, 1.6, style="F")
    pdf.set_y(14)


def _draw_section_heading(pdf: FPDF, title: str, *, pt: int = 12) -> None:
    _ensure_space(pdf, pt * 0.62 + 18)
    y = pdf.get_y()
    pdf.set_fill_color(*_TEAL)
    pdf.rect(pdf.l_margin, y + 0.8, 1.8, pt * 0.55, style="F")
    pdf.set_xy(pdf.l_margin + 4, y)
    pdf.set_font("Helvetica", "B", pt)
    pdf.set_text_color(*_NAVY)
    pdf.multi_cell(pdf.epw - 4, pt * 0.62, title, **_PDF_NEXT_LINE)
    pdf.set_text_color(*_INK)
    pdf.ln(1.5)
    # Soft rule under chapter titles
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.25)
    y2 = pdf.get_y()
    pdf.line(pdf.l_margin, y2, pdf.w - pdf.r_margin, y2)
    pdf.ln(3)


def _draw_subsection_title(pdf: FPDF, title: str, *, pt: int = 10) -> None:
    _ensure_space(pdf, pt * 0.58 + 14)
    pdf.set_font("Helvetica", "B", pt)
    pdf.set_text_color(*_TEAL)
    pdf.multi_cell(0, pt * 0.58, title, **_PDF_NEXT_LINE)
    pdf.set_text_color(*_INK)
    pdf.ln(1.4)


def _draw_env_chip(pdf: FPDF, env: str, *, x: float, y: float) -> float:
    """Draw colored env chip; returns width used."""
    label = env.strip().upper()[:8] or "ENV"
    bg, fg = _env_colors(env)
    pdf.set_font("Helvetica", "B", 7)
    width = pdf.get_string_width(label) + 3.2
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_xy(x, y + 0.35)
    pdf.cell(width, _CHIP_H, label, fill=True, align="C")
    pdf.set_text_color(*_INK)
    return width


def _draw_hours_at(
    pdf: FPDF,
    *,
    hours: float,
    x: float,
    y: float,
    width: float,
    line_h: float,
) -> None:
    pdf.set_xy(x, y)
    pdf.set_text_color(*_HOURS)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(width, line_h, f"{format_hours(hours)} h", align="R")
    pdf.set_text_color(*_INK)


def _write_bullet_row(
    pdf: FPDF,
    *,
    text: str,
    env: EnvLabel,
    hours: float | None,
    tag_environment: bool,
    body_pt: int,
    indent: float,
) -> None:
    body = _clean_bullet_text(text)
    if not body:
        return

    line_h = body_pt * 0.65
    # Chip + at least two text lines must stay together (avoid orphan env tags).
    _ensure_space(pdf, _CHIP_H + line_h * 2 + 6)

    x0 = pdf.l_margin + indent
    y0 = pdf.get_y()
    hours_w = _HOURS_COL_W if hours is not None else 0.0
    usable = pdf.epw - indent - hours_w

    cursor_x = x0
    if tag_environment:
        chip_w = _draw_env_chip(pdf, env, x=x0, y=y0)
        cursor_x = x0 + chip_w + 2.0

    text_w = max(usable - (cursor_x - x0), 20.0)
    pdf.set_xy(cursor_x, y0)
    pdf.set_font("Helvetica", "", body_pt)
    pdf.set_text_color(*_INK)
    pdf.multi_cell(text_w, line_h, body, **_PDF_NEXT_LINE)
    y_after = pdf.get_y()

    if hours is not None:
        _draw_hours_at(
            pdf,
            hours=hours,
            x=pdf.l_margin + pdf.epw - hours_w,
            y=y0,
            width=hours_w,
            line_h=line_h,
        )
        pdf.set_y(y_after)

    pdf.ln(2.4)


def write_report_hierarchy(
    pdf: FPDF,
    sections: list[ReportSection],
    *,
    tag_environment: bool = True,
    main_pt: int = 12,
    sub_pt: int = 10,
    body_pt: int = 9,
    indent: float = 3,
) -> None:
    rendered_sections = 0
    for sec in sections:
        main_title = sec["title"].strip()
        # Keep only subsections that still have visible bullets.
        live_subs: list[tuple[str, list]] = []
        for sub in sec["subsections"]:
            sub_title = sub["title"].strip()
            if sub_title and not sub_title.endswith(":"):
                sub_title = f"{sub_title}:"
            bullets = [
                b
                for b in sub["bullets"]
                if _clean_bullet_text(b.get("text", ""))
            ]
            if bullets:
                live_subs.append((sub_title, bullets))
        if not live_subs:
            continue

        if rendered_sections > 0:
            pdf.ln(4)
        if main_title:
            _draw_section_heading(pdf, main_title, pt=main_pt)

        for sub_title, bullets in live_subs:
            if sub_title:
                _draw_subsection_title(pdf, sub_title, pt=sub_pt)
            for bullet in bullets:
                _write_bullet_row(
                    pdf,
                    text=bullet["text"],
                    env=bullet["env"],
                    hours=bullet.get("hours"),
                    tag_environment=tag_environment,
                    body_pt=body_pt,
                    indent=indent,
                )
            pdf.ln(1.2)
        rendered_sections += 1


def write_extra_task_lines(
    pdf: FPDF,
    lines: list[ExtraTaskLine],
    *,
    title_pt: int = 10,
    body_pt: int = 9,
) -> None:
    line_h = body_pt * 0.65
    for line in lines:
        text = (line.get("text") or "").strip()
        if not text:
            continue
        hours = line.get("hours")
        _ensure_space(pdf, title_pt * 0.55 + line_h * 2 + 8)
        y0 = pdf.get_y()
        hours_w = _HOURS_COL_W if hours is not None else 0.0
        content_w = pdf.epw - 4 - hours_w

        if ": " in text:
            title, body = text.split(": ", 1)
            if not body.strip():
                body = title
                title = ""
            pdf.set_xy(pdf.l_margin + 4, y0)
            if title.strip():
                pdf.set_font("Helvetica", "B", title_pt)
                pdf.set_text_color(*_NAVY)
                pdf.multi_cell(
                    content_w, title_pt * 0.55, title.strip(), **_PDF_NEXT_LINE
                )
                pdf.set_x(pdf.l_margin + 4)
            pdf.set_font("Helvetica", "", body_pt)
            pdf.set_text_color(*_INK)
            pdf.multi_cell(content_w, line_h, body.strip(), **_PDF_NEXT_LINE)
            y_after = pdf.get_y()
            hours_line_h = title_pt * 0.55
        else:
            pdf.set_xy(pdf.l_margin + 4, y0)
            pdf.set_font("Helvetica", "", body_pt)
            pdf.set_text_color(*_INK)
            pdf.multi_cell(content_w, line_h, text, **_PDF_NEXT_LINE)
            y_after = pdf.get_y()
            hours_line_h = line_h

        pdf.set_fill_color(*_TEAL)
        pdf.rect(pdf.l_margin, y0, 1.6, max(y_after - y0, 6), style="F")

        if hours is not None:
            _draw_hours_at(
                pdf,
                hours=hours,
                x=pdf.l_margin + pdf.epw - hours_w,
                y=y0,
                width=hours_w,
                line_h=hours_line_h,
            )

        pdf.set_y(y_after)
        pdf.ln(3.2)


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
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_text_color(*_INK)

    _draw_top_band(pdf)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*_NAVY)
    pdf.multi_cell(0, 8, project_name, **_PDF_NEXT_LINE)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MUTED)
    pdf.cell(0, 5.5, "Informe de actividad mensual", **_PDF_NEXT_LINE)
    pdf.ln(2)

    # Meta strip
    pdf.set_fill_color(*_TEAL_SOFT)
    meta_y = pdf.get_y()
    pdf.rect(pdf.l_margin, meta_y, pdf.epw, 12, style="F")
    pdf.set_xy(pdf.l_margin + 3, meta_y + 2.2)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_INK)
    meta_bits = [f"Período: {month_label} {year}", responsible_name]
    if assigned_hours is not None:
        meta_bits.append(f"Horas: {assigned_hours}")
    pdf.cell(pdf.epw - 6, 7, "  ·  ".join(meta_bits), **_PDF_NEXT_LINE)
    pdf.set_y(meta_y + 14)

    # Content sections from Gemini (no empty wrapper chapter).
    write_report_hierarchy(pdf, sections, tag_environment=tag_environment)

    visible_extras = [e for e in extra_lines if (e.get("text") or "").strip()]
    if visible_extras:
        pdf.ln(3)
        _draw_section_heading(pdf, "Gestión administrativa y soporte adicional", pt=12)
        write_extra_task_lines(pdf, visible_extras)

    pdf.output(output_path)
