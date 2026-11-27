import pytest

import main
from judge.core import JudgeResult
from judge.errors import JudgeConfigError, error_for_status


def verdict(text):
    return JudgeResult(text=text, provider="fake", model="fake-model", attempts=1)


def judge_returning(text):
    def judge(prompt, api_key=None):
        return verdict(text)

    return judge


def judge_raising(error):
    def judge(prompt, api_key=None):
        raise error

    return judge


def semantic(judge, actual="the answer is four", expected="4", api_key=None):
    return main.evaluate_match(actual, expected, "semantic", api_key=api_key, judge=judge)


def test_judge_says_pass():
    result = semantic(judge_returning('{"passed": true, "reason": ""}'))
    assert result == {"passed": True, "reason": None, "method": "semantic"}


def test_judge_says_fail_and_its_reason_is_kept():
    result = semantic(judge_returning('{"passed": false, "reason": "numbers differ"}'))
    assert result["passed"] is False
    assert result["reason"] == "numbers differ"
    assert result["method"] == "semantic"


def test_json_wrapped_in_code_fences_is_accepted():
    result = semantic(judge_returning('```json\n{"passed": true, "reason": ""}\n```'))
    assert result["passed"] is True
    assert result["method"] == "semantic"


def test_prompt_has_both_texts_and_the_request_key_is_forwarded():
    seen = {}

    def judge(prompt, api_key=None):
        seen["prompt"] = prompt
        seen["key"] = api_key
        return verdict('{"passed": true, "reason": ""}')

    semantic(judge, actual="ACTUAL-TEXT", expected="EXPECTED-TEXT", api_key="request-key")
    assert "ACTUAL-TEXT" in seen["prompt"]
    assert "EXPECTED-TEXT" in seen["prompt"]
    assert seen["key"] == "request-key"


def test_default_judge_is_ask_judge(monkeypatch):
    monkeypatch.setattr(main, "ask_judge", judge_returning('{"passed": true, "reason": ""}'))
    result = main.evaluate_match("a", "b", "semantic")
    assert result["method"] == "semantic"


def test_no_judge_falls_back_to_contains_and_says_so():
    judge = judge_raising(JudgeConfigError("No judge configured."))
    good = semantic(judge, actual="it is 4", expected="4")
    assert good["passed"] is True
    assert good["method"] == "contains_fallback"
    bad = semantic(judge, actual="it is five", expected="4")
    assert bad["passed"] is False
    assert bad["method"] == "contains_fallback"
    assert "not configured" in bad["reason"]


def test_judge_failure_falls_back_and_explains():
    judge = judge_raising(error_for_status(503, detail="overloaded"))
    bad = semantic(judge, actual="it is five", expected="4")
    assert bad["passed"] is False
    assert bad["method"] == "contains_fallback"
    assert "unavailable" in bad["reason"]
    assert "overloaded" in bad["reason"]


@pytest.mark.parametrize(
    "text",
    [
        "I think it matches",
        "",
        '{"passed": "false"}',
        '{"passed": "yes", "reason": ""}',
        "[1, 2]",
        '{"reason": "no passed key"}',
    ],
)
def test_unreadable_answers_fall_back_instead_of_guessing(text):
    bad = semantic(judge_returning(text), actual="it is five", expected="4")
    assert bad["passed"] is False
    assert bad["method"] == "contains_fallback"
    assert "unreadable" in bad["reason"]


@pytest.mark.parametrize(
    "kind, actual, expected",
    [("contains", "hello world", "hello"), ("exact", "hello", "hello"), ("regex", "abc123", r"\d+")],
)
def test_simple_match_types_report_their_method_and_never_call_the_judge(kind, actual, expected):
    def judge(prompt, api_key=None):
        raise AssertionError("the judge must not be called for this match type")

    result = main.evaluate_match(actual, expected, kind, judge=judge)
    assert result["passed"] is True
    assert result["method"] == kind
    assert result["reason"] is None