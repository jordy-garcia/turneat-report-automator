"""CLI entry: resolve report period and per-project extras, then run the pipeline."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tra.config import load_config
from tra.main import run


def previous_month(tz_name: str) -> tuple[int, int]:
    """Return (month, year) for the calendar month before 'now' in tz_name."""
    now = datetime.now(ZoneInfo(tz_name))
    if now.month == 1:
        return 12, now.year - 1
    return now.month - 1, now.year


def parse_period_mm_yyyy(raw: str) -> tuple[int, int]:
    """Parse 'MM-YYYY' into (month, year). Raises ValueError on bad input."""
    text = raw.strip()
    parts = text.split("-")
    if len(parts) != 2:
        raise ValueError("use MM-YYYY (e.g. 07-2026)")
    month_s, year_s = parts[0].strip(), parts[1].strip()
    if not month_s.isdigit() or not year_s.isdigit():
        raise ValueError("use MM-YYYY (e.g. 07-2026)")
    month = int(month_s)
    year = int(year_s)
    if month < 1 or month > 12:
        raise ValueError("month must be between 01 and 12")
    if year < 1970 or year > 2100:
        raise ValueError("year looks invalid")
    return month, year


def parse_extras_line(raw: str) -> list[dict[str, str]]:
    """
    Parse 'Cat: desc; Cat2: desc2' into extra_tasks dicts.
    Empty / whitespace-only → [].
    """
    text = raw.strip()
    if not text:
        return []

    tasks: list[dict[str, str]] = []
    for segment in text.split(";"):
        piece = segment.strip()
        if not piece:
            continue
        if ":" not in piece:
            raise ValueError(
                f"missing ':' in {piece!r} (expected Category: description)"
            )
        category, description = piece.split(":", 1)
        category = category.strip()
        description = description.strip()
        if not category or not description:
            raise ValueError(
                f"empty category or description in {piece!r} "
                "(expected Category: description)"
            )
        tasks.append({"category": category, "description": description})
    return tasks


def _prompt_period(tz_name: str) -> tuple[int, int]:
    suggested_m, suggested_y = previous_month(tz_name)
    suggested = f"{suggested_m:02d}-{suggested_y}"
    print(
        f"Nota: por defecto se sugiere el mes anterior ({suggested}). "
        "Enter vacío acepta la sugerencia."
    )
    while True:
        try:
            raw = input(f"Mes a reportar? [{suggested}]: ")
        except EOFError:
            print("ERROR: No input for report period.", file=sys.stderr)
            sys.exit(1)
        if not raw.strip():
            return suggested_m, suggested_y
        try:
            return parse_period_mm_yyyy(raw)
        except ValueError as exc:
            print(f"Entrada inválida: {exc}. Intenta de nuevo.")


def _prompt_extras_for_projects(project_names: list[str]) -> dict[str, list[dict]]:
    extras: dict[str, list[dict]] = {}
    for name in project_names:
        while True:
            try:
                raw = input(
                    f"Extras for {name} (Cat: desc; Cat2: desc2). Empty = none: "
                )
            except EOFError:
                print("ERROR: No input for extra tasks.", file=sys.stderr)
                sys.exit(1)
            try:
                extras[name] = parse_extras_line(raw)
                break
            except ValueError as exc:
                print(f"Entrada inválida: {exc}. Intenta de nuevo.")
    return extras


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reporter",
        description="Generate monthly activity PDFs from git commits.",
    )
    parser.add_argument(
        "--month",
        type=int,
        help="Report month (1-12). Requires --year; skips the period prompt.",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Report year. Requires --month; skips the period prompt.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.json (default: ./config.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    tz_name = config.settings.calendar_timezone
    tty = sys.stdin.isatty()

    both_flags = args.month is not None and args.year is not None
    partial_flags = (args.month is not None) ^ (args.year is not None)

    if both_flags:
        if args.month < 1 or args.month > 12:
            print("ERROR: --month must be between 1 and 12.", file=sys.stderr)
            sys.exit(1)
        if args.year < 1970 or args.year > 2100:
            print("ERROR: --year looks invalid.", file=sys.stderr)
            sys.exit(1)
        month, year = args.month, args.year
    else:
        if partial_flags:
            print(
                "WARNING: both --month and --year are required to skip the prompt; "
                "ignoring the partial flag.",
                file=sys.stderr,
            )
        if not tty:
            print(
                "ERROR: non-interactive stdin requires both --month and --year.",
                file=sys.stderr,
            )
            sys.exit(1)
        month, year = _prompt_period(tz_name)

    project_names = [str(p["name"]) for p in config.projects]
    if tty:
        extras_by_project = _prompt_extras_for_projects(project_names)
    else:
        print(
            "WARNING: non-interactive stdin; using empty extra_tasks for all projects.",
            file=sys.stderr,
        )
        extras_by_project = {name: [] for name in project_names}

    settings = replace(config.settings, month=month, year=year)
    config = replace(config, settings=settings)
    run(config, extras_by_project=extras_by_project)


if __name__ == "__main__":
    main()
