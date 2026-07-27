from typing import Protocol


class TextGenerator(Protocol):
    def generate(self, prompt: str, *, model: str | None = None) -> str: ...
