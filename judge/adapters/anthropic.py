import httpx

from judge.errors import JudgeNetworkError, JudgeResponseError, error_for_status
from judge.headers import parse_retry_after

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
API_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 1024


class AnthropicAdapter:
    provider = "anthropic"

    def __init__(
        self,
        model,
        api_key,
        base_url=DEFAULT_BASE_URL,
        max_tokens=DEFAULT_MAX_TOKENS,
        timeout=30.0,
        transport=None,
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._transport = transport

    def complete(self, prompt):
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": API_VERSION,
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            with httpx.Client(transport=self._transport, timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TransportError as exc:
            raise JudgeNetworkError(
                f"Could not reach Anthropic ({exc.__class__.__name__})."
            ) from exc

        if response.status_code != 200:
            retry_after = parse_retry_after(response.headers.get("Retry-After"))
            raise error_for_status(response.status_code, retry_after=retry_after)

        try:
            blocks = response.json()["content"]
            text = "".join(
                block["text"] for block in blocks if block.get("type") == "text"
            )
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise JudgeResponseError(
                "Anthropic returned no usable text."
            ) from exc

        if not text.strip():
            raise JudgeResponseError(
                "Anthropic returned no text (the answer may have been a refusal or a tool call)."
            )
        return text