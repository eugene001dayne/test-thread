import httpx
import pytest

from judge.adapters.gemini import GeminiAdapter
from judge.errors import (
    JudgeModelNotFoundError,
    JudgeNetworkError,
    JudgeRateLimitError,
    JudgeResponseError,
)

OK_BODY = {"candidates": [{"content": {"parts": [{"text": "hello there"}]}}]}


def make_adapter(handler):
    return GeminiAdapter(
        model="test-model",
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )


def test_sends_model_in_url_and_key_in_header_only():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key_header"] = request.headers.get("x-goog-api-key")
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler).complete("say hi")
    assert "test-model" in seen["url"]
    assert "secret-key" not in seen["url"]
    assert seen["key_header"] == "secret-key"
    assert "say hi" in seen["body"]


def test_returns_the_text_from_the_response():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.complete("hi") == "hello there"


def test_provider_and_model_are_reported():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.provider == "gemini"
    assert adapter.model == "test-model"


def test_404_becomes_model_not_found():
    adapter = make_adapter(lambda request: httpx.Response(404, json={"error": {"message": "gone"}}))
    with pytest.raises(JudgeModelNotFoundError):
        adapter.complete("hi")


def test_retry_after_header_is_parsed():
    adapter = make_adapter(lambda request: httpx.Response(429, headers={"Retry-After": "2"}))
    with pytest.raises(JudgeRateLimitError) as info:
        adapter.complete("hi")
    assert info.value.retry_after == 2.0


def test_response_without_text_is_an_error_not_an_empty_string():
    adapter = make_adapter(lambda request: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(JudgeResponseError) as info:
        adapter.complete("hi")
    assert info.value.retryable is False


def test_network_failure_is_retryable():
    def handler(request):
        raise httpx.ConnectTimeout("too slow")

    adapter = make_adapter(handler)
    with pytest.raises(JudgeNetworkError) as info:
        adapter.complete("hi")
    assert info.value.retryable is True