import pytest

from judge.core import ask
from judge.errors import JudgeAuthError, JudgeServerError, error_for_status


class FakeAdapter:
    provider = "fake"
    model = "fake-model"

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def complete(self, prompt):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def test_success_on_first_try():
    adapter = FakeAdapter(["hello"])
    result = ask("hi", adapter, sleep=lambda s: None)
    assert result.text == "hello"
    assert result.attempts == 1
    assert result.provider == "fake"
    assert result.model == "fake-model"


def test_retries_server_errors_then_succeeds():
    adapter = FakeAdapter([error_for_status(503), error_for_status(503), "ok"])
    sleeps = []
    result = ask("hi", adapter, sleep=sleeps.append)
    assert result.text == "ok"
    assert result.attempts == 3
    assert len(sleeps) == 2


def test_gives_up_after_max_attempts_and_raises():
    adapter = FakeAdapter([error_for_status(503)] * 3)
    with pytest.raises(JudgeServerError):
        ask("hi", adapter, max_attempts=3, sleep=lambda s: None)
    assert adapter.calls == 3


def test_auth_errors_are_not_retried():
    adapter = FakeAdapter([error_for_status(401)])
    sleeps = []
    with pytest.raises(JudgeAuthError):
        ask("hi", adapter, sleep=sleeps.append)
    assert adapter.calls == 1
    assert sleeps == []


def test_retry_after_is_respected():
    adapter = FakeAdapter([error_for_status(429, retry_after=2.5), "ok"])
    sleeps = []
    ask("hi", adapter, sleep=sleeps.append)
    assert sleeps == [2.5]


def test_backoff_grows_between_attempts():
    adapter = FakeAdapter([error_for_status(503), error_for_status(503), "ok"])
    sleeps = []
    ask("hi", adapter, sleep=sleeps.append)
    assert 0 < sleeps[0] < sleeps[1]