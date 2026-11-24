import httpx
import main


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}


def fake_post_factory(calls):
    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return FakeResponse()
    return fake_post


def test_model_name_is_configurable(monkeypatch):
    calls = []
    monkeypatch.setattr(httpx, "post", fake_post_factory(calls))
    monkeypatch.setattr(main, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(main, "GEMINI_MODEL", "my-test-model")
    main.gemini_call("hi")
    assert "my-test-model" in calls[0]["url"]


def test_key_goes_in_header_not_url(monkeypatch):
    calls = []
    monkeypatch.setattr(httpx, "post", fake_post_factory(calls))
    monkeypatch.setattr(main, "GEMINI_API_KEY", None)
    main.gemini_call("hi", "caller-key")
    assert "caller-key" not in calls[0]["url"]
    assert calls[0]["headers"]["x-goog-api-key"] == "caller-key"