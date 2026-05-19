import json
from pathlib import Path

from tra.config import AppConfig, ReportSettings
from tra.types import CommitRecord


def safe_debug_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:64]


def write_ai_context_debug(
    config: AppConfig,
    settings: ReportSettings,
    project_name: str,
    commits: list[CommitRecord],
    prompt: str,
    model: str,
) -> None:
    if not settings.write_ai_debug_file:
        return
    path = _debug_path(config, settings, f"debug_ai_context_{safe_debug_filename(project_name)}")
    head = [
        f"# Gemini context — project «{project_name}»",
        f"# Model: {model}",
        f"# author_emails: {settings.author_emails}",
        f"# env_map: { {label: list(patterns) for label, patterns in settings.env_map.entries} }",
        f"# env_default: {settings.env_map.default_label}",
        f"# Commits: {len(commits)}",
        "",
        "## Commits (verify author_email with: git show <sha>)",
        "",
    ]
    body: list[str] = []
    for i, c in enumerate(commits, 1):
        sha = str(c.get("sha", ""))[:40]
        body.append(f"{i}. [{c.get('env', '')}] sha={sha}")
        body.append(f"   email={c.get('author_email', '')}")
        body.append(f"   msg: {(c.get('message') or '').replace(chr(10), ' ')}")
    tail = ["", "## Full prompt", "", prompt]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(head + body + tail), encoding="utf-8")
    print(f"Debug: {path}")


def write_paraphrase_debug(
    config: AppConfig,
    settings: ReportSettings,
    project_name: str,
    extra_tasks: list[dict],
    prompt: str,
    model: str,
) -> None:
    if not settings.write_ai_debug_file:
        return
    path = _debug_path(
        config, settings, f"debug_paraphrase_{safe_debug_filename(project_name)}"
    )
    lines = [
        f"# Extra-task paraphrase — «{project_name}»",
        f"# Model: {model}",
        "",
        "## Items (JSON)",
        json.dumps(extra_tasks, ensure_ascii=False, indent=2),
        "",
        "## Prompt",
        prompt,
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Debug: {path}")


def _debug_path(config: AppConfig, settings: ReportSettings, prefix: str) -> Path:
    return (
        config.debug_dir
        / f"{prefix}_{settings.year}_{settings.month:02d}.txt"
    )
