import json

import httpx
import pytest

from judge.adapters.openai_compat import OpenAICompatAdapter
from judge.errors import (
    JudgeAuthError,
    JudgeModelNotFoundError,
    JudgeNetworkError,
    JudgeRateLimitError,
    JudgeResponseError,
)

OK_BODY = {"choices": [{"message": {"role": "assistant", "content": "hello there"}}]}


def make_adapter(handler, **overrides):
    options = {
        "model": "test-model",
        "api_key": "secret-key",
        "base_url": "https://llm.example.com/v1",
    }
    options.update(overrides)
    return OpenAICompatAdapter(transport=httpx.MockTransport(handler), **options)


def test_sends_model_and_prompt_in_body_and_key_in_header_only():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        seen["raw"] = request.content.decode()
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler).complete("say hi")
    assert seen["url"] == "https://llm.example.com/v1/chat/completions"
    assert seen["auth"] == "Bearer secret-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["messages"][0]["content"] == "say hi"
    assert "secret-key" not in seen["url"]
    assert "secret-key" not in seen["raw"]


def test_no_key_means_no_authorization_header():
    seen = {}

    def handler(request):
        seen["has_auth"] = "authorization" in request.headers
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler, api_key=None).complete("hi")
    assert seen["has_auth"] is False


def test_trailing_slash_on_base_url_is_fine():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler, base_url="https://llm.example.com/v1/").complete("hi")
    assert seen["url"] == "https://llm.example.com/v1/chat/completions"


def test_returns_the_text_from_the_response():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.complete("hi") == "hello there"


def test_provider_and_model_are_reported():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.provider == "openai-compatible"
    assert adapter.model == "test-model"


def test_default_base_url_is_openai():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json=OK_BODY)

    adapter = OpenAICompatAdapter(
        model="m", api_key="k", transport=httpx.MockTransport(handler)
    )
    adapter.complete("hi")
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"


def test_401_becomes_auth_error():
    adapter = make_adapter(lambda request: httpx.Response(401, json={"error": "no"}))
    with pytest.raises(JudgeAuthError):
        adapter.complete("hi")


def test_404_becomes_model_not_found():
    adapter = make_adapter(lambda request: httpx.Response(404, json={"error": "gone"}))
    with pytest.raises(JudgeModelNotFoundError):
        adapter.complete("hi")


def test_retry_after_header_is_parsed():
    adapter = make_adapter(lambda request: httpx.Response(429, headers={"Retry-After": "2"}))
    with pytest.raises(JudgeRateLimitError) as info:
        adapter.complete("hi")
    assert info.value.retry_after == 2.0


def test_no_choices_is_an_error_not_an_empty_string():
    adapter = make_adapter(lambda request: httpx.Response(200, json={"choices": []}))
    with pytest.raises(JudgeResponseError) as info:
        adapter.complete("hi")
    assert info.value.retryable is False


def test_null_content_is_an_error():
    body = {"choices": [{"message": {"role": "assistant", "content": None}}]}
    adapter = make_adapter(lambda request: httpx.Response(200, json=body))
    with pytest.raises(JudgeResponseError):
        adapter.complete("hi")


def test_network_failure_is_retryable():
    def handler(request):
        raise httpx.ConnectTimeout("too slow")

    adapter = make_adapter(handler)
    with pytest.raises(JudgeNetworkError) as info:
        adapter.complete("hi")
    assert info.value.retryable is True