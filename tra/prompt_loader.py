from pathlib import Path
from string import Template

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def render_prompt(filename: str, **variables: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    template = Template(path.read_text(encoding="utf-8"))
    return template.substitute(**variables)
