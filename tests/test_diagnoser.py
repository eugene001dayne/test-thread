import pytest

from judge.core import JudgeResult
from judge.diagnosis import Diagnoser
from judge.errors import JudgeConfigError, error_for_status

CASE = {"input": "what is 2+2", "expected_output": "4"}


def result(text="try X"):
    return JudgeResult(text=text, provider="fake", model="fake-model", attempts=1)


class Recorder:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_returns_the_judges_text():
    ask = Recorder([result("try X")])
    assert Diagnoser(ask).diagnose(CASE, "5", "no match") == "try X"


def test_prompt_contains_the_case_the_output_and_the_reason():
    ask = Recorder([result()])
    Diagnoser(ask).diagnose(CASE, "five", "expected text not found")
    prompt = ask.prompts[0]
    for piece in ("what is 2+2", "4", "five", "expected text not found"):
        assert piece in prompt


def test_unconfigured_judge_gives_none_quietly_and_is_not_asked_again():
    ask = Recorder([JudgeConfigError("No judge configured.")])
    diagnoser = Diagnoser(ask)
    assert diagnoser.diagnose(CASE, "5", "r") is None
    assert diagnoser.diagnose(CASE, "6", "r") is None
    assert len(ask.prompts) == 1


def test_a_failing_judge_gives_an_honest_marker_not_a_blank():
    ask = Recorder([error_for_status(503, detail="overloaded")])
    text = Diagnoser(ask).diagnose(CASE, "5", "r")
    assert text.startswith("[Diagnosis unavailable")
    assert "overloaded" in text


def test_after_one_failure_the_rest_of_the_run_skips_the_judge():
    ask = Recorder([error_for_status(503)])
    diagnoser = Diagnoser(ask)
    diagnoser.diagnose(CASE, "5", "r")
    second = diagnoser.diagnose(CASE, "6", "r")
    assert len(ask.prompts) == 1
    assert second.startswith("[Diagnosis unavailable")


def test_programming_errors_are_not_swallowed():
    ask = Recorder([KeyError("bug")])
    with pytest.raises(KeyError):
        Diagnoser(ask).diagnose(CASE, "5", "r")