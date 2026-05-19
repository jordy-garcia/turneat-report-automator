def distribute_hours_proportional(total_hours: int, counts: list[int]) -> list[int]:
    n = len(counts)
    if n == 0:
        return []
    total = max(0, int(total_hours))
    weight_sum = sum(counts)
    if weight_sum <= 0:
        base, rem = divmod(total, n)
        return [base + (1 if i < rem else 0) for i in range(n)]
    raw = [total * c / weight_sum for c in counts]
    floors = [int(x) for x in raw]
    remainder = total - sum(floors)
    order = sorted(range(n), key=lambda i: (raw[i] - floors[i], i), reverse=True)
    result = floors[:]
    for k in range(remainder):
        result[order[k]] += 1
    return result


def resolve_project_hours(
    total_hours: int,
    manual_hours: list[int | None],
    commit_counts: list[int],
) -> list[int]:
    """
    Use per-project manual hours when set; split the remaining budget across
    projects without manual hours, proportional to commit count.
    """
    n = len(manual_hours)
    if n == 0:
        return []

    manual_sum = sum(h for h in manual_hours if h is not None)
    if manual_sum > total_hours:
        print(
            f"WARNING: Manual project hours ({manual_sum}) exceed "
            f"total_hours ({total_hours})."
        )

    remainder = max(0, int(total_hours) - manual_sum)
    auto_indices = [i for i, h in enumerate(manual_hours) if h is None]

    assigned = [0] * n
    for i, hours in enumerate(manual_hours):
        if hours is not None:
            assigned[i] = max(0, int(hours))

    if auto_indices:
        auto_counts = [commit_counts[i] for i in auto_indices]
        distributed = distribute_hours_proportional(remainder, auto_counts)
        for idx, project_index in enumerate(auto_indices):
            assigned[project_index] = distributed[idx]

    return assigned
