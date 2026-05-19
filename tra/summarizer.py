from tra.config import AppConfig, ReportSettings
from tra.debug_io import write_ai_context_debug
from tra.dates import month_name_es
from tra.gemini_client import GeminiClient
from tra.prompt_loader import render_prompt
from tra.report_parse import (
    commits_for_prompt,
    parse_hierarchy_json,
    sanitize_report_sections,
)
from tra.types import (
    BulletItem,
    CommitRecord,
    EnvLabel,
    ReportSection,
    SubsectionBlock,
)


class CommitSummarizer:
    def __init__(
        self, client: GeminiClient, settings: ReportSettings, config: AppConfig
    ) -> None:
        self._client = client
        self._settings = settings
        self._config = config

    def summarize(self, project_name: str, commits: list[CommitRecord]) -> list[ReportSection]:
        if not commits:
            return [
                ReportSection(
                    title="Soporte y coordinación",
                    subsections=[
                        SubsectionBlock(
                            title="Actividades del periodo:",
                            bullets=[
                                BulletItem(
                                    text=(
                                        "Realicé seguimiento del proyecto, revisiones y "
                                        "soporte continuo sin entregables de código en el periodo."
                                    ),
                                    env=self._settings.env_map.default_label,
                                )
                            ],
                        )
                    ],
                )
            ]

        prompt = self._build_prompt(project_name, commits)
        write_ai_context_debug(
            self._config,
            self._settings,
            project_name,
            commits,
            prompt,
            self._settings.gemini_model,
        )

        try:
            raw = self._client.generate(prompt)
        except Exception:
            print(
                "WARNING: Gemini summary failed; listing raw commit messages instead."
            )
            return self._fallback_from_commits(commits)

        parsed = parse_hierarchy_json(raw, self._settings.env_map)
        if parsed is not None:
            return sanitize_report_sections(parsed)

        print("WARNING: Invalid hierarchical JSON from Gemini; using plain text block.")
        paragraphs = [p.strip() for p in raw.strip().split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [raw.strip()]
            return [
                ReportSection(
                    title="Entregas del periodo",
                    subsections=[
                        SubsectionBlock(
                            title="Detalle:",
                            bullets=[
                                BulletItem(
                                    text=b, env=self._settings.env_map.default_label
                                )
                                for b in paragraphs
                            ],
                        )
                    ],
                )
            ]

    def _fallback_from_commits(self, commits: list[CommitRecord]) -> list[ReportSection]:
        known = self._settings.env_map.known_labels
        default = self._settings.env_map.default_label
        bullets: list[BulletItem] = []
        for c in commits:
            msg = (c.get("message") or "").strip().split("\n")[0][:500]
            env_raw = c.get("env")
            env = env_raw if env_raw in known else default
            bullets.append(BulletItem(text=msg or "(sin mensaje)", env=env))
        return [
            ReportSection(
                title="Entregas del periodo",
                subsections=[
                    SubsectionBlock(
                        title="Detalle (sin resumen automático):",
                        bullets=bullets[:80],
                    )
                ],
            )
        ]

    def _build_prompt(self, project_name: str, commits: list[CommitRecord]) -> str:
        env_map = self._settings.env_map
        ordered = env_map.ordered_labels()
        labels = " | ".join(ordered) if ordered else env_map.default_label
        example = ordered[0] if ordered else env_map.default_label
        return render_prompt(
            "commit_summary.md",
            project_name=project_name,
            month=month_name_es(self._settings.month),
            year=str(self._settings.year),
            timezone=self._settings.calendar_timezone,
            commits_block=commits_for_prompt(commits),
            env_labels=labels,
            env_example=example,
            env_priority=env_map.priority_hint(),
            env_mapping=env_map.format_for_prompt(),
        )
