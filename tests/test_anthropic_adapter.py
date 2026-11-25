import json

import httpx
import pytest

from judge.adapters.anthropic import AnthropicAdapter
from judge.errors import (
    JudgeAuthError,
    JudgeModelNotFoundError,
    JudgeNetworkError,
    JudgeRateLimitError,
    JudgeResponseError,
    JudgeServerError,
)

OK_BODY = {
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "hello there"}],
    "stop_reason": "end_turn",
}


def make_adapter(handler, **overrides):
    options = {"model": "test-model", "api_key": "secret-key"}
    options.update(overrides)
    return AnthropicAdapter(transport=httpx.MockTransport(handler), **options)


def test_sends_the_right_url_headers_and_body():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        seen["raw"] = request.content.decode()
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler).complete("say hi")
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["key"] == "secret-key"
    assert seen["version"]
    assert seen["auth"] is None
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["messages"][0]["role"] == "user"
    assert seen["body"]["messages"][0]["content"] == "say hi"
    assert "secret-key" not in seen["url"]
    assert "secret-key" not in seen["raw"]


def test_max_tokens_is_always_sent_and_can_be_changed():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["max_tokens"])
        return httpx.Response(200, json=OK_BODY)

    make_adapter(handler).complete("hi")
    make_adapter(handler, max_tokens=50).complete("hi")
    assert seen[0] > 0
    assert seen[1] == 50


def test_returns_the_text_from_the_response():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.complete("hi") == "hello there"


def test_joins_text_blocks_and_ignores_other_block_types():
    body = {
        "content": [
            {"type": "thinking", "thinking": "hmm"},
            {"type": "text", "text": "part one "},
            {"type": "tool_use", "id": "x", "name": "y", "input": {}},
            {"type": "text", "text": "part two"},
        ]
    }
    adapter = make_adapter(lambda request: httpx.Response(200, json=body))
    assert adapter.complete("hi") == "part one part two"


def test_provider_and_model_are_reported():
    adapter = make_adapter(lambda request: httpx.Response(200, json=OK_BODY))
    assert adapter.provider == "anthropic"
    assert adapter.model == "test-model"


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


def test_overloaded_529_is_a_retryable_server_error():
    adapter = make_adapter(lambda request: httpx.Response(529, json={"error": "overloaded"}))
    with pytest.raises(JudgeServerError) as info:
        adapter.complete("hi")
    assert info.value.retryable is True


def test_empty_content_is_an_error_not_an_empty_string():
    adapter = make_adapter(lambda request: httpx.Response(200, json={"content": []}))
    with pytest.raises(JudgeResponseError) as info:
        adapter.complete("hi")
    assert info.value.retryable is False


def test_only_non_text_blocks_is_an_error():
    body = {"content": [{"type": "tool_use", "id": "x", "name": "y", "input": {}}]}
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