import os

from git import Repo

from tra.dates import month_bounds_utc
from tra.env_labels import EnvMapConfig, env_label_for_commit
from tra.git_filters import (
    commit_author_email_matches,
    commit_datetime_utc,
    is_environment_sync_merge,
    is_pr_merge_commit,
)
from tra.types import CommitDateBasis, CommitRecord


def collect_monthly_commits(
    repo_path: str,
    author_emails: list[str],
    month: int,
    year: int,
    *,
    tz_name: str,
    date_basis: CommitDateBasis,
    exclude_pr_merge_commits: bool = False,
    exclude_environment_sync_merges: bool = True,
    env_map: EnvMapConfig,
) -> list[CommitRecord]:
    try:
        repo = Repo(repo_path)
        shallow_marker = os.path.join(repo_path, ".git", "shallow")
        if os.path.isfile(shallow_marker):
            print(
                f"WARNING: Shallow clone at {repo_path}; history may be incomplete. "
                "Run git fetch --unshallow if older commits are missing."
            )

        start_date, end_date = month_bounds_utc(year, month, tz_name)
        results: list[CommitRecord] = []
        seen_hashes: set[str] = set()

        for commit in repo.iter_commits("--all"):
            if commit.hexsha in seen_hashes:
                continue

            commit_time = commit_datetime_utc(commit, date_basis)
            if not (start_date <= commit_time < end_date):
                continue
            if exclude_pr_merge_commits and is_pr_merge_commit(commit):
                continue
            if exclude_environment_sync_merges and is_environment_sync_merge(commit):
                continue
            if not commit_author_email_matches(commit, author_emails):
                continue

            msg = commit.message.strip().split("\n")[0]
            if not msg:
                continue

            auth_name = (commit.author.name or "").strip()
            auth_email = (commit.author.email or "").strip()
            results.append(
                CommitRecord(
                    sha=commit.hexsha,
                    message=msg,
                    env=env_label_for_commit(repo, commit.hexsha, env_map),
                    author=f"{auth_name} <{auth_email}>",
                    author_email=auth_email,
                )
            )
            seen_hashes.add(commit.hexsha)

        return results
    except Exception as exc:
        print(f"WARNING: Could not read repository {repo_path}: {exc}")
        return []
