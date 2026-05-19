from dataclasses import dataclass
from typing import Any

from git import Repo

from tra.types import EnvLabel

_repo_env_cache: dict[str, dict[str, str]] = {}

DEFAULT_ENV_MAP: dict[str, list[str]] = {
    "prod": ["main", "master"],
    "stage": ["release", "staging"],
    "dev": ["development", "develop", "dev"],
}

DEFAULT_ENV_LABEL = "dev"


@dataclass(frozen=True)
class EnvMapConfig:
    """Ordered (label, branch patterns). First matching label wins."""

    entries: tuple[tuple[str, tuple[str, ...]], ...]
    default_label: str

    @property
    def known_labels(self) -> frozenset[str]:
        labels = {label for label, _ in self.entries}
        labels.add(self.default_label)
        return frozenset(labels)

    def ordered_labels(self) -> list[str]:
        return [label for label, _ in self.entries]

    def priority_hint(self) -> str:
        ordered = self.ordered_labels()
        if not ordered:
            return self.default_label
        return " > ".join(ordered)

    def format_for_prompt(self) -> str:
        lines = [
            "Cada commit en la lista ya tiene su etiqueta de entorno entre corchetes.",
            "Esa etiqueta se obtuvo de env_map (ramas → entorno):",
            "",
        ]
        for label, patterns in self.entries:
            branches = ", ".join(patterns)
            lines.append(f"- {label}: ramas {branches}")
        lines.append(
            f"- {self.default_label}: cualquier otra rama (valor por defecto)"
        )
        lines.append("")
        lines.append(
            f"Prioridad al elegir env en un bullet (mayor a menor): {self.priority_hint()}."
        )
        return "\n".join(lines)


def parse_env_map(raw: Any, *, default_label: str | None = None) -> EnvMapConfig:
    fallback = (default_label or DEFAULT_ENV_LABEL).strip() or DEFAULT_ENV_LABEL

    source = DEFAULT_ENV_MAP if raw is None else raw
    if not isinstance(source, dict):
        print("WARNING: env_map must be a JSON object; using built-in defaults.")
        source = DEFAULT_ENV_MAP

    entries: list[tuple[str, tuple[str, ...]]] = []
    for env, branches in source.items():
        label = str(env).strip()
        if not label:
            continue
        if not isinstance(branches, list):
            print(f"WARNING: env_map.{env} must be a list of branch names; skipping.")
            continue
        patterns = tuple(str(b).strip().lower() for b in branches if str(b).strip())
        if patterns:
            entries.append((label, patterns))

    if not entries:
        print("WARNING: env_map is empty; using built-in defaults.")
        return parse_env_map(DEFAULT_ENV_MAP, default_label=fallback)

    return EnvMapConfig(entries=tuple(entries), default_label=fallback)


def _normalize_branch_ref(name: str) -> str:
    name = name.replace("remotes/origin/", "").replace("remotes/", "").strip()
    if "->" in name:
        name = name.split("->")[0].strip()
    return name


def branch_matches_pattern(branch: str, pattern: str) -> bool:
    normalized = _normalize_branch_ref(branch).lower()
    needle = pattern.strip().lower()
    if not needle:
        return False
    tail = normalized.split("/")[-1]
    if normalized == needle or tail == needle:
        return True
    if normalized.startswith(needle + "/"):
        return True
    return False


def resolve_env_label(branch_names: list[str], env_map: EnvMapConfig) -> EnvLabel:
    normalized = [_normalize_branch_ref(b) for b in branch_names if b.strip()]
    for label, patterns in env_map.entries:
        for branch in normalized:
            for pattern in patterns:
                if branch_matches_pattern(branch, pattern):
                    return label
    return env_map.default_label


def env_label_for_commit(repo: Repo, hexsha: str, env_map: EnvMapConfig) -> EnvLabel:
    rkey = f"{repo.working_tree_dir or repo.git_dir}:{id(env_map)}"
    cache = _repo_env_cache.setdefault(rkey, {})
    if hexsha in cache:
        return cache[hexsha]

    try:
        out = repo.git.branch("-a", "--contains", hexsha)
        lines = [ln for ln in out.splitlines() if ln.strip()]
        label = resolve_env_label(lines, env_map)
    except Exception:
        label = env_map.default_label

    cache[hexsha] = label
    return label
