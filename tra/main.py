from tra.cleanup import prepare_output_dirs
from tra.collector import collect_monthly_commits
from tra.config import AppConfig
from tra.dates import month_name_es
from tra.gemini_client import GeminiClient
from tra.git_filters import parse_repo_entry, resolve_repo_filters
from tra.hours import resolve_project_hours
from tra.paraphrase import ExtraTaskParaphraser
from tra.pdf_builder import build_project_pdf
from tra.summarizer import CommitSummarizer
from tra.types import ProjectData


def collect_all_projects(
    config: AppConfig,
    extras_by_project: dict[str, list[dict]] | None = None,
) -> list[ProjectData]:
    settings = config.settings
    extras_by_project = extras_by_project or {}
    results: list[ProjectData] = []

    for project in config.projects:
        all_commits = []
        for entry in project["repos"]:
            repo_path, repo_cfg = parse_repo_entry(entry)
            author_emails, exclude_pr_merge = resolve_repo_filters(repo_cfg, settings)
            repo_commits = collect_monthly_commits(
                repo_path,
                author_emails,
                settings.month,
                settings.year,
                tz_name=settings.calendar_timezone,
                date_basis=settings.commit_date_basis,
                exclude_pr_merge_commits=exclude_pr_merge,
                exclude_environment_sync_merges=settings.exclude_environment_sync_merges,
                env_map=settings.env_map,
            )
            all_commits.extend(repo_commits)

        raw_hours = project.get("hours")
        manual_hours = max(0, int(raw_hours)) if raw_hours is not None else None
        name = project["name"]

        results.append(
            ProjectData(
                name=name,
                commits=all_commits,
                count=len(all_commits),
                extras=extras_by_project.get(name, []),
                manual_hours=manual_hours,
            )
        )

    return results


def run(
    config: AppConfig,
    *,
    extras_by_project: dict[str, list[dict]] | None = None,
) -> None:
    settings = config.settings
    if settings.month < 1 or settings.month > 12 or settings.year < 1970:
        raise ValueError(
            "Report period is not set. Use the CLI (uv run reporter) so month/year "
            "are resolved before run()."
        )

    prepare_output_dirs(config.debug_dir, config.reports_dir)

    gemini = GeminiClient(config.api_key, settings.gemini_model)
    summarizer = CommitSummarizer(gemini, settings, config)
    paraphraser = ExtraTaskParaphraser(gemini, settings, config)

    projects = collect_all_projects(config, extras_by_project=extras_by_project)
    month_label = month_name_es(settings.month)
    date_label = (
        "author date (when the change was written)"
        if settings.commit_date_basis == "author"
        else "committer date (when it landed in the repo)"
    )
    print(
        f"Period: {month_label} {settings.year} | "
        f"timezone {settings.calendar_timezone} | {date_label}"
    )

    if settings.report_hours:
        project_hours: list[int | None] = resolve_project_hours(
            settings.total_hours,
            [p["manual_hours"] for p in projects],
            [p["count"] for p in projects],
        )
    else:
        project_hours = [None] * len(projects)

    for idx, data in enumerate(projects):
        sections = summarizer.summarize(data["name"], data["commits"])
        extra_lines = paraphraser.paraphrase(
            data["extras"], project_name=data["name"]
        )
        output = (
            config.reports_dir
            / f"Report_{data['name']}_{month_label}_{settings.year}.pdf"
        )
        build_project_pdf(
            project_name=data["name"],
            responsible_name=settings.responsible_name,
            month=settings.month,
            year=settings.year,
            assigned_hours=project_hours[idx],
            sections=sections,
            extra_lines=extra_lines,
            output_path=str(output),
            tag_environment=settings.tag_environment,
        )
        print(f"Wrote {output}")
