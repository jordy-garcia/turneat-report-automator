import sys

from tra.ai.base import TextGenerator
from tra.ai.gemini import GeminiClient

SUPPORTED_PROVIDERS = ("gemini",)


def create_text_generator(
    provider: str, api_key: str, default_model: str
) -> TextGenerator:
    name = (provider or "").strip().lower()
    if name == "gemini":
        return GeminiClient(api_key, default_model)

    supported = ", ".join(SUPPORTED_PROVIDERS)
    print(
        f"ERROR: Unknown ai_provider {provider!r}. Supported: {supported}.",
        file=sys.stderr,
    )
    sys.exit(1)
