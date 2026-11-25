import httpx

from judge.errors import JudgeNetworkError, JudgeResponseError, error_for_status
from judge.headers import parse_retry_after

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatAdapter:
    provider = "openai-compatible"

    def __init__(self, model, api_key=None, base_url=DEFAULT_BASE_URL, timeout=30.0, transport=None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._transport = transport

    def complete(self, prompt):
        url = f"{self.base_url}/chat/completions"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            with httpx.Client(transport=self._transport, timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TransportError as exc:
            raise JudgeNetworkError(
                f"Could not reach the model server ({exc.__class__.__name__})."
            ) from exc

        if response.status_code != 200:
            retry_after = parse_retry_after(response.headers.get("Retry-After"))
            raise error_for_status(response.status_code, retry_after=retry_after)

        try:
            text = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise JudgeResponseError(
                "The model server returned no usable text."
            ) from exc

        if not isinstance(text, str) or not text.strip():
            raise JudgeResponseError("The model server returned empty or null text.")
        return text