import httpx
import pytest

from judge.adapters.anthropic import AnthropicAdapter
from judge.adapters.gemini import GeminiAdapter
from judge.adapters.openai_compat import OpenAICompatAdapter
from judge.errors import JudgeError

KEY = "secret-key-123"
ADAPTERS = [GeminiAdapter, OpenAICompatAdapter, AnthropicAdapter]


def make(cls, handler):
    return cls(model="m", api_key=KEY, transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("cls", ADAPTERS)
def test_provider_explanation_reaches_the_error_message(cls):
    def handler(request):
        return httpx.Response(
            503, json={"error": {"message": "The model is overloaded. Try again later."}}
        )

    with pytest.raises(JudgeError) as info:
        make(cls, handler).complete("hi")
    assert "The model is overloaded" in str(info.value)
    assert "503" in str(info.value)


@pytest.mark.parametrize("cls", ADAPTERS)
def test_an_echoed_key_is_never_in_the_error_message(cls):
    def handler(request):
        return httpx.Response(401, json={"error": {"message": f"API key {KEY} is not valid"}})

    with pytest.raises(JudgeError) as info:
        make(cls, handler).complete("hi")
    assert KEY not in str(info.value)


@pytest.mark.parametrize("cls", ADAPTERS)
def test_a_huge_html_error_page_stays_short(cls):
    def handler(request):
        return httpx.Response(502, text="<html>" + "oops " * 2000 + "</html>")

    with pytest.raises(JudgeError) as info:
        make(cls, handler).complete("hi")
    assert len(str(info.value)) < 400