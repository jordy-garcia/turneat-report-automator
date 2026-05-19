import json

from tra.env_labels import EnvMapConfig
from tra.json_utils import strip_json_fence
from tra.types import (
    BulletItem,
    CommitRecord,
    ReportSection,
    SubsectionBlock,
)


def coerce_bullet_item(raw: object, env_map: EnvMapConfig) -> BulletItem | None:
    default = env_map.default_label
    known = env_map.known_labels

    if isinstance(raw, dict):
        text = raw.get("text")
        env_raw = raw.get("env", default)
        if not isinstance(text, str) or not text.strip():
            return None
        env = str(env_raw).strip() if str(env_raw).strip() in known else default
        return BulletItem(text=text.strip(), env=env)
    if isinstance(raw, str) and raw.strip():
        return BulletItem(text=raw.strip(), env=default)
    return None


def _extract_report_blocks(data: object) -> list | None:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("reporte", "report", "sections"):
            blocks = data.get(key)
            if isinstance(blocks, list):
                return blocks
    return None


def _parse_sections_from_blocks(
    blocks: list, env_map: EnvMapConfig
) -> list[ReportSection]:
    sections: list[ReportSection] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        main = block.get("title")
        subs_raw = block.get("subsections")
        if not isinstance(main, str) or not main.strip():
            continue
        if not isinstance(subs_raw, list):
            continue

        subsections: list[SubsectionBlock] = []
        for sub in subs_raw:
            if not isinstance(sub, dict):
                continue
            sub_title = sub.get("title")
            bullets_raw = sub.get("bullets")
            if not isinstance(sub_title, str) or not sub_title.strip():
                continue
            if not isinstance(bullets_raw, list):
                continue
            bullets = [
                b
                for raw_b in bullets_raw
                if (b := coerce_bullet_item(raw_b, env_map))
            ]
            if bullets:
                subsections.append(
                    SubsectionBlock(title=sub_title.strip(), bullets=bullets)
                )
        if subsections:
            sections.append(ReportSection(title=main.strip(), subsections=subsections))

    return sections


def parse_hierarchy_json(
    raw: str, env_map: EnvMapConfig
) -> list[ReportSection] | None:
    text = strip_json_fence(raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    blocks = _extract_report_blocks(data)
    if blocks is None:
        return None
    if not blocks:
        return []

    sections = _parse_sections_from_blocks(blocks, env_map)
    return sections


def is_meta_report_title(title: str) -> bool:
    t = title.lower().strip()
    if not t:
        return False
    if "reporte de actividad" in t and "commit" in t:
        return True
    if "actividad de commit" in t:
        return True
    if "informe de commit" in t or "reporte de commit" in t:
        return True
    if t.startswith("reporte ") and "commit" in t:
        return True
    if "resumen de commit" in t or "resumen del periodo" in t:
        return True
    if "reporte mensual" in t or "informe mensual" in t:
        return True
    return False


def sanitize_report_sections(sections: list[ReportSection]) -> list[ReportSection]:
    out: list[ReportSection] = []
    for sec in sections:
        title = sec["title"].strip()
        if is_meta_report_title(title):
            out.append(ReportSection(title="", subsections=list(sec["subsections"])))
        else:
            out.append(sec)
    return out


def commits_for_prompt(commits: list[CommitRecord]) -> str:
    lines: list[str] = []
    for c in commits:
        who = (c.get("author") or "").strip()
        if who:
            lines.append(f"[{c['env']}] {who} | {c['message']}")
        else:
            lines.append(f"[{c['env']}] {c['message']}")
    return "\n".join(lines)
