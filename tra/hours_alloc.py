from typing import Literal, TypedDict

from tra.types import ReportSection


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
