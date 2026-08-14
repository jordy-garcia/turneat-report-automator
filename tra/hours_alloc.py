import copy
import json
from typing import Literal, TypedDict

from tra.config import AppConfig, ReportSettings
from tra.gemini_client import GeminiClient
from tra.json_utils import strip_json_fence
from tra.prompt_loader import render_prompt
from tra.types import ExtraTaskLine, ReportSection


class AllocItem(TypedDict):
    id: str
    kind: Literal["bullet", "extra"]
    text: str


def flatten_alloc_items(
    sections: list[ReportSection],
    extra_lines: list[str],
) -> list[AllocItem]:
    items: list[AllocItem] = []
    bullet_idx = 0
    for section in sections:
        for subsection in section["subsections"]:
            for bullet in subsection["bullets"]:
                items.append(
                    AllocItem(
                        id=f"b-{bullet_idx}",
                        kind="bullet",
                        text=bullet["text"],
                    )
                )
                bullet_idx += 1

    for extra_idx, line in enumerate(extra_lines):
        items.append(
            AllocItem(
                id=f"e-{extra_idx}",
                kind="extra",
                text=line,
            )
        )

    return items


def fallback_equal_hours(item_ids: list[str], total: float) -> dict[str, float]:
    n = len(item_ids)
    if n == 0:
        return {}
    units = int(round(float(total) * 2))
    base, rem = divmod(units, n)
    out: dict[str, float] = {}
    for i, item_id in enumerate(item_ids):
        out[item_id] = (base + (1 if i < rem else 0)) / 2
    return out


def normalize_hours(
    raw: dict[str, float],
    item_ids: list[str],
    total: float,
) -> dict[str, float]:
    if not item_ids:
        return {}

    total_units = int(round(float(total) * 2))
    if total_units <= 0:
        return {item_id: 0.0 for item_id in item_ids}

    values = {item_id: max(0.0, float(raw.get(item_id, 0))) for item_id in item_ids}
    if all(v == 0 for v in values.values()):
        return fallback_equal_hours(item_ids, total)

    raw_sum = sum(values.values())
    if raw_sum <= 0:
        return fallback_equal_hours(item_ids, total)

    scaled = {item_id: values[item_id] * total / raw_sum for item_id in item_ids}
    units = {item_id: round(scaled[item_id] * 2) for item_id in item_ids}

    diff = total_units - sum(units.values())
    while diff != 0:
        step = 1 if diff > 0 else -1
        if diff > 0:
            candidates = sorted(
                item_ids,
                key=lambda item_id: (scaled[item_id] - units[item_id] / 2, scaled[item_id]),
                reverse=True,
            )
        else:
            candidates = sorted(item_ids, key=lambda item_id: units[item_id], reverse=True)

        adjusted = False
        for item_id in candidates:
            next_units = units[item_id] + step
            if next_units >= 0:
                units[item_id] = next_units
                diff -= step
                adjusted = True
                break
        if not adjusted:
            break

    return {item_id: units[item_id] / 2.0 for item_id in item_ids}


class TaskHoursAllocator:
    def __init__(
        self,
        client: GeminiClient,
        settings: ReportSettings,
        config: AppConfig,
    ) -> None:
        self._client = client
        self._settings = settings
        self._config = config

    def allocate(
        self,
        project_name: str,
        sections: list[ReportSection],
        extra_lines: list[str],
        total_hours: int,
    ) -> tuple[list[ReportSection], list[ExtraTaskLine]]:
        items = flatten_alloc_items(sections, extra_lines)
        if not items or total_hours <= 0:
            return sections, [ExtraTaskLine(text=line) for line in extra_lines]

        prompt = self._build_prompt(project_name, total_hours, items)
        item_ids = [item["id"] for item in items]

        try:
            raw = strip_json_fence(
                self._client.generate(
                    prompt, model=self._settings.gemini_paraphrase_model
                )
            )
            parsed = json.loads(raw)
            raw_hours = self._parse_hours(parsed, item_ids)
        except Exception:
            print("WARNING: Task hours allocation failed; using equal split.")
            raw_hours = fallback_equal_hours(item_ids, total_hours)

        hours_map = normalize_hours(raw_hours, item_ids, total_hours)
        return self._apply_hours(sections, extra_lines, hours_map)

    @staticmethod
    def _build_prompt(
        project_name: str,
        total_hours: int,
        items: list[AllocItem],
    ) -> str:
        items_block = "\n".join(
            f"- id: {item['id']} | kind: {item['kind']} | text: {item['text']}"
            for item in items
        )
        return render_prompt(
            "task_hours_alloc.md",
            project_name=project_name,
            total_hours=str(total_hours),
            items_block=items_block,
        )

    @staticmethod
    def _parse_hours(parsed: object, item_ids: list[str]) -> dict[str, float]:
        if not isinstance(parsed, list):
            raise ValueError("expected JSON array")

        expected = set(item_ids)
        raw: dict[str, float] = {}
        for row in parsed:
            if not isinstance(row, dict):
                continue
            item_id = row.get("id")
            hours = row.get("hours")
            if item_id in expected and hours is not None:
                raw[str(item_id)] = float(hours)

        if set(raw.keys()) != expected:
            raise ValueError("missing or extra item ids")
        return raw

    @staticmethod
    def _apply_hours(
        sections: list[ReportSection],
        extra_lines: list[str],
        hours_map: dict[str, float],
    ) -> tuple[list[ReportSection], list[ExtraTaskLine]]:
        out_sections = copy.deepcopy(sections)
        bullet_idx = 0
        for section in out_sections:
            for subsection in section["subsections"]:
                for bullet in subsection["bullets"]:
                    bullet["hours"] = hours_map[f"b-{bullet_idx}"]
                    bullet_idx += 1

        out_extras = [
            ExtraTaskLine(text=line, hours=hours_map[f"e-{i}"])
            for i, line in enumerate(extra_lines)
        ]
        return out_sections, out_extras
