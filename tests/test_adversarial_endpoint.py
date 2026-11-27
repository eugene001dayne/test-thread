import json

import httpx
from fastapi.testclient import TestClient

import main
from judge.core import JudgeResult
from judge.errors import JudgeConfigError, error_for_status

client = TestClient(main.app)

SUITE = {"id": "s1", "name": "demo", "agent_endpoint": "https://agent.example.com/chat"}
CASES = [{"name": "greet", "input": "hello", "expected_output": "hi", "match_type": "contains"}]
URL = "/suites/s1/generate-adversarial"


def fake_db(suites=None, cases=None):
    suites = [SUITE] if suites is None else suites
    cases = CASES if cases is None else cases

    def handler(request):
        if request.url.path.endswith("/test_suites"):
            return httpx.Response(200, json=suites)
        if request.url.path.endswith("/test_cases"):
            return httpx.Response(200, json=cases)
        return httpx.Response(404, json=[])

    return lambda: httpx.Client(base_url="http://fake", transport=httpx.MockTransport(handler))


def judge_returning(text):
    seen = []

    def judge(prompt, api_key=None):
        seen.append(prompt)
        return JudgeResult(text=text, provider="fake", model="fake-model", attempts=1)

    judge.seen = seen
    return judge


def judge_raising(error):
    def judge(prompt, api_key=None):
        raise error

    return judge


def item(name, **extra):
    return {"name": name, "input": f"in-{name}", "expected_output": f"out-{name}", **extra}


def setup(monkeypatch, judge, **db_kwargs):
    monkeypatch.setattr(main, "db", fake_db(**db_kwargs))
    monkeypatch.setattr(main, "ask_judge", judge)


def test_success_returns_cases_and_who_judged(monkeypatch):
    setup(monkeypatch, judge_returning(json.dumps([item("a"), item("b")])))
    response = client.post(URL, json={"count": 2, "focus": "safety"})
    assert response.status_code == 200
    data = response.json()
    assert data["generated_count"] == 2
    assert data["cases"][0]["source"] == "adversarial"
    assert data["judge"] == {"provider": "fake", "model": "fake-model"}


def test_prompt_contains_existing_cases_and_the_count(monkeypatch):
    judge = judge_returning(json.dumps([item("a")]))
    setup(monkeypatch, judge)
    client.post(URL, json={"count": 2})
    prompt = judge.seen[0]
    assert "hello" in prompt
    assert "exactly 2" in prompt


def test_json_wrapped_in_code_fences_is_accepted(monkeypatch):
    setup(monkeypatch, judge_returning("```json\n" + json.dumps([item("a")]) + "\n```"))
    response = client.post(URL, json={"count": 1})
    assert response.status_code == 200
    assert response.json()["generated_count"] == 1


def test_count_is_clamped_to_twenty(monkeypatch):
    setup(monkeypatch, judge_returning(json.dumps([item(f"c{i}") for i in range(30)])))
    response = client.post(URL, json={"count": 100})
    assert response.json()["generated_count"] == 20


def test_untrusted_items_are_cleaned(monkeypatch):
    items = [
        item("a", match_type="regex"),
        "just a string",
        {"name": "b", "input": "", "expected_output": "z"},
        item("c", match_type="exact"),
        item("d", match_type="semantic"),
    ]
    setup(monkeypatch, judge_returning(json.dumps(items)))
    response = client.post(URL, json={"count": 10})
    cases = response.json()["cases"]
    assert [c["name"] for c in cases] == ["a", "c", "d"]
    assert [c["match_type"] for c in cases] == ["contains", "exact", "semantic"]


def test_unreadable_answer_is_a_502(monkeypatch):
    setup(monkeypatch, judge_returning("sorry, I cannot do that"))
    response = client.post(URL, json={})
    assert response.status_code == 502
    assert "readable" in response.json()["detail"]


def test_json_that_is_not_a_list_is_a_502(monkeypatch):
    setup(monkeypatch, judge_returning('{"cases": []}'))
    response = client.post(URL, json={})
    assert response.status_code == 502
    assert "readable" in response.json()["detail"]


def test_no_judge_configured_is_a_400_that_says_what_to_set(monkeypatch):
    setup(monkeypatch, judge_raising(JudgeConfigError("No judge configured. Set JUDGE_PROVIDER.")))
    response = client.post(URL, json={})
    assert response.status_code == 400
    assert "JUDGE_PROVIDER" in response.json()["detail"]


def test_judge_failure_is_a_502_with_the_providers_explanation(monkeypatch):
    setup(monkeypatch, judge_raising(error_for_status(503, detail="overloaded")))
    response = client.post(URL, json={})
    assert response.status_code == 502
    assert "overloaded" in response.json()["detail"]


def test_invalid_focus_is_rejected_before_anything_else(monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("must not be reached")

    monkeypatch.setattr(main, "db", never)
    monkeypatch.setattr(main, "ask_judge", never)
    response = client.post(URL, json={"focus": "nonsense"})
    assert response.status_code == 400
    assert "focus" in response.json()["detail"]


def test_unknown_suite_is_a_404(monkeypatch):
    setup(monkeypatch, judge_returning("[]"), suites=[])
    assert client.post(URL, json={}).status_code == 404


def test_suite_without_cases_is_a_400(monkeypatch):
    setup(monkeypatch, judge_returning("[]"), cases=[])
    response = client.post(URL, json={})
    assert response.status_code == 400
    assert "no test cases" in response.json()["detail"].lower()