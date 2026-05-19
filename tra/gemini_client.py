import sys

from google import genai
from google.genai import errors as genai_errors


def format_api_error(err: Exception) -> str:
    if isinstance(err, genai_errors.APIError):
        code = int(getattr(err, "code", 0) or 0)
        status = str(getattr(err, "status", "") or "").upper()
        if code == 408 or "DEADLINE" in status or "TIMEOUT" in status:
            return "Gemini request timed out"
        if code == 503 or status == "UNAVAILABLE" or "UNAVAILABLE" in status:
            return "Gemini service unavailable (503)"
        if code == 429 or "RESOURCE_EXHAUSTED" in status:
            return "Gemini rate limit / quota exceeded (429)"
        if code in (500, 502):
            return "Gemini server error"
        if 400 <= code < 500:
            return f"Gemini client error ({code})"
        return f"Gemini API error ({code})"
    low = str(err).lower()
    if "timeout" in low or "timed out" in low or "deadline exceeded" in low:
        return "Gemini request timed out"
    if "503" in str(err) or "unavailable" in low or "high demand" in low:
        return "Gemini service unavailable (503)"
    return "Gemini API call failed"


class GeminiClient:
    def __init__(self, api_key: str, default_model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._default_model = default_model

    def generate(self, prompt: str, *, model: str | None = None) -> str:
        model_name = (model or self._default_model).strip() or self._default_model
        try:
            response = self._client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if not text:
                msg = "Gemini returned an empty response"
                print(msg, file=sys.stderr)
                raise RuntimeError(msg)
            return text
        except RuntimeError:
            raise
        except Exception as exc:
            msg = format_api_error(exc)
            print(msg, file=sys.stderr)
            raise RuntimeError(msg) from None
