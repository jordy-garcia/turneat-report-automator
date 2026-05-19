import re
from typing import Any

from tra.config import ReportSettings
from tra.types import CommitDateBasis

_ENV_BRANCH_SOURCES = (
    r"development",
    r"develop",
    r"dev",
    r"release(?:/[\w.-]+)?",
    r"main",
    r"master",
    r"staging",
)
ENV_SYNC_GITLAB = re.compile(
    r"^merged\s+(?:" + "|".join(_ENV_BRANCH_SOURCES) + r")\s+into\s+",
    re.IGNORECASE,
)
ENV_SYNC_MERGE_BRANCH = re.compile(
    r"^merge\s+branch\s+['\"]"
    r"(?:development|develop|dev|release(?:/[\w.-]+)?|main|master|staging)"
    r"(?:/[\w.-]+)?['\"]\s+into\s+",
    re.IGNORECASE,
)


def parse_repo_entry(entry: Any) -> tuple[str, dict]:
    if isinstance(entry, str):
        return entry.strip(), {}
    if isinstance(entry, dict):
        path = entry.get("path") or entry.get("repo")
        if not path:
            raise ValueError("Each repos entry must include 'path'")
        return str(path).strip(), entry
    raise ValueError(f"Invalid repos entry: {entry!r}")


def parse_email_list(raw: Any) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        s = raw.strip()
        return [s] if s else None
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if str(x).strip()]
        return out or None
    return None


def resolve_repo_filters(
    repo_cfg: dict,
    settings: ReportSettings,
) -> tuple[list[str], bool]:
    emails = parse_email_list(repo_cfg.get("author_emails")) or list(settings.author_emails)
    exclude_raw = repo_cfg.get("exclude_pr_merge_commits")
    exclude_pr_merge = (
        settings.exclude_pr_merge_commits if exclude_raw is None else bool(exclude_raw)
    )
    return emails, exclude_pr_merge


def is_pr_merge_commit(commit) -> bool:
    if len(commit.parents) <= 1:
        return False
    first = commit.message.strip().split("\n")[0].strip().lower()
    if "merge pull request" in first:
        return True
    if "merge remote-tracking branch" in first:
        return True
    if first.startswith("merge branch ") and " into " in first:
        return True
    return False


def is_environment_sync_merge(commit) -> bool:
    if len(commit.parents) <= 1:
        return False
    first = commit.message.strip().split("\n")[0].strip()
    return bool(ENV_SYNC_GITLAB.match(first) or ENV_SYNC_MERGE_BRANCH.match(first))


def commit_datetime_utc(commit, basis: CommitDateBasis):
    from datetime import timezone

    dt = (
        commit.authored_datetime
        if basis == "author"
        else commit.committed_datetime
    )
    return dt.astimezone(timezone.utc)


def commit_author_email_matches(commit, author_emails: list[str]) -> bool:
    wanted = {e.lower().strip() for e in author_emails if e.strip()}
    if not wanted:
        return False
    return (commit.author.email or "").lower().strip() in wanted
