import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from tra.env_labels import EnvMapConfig, parse_env_map
from tra.types import CommitDateBasis


@dataclass(frozen=True)
class ReportSettings:
    report_hours: bool
    tag_environment: bool
    env_map: EnvMapConfig
    total_hours: int
    month: int
    year: int
    responsible_name: str
    author_emails: list[str]
    exclude_pr_merge_commits: bool
    exclude_environment_sync_merges: bool
    gemini_model: str
    gemini_paraphrase_model: str
    write_ai_debug_file: bool
    calendar_timezone: str
    commit_date_basis: CommitDateBasis


@dataclass(frozen=True)
class AppConfig:
    settings: ReportSettings
    projects: list[dict[str, Any]]
    script_dir: Path
    debug_dir: Path
    reports_dir: Path
    api_key: str


def _parse_email_list(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else None
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out or None
    return None


def _parse_timezone(raw: Any) -> str:
    name = str(raw or "UTC").strip() or "UTC"
    try:
        ZoneInfo(name)
        return name
    except Exception:
        print(f"WARNING: Invalid calendar_timezone ({raw!r}); using UTC.")
        return "UTC"


def _parse_date_basis(raw: Any) -> CommitDateBasis:
    return "author" if str(raw or "").lower() == "author" else "committer"


def load_config(config_path: Path | None = None) -> AppConfig:
    script_dir = Path(__file__).resolve().parent.parent
    load_dotenv(script_dir / ".env")

    api_key = ""
    for var in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        value = os.environ.get(var, "").strip()
        if value:
            api_key = value
            break
    if not api_key:
        print(
            "ERROR: Missing Gemini API key. Set GOOGLE_API_KEY or GEMINI_API_KEY "
            "in the environment or in .env (see .env.example).",
            file=sys.stderr,
        )
        sys.exit(1)

    path = config_path or (script_dir / "config.json")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    raw = data["report_settings"]
    author_emails = _parse_email_list(raw.get("author_emails"))
    if not author_emails:
        print(
            "ERROR: report_settings.author_emails must list at least one git author email "
            "(from git log, e.g. git log -1 --format='%ae').",
            file=sys.stderr,
        )
        sys.exit(1)

    settings = ReportSettings(
        report_hours=bool(raw.get("report_hours", True)),
        tag_environment=bool(raw.get("tag_environment", True)),
        env_map=parse_env_map(
            raw.get("env_map"),
            default_label=str(raw.get("env_default", "")).strip() or None,
        ),
        total_hours=int(raw["total_hours"]),
        month=int(raw["month"]),
        year=int(raw["year"]),
        responsible_name=str(raw["responsible_name"]),
        author_emails=author_emails,
        exclude_pr_merge_commits=bool(raw.get("exclude_pr_merge_commits", False)),
        exclude_environment_sync_merges=bool(
            raw.get("exclude_environment_sync_merges", True)
        ),
        gemini_model=str(raw.get("gemini_model", "gemini-2.5-pro")).strip()
        or "gemini-2.5-pro",
        gemini_paraphrase_model=str(
            raw.get("gemini_paraphrase_model", "gemini-2.5-flash")
        ).strip()
        or "gemini-2.5-flash",
        write_ai_debug_file=bool(raw.get("write_ai_debug_file", True)),
        calendar_timezone=_parse_timezone(raw.get("calendar_timezone", "UTC")),
        commit_date_basis=_parse_date_basis(raw.get("commit_date_basis", "committer")),
    )

    return AppConfig(
        settings=settings,
        projects=data["projects"],
        script_dir=script_dir,
        debug_dir=script_dir / "debug",
        reports_dir=script_dir / "reports",
        api_key=api_key,
    )
