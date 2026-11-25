from fastapi.testclient import TestClient

import main
from judge.core import JudgeResult
from judge.errors import JudgeAuthError, JudgeConfigError

client = TestClient(main.app)

BODY = {"input": "hi there", "expected_output": "hello", "actual_output": "bye"}


def fake_result(text="try changing the prompt"):
    return JudgeResult(text=text, provider="fake", model="fake-model", attempts=1)


def test_returns_the_judges_text_and_who_judged(monkeypatch):
    monkeypatch.setattr(main, "ask_judge", lambda prompt, **kw: fake_result("try X"))
    response = client.post("/diagnose", json=BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["diagnosis"] == "try X"
    assert data["judge"] == {"provider": "fake", "model": "fake-model"}


def test_the_prompt_contains_the_case(monkeypatch):
    seen = {}

    def fake(prompt, **kw):
        seen["prompt"] = prompt
        return fake_result()

    monkeypatch.setattr(main, "ask_judge", fake)
    client.post("/diagnose", json=BODY)
    assert "hi there" in seen["prompt"]
    assert "hello" in seen["prompt"]
    assert "bye" in seen["prompt"]


def test_missing_setup_is_a_400_that_says_what_to_set(monkeypatch):
    def fake(prompt, **kw):
        raise JudgeConfigError("No judge configured. Set JUDGE_PROVIDER to one of: gemini, openai, anthropic.")

    monkeypatch.setattr(main, "ask_judge", fake)
    response = client.post("/diagnose", json=BODY)
    assert response.status_code == 400
    assert "JUDGE_PROVIDER" in response.json()["detail"]


def test_a_failing_judge_is_a_502_not_an_empty_200(monkeypatch):
    def fake(prompt, **kw):
        raise JudgeAuthError("API key was rejected. Check JUDGE_API_KEY. (HTTP 401)", status_code=401)

    monkeypatch.setattr(main, "ask_judge", fake)
    response = client.post("/diagnose", json=BODY)
    assert response.status_code == 502
    assert "JUDGE_API_KEY" in response.json()["detail"]
    assert "diagnosis" not in response.json()