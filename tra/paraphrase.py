import json

from tra.config import AppConfig, ReportSettings
from tra.debug_io import write_paraphrase_debug
from tra.gemini_client import GeminiClient
from tra.json_utils import strip_json_fence
from tra.prompt_loader import render_prompt


class ExtraTaskParaphraser:
    def __init__(
        self,
        client: GeminiClient,
        settings: ReportSettings,
        config: AppConfig,
    ) -> None:
        self._client = client
        self._settings = settings
        self._config = config

    def paraphrase(
        self,
        extra_tasks: list[dict],
        *,
        project_name: str = "",
    ) -> list[str]:
        if not extra_tasks:
            return []

        prompt = self._build_prompt(extra_tasks)
        label = project_name.strip() or "extras"
        write_paraphrase_debug(
            self._config,
            self._settings,
            label,
            extra_tasks,
            prompt,
            self._settings.gemini_paraphrase_model,
        )

        try:
            raw = strip_json_fence(
                self._client.generate(
                    prompt, model=self._settings.gemini_paraphrase_model
                )
            )
        except Exception:
            print("WARNING: Extra-task paraphrase failed; using original text.")
            return self._original_lines(extra_tasks)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            print("WARNING: Could not parse extra-task JSON; using original text.")
            return self._original_lines(extra_tasks)

        if not isinstance(parsed, list):
            return self._original_lines(extra_tasks)

        lines: list[str] = []
        for i, task in enumerate(extra_tasks):
            row = parsed[i] if i < len(parsed) else None
            if isinstance(row, dict) and row.get("text"):
                category = row.get("category") or task["category"]
                lines.append(f"{category}: {row['text']}")
            else:
                lines.append(f"{task['category']}: {task['description']}")
        return lines

    @staticmethod
    def _original_lines(extra_tasks: list[dict]) -> list[str]:
        return [f"{t['category']}: {t['description']}" for t in extra_tasks]

    @staticmethod
    def _build_prompt(extra_tasks: list[dict]) -> str:
        items = "\n".join(
            f"- [{t['category']}] {t['description']}" for t in extra_tasks
        )
        return render_prompt(
            "extra_tasks_paraphrase.md",
            extra_tasks_items=items,
        )
