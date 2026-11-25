import httpx

from judge.errors import JudgeNetworkError, JudgeResponseError, error_for_status

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _parse_retry_after(value):
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class GeminiAdapter:
    provider = "gemini"

    def __init__(self, model, api_key, timeout=30.0, transport=None):
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._transport = transport

    def complete(self, prompt):
        url = f"{BASE_URL}/{self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        try:
            with httpx.Client(transport=self._transport, timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TransportError as exc:
            raise JudgeNetworkError(
                f"Could not reach Gemini ({exc.__class__.__name__})."
            ) from exc

        if response.status_code != 200:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            raise error_for_status(response.status_code, retry_after=retry_after)

        try:
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise JudgeResponseError(
                "Gemini returned no usable text. The prompt may have been blocked."
            ) from exc

        if not text.strip():
            raise JudgeResponseError("Gemini returned empty text.")
        return text