import pytest

from judge.core import ask
from judge.errors import JudgeServerError, error_for_status


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FailingAdapter:
    provider = "fake"
    model = "fake-model"

    def __init__(self, clock, seconds_per_call, error):
        self.clock = clock
        self.seconds_per_call = seconds_per_call
        self.error = error
        self.calls = 0

    def complete(self, prompt):
        self.calls += 1
        self.clock.now += self.seconds_per_call
        raise self.error


class WorkingAdapter:
    provider = "fake"
    model = "fake-model"

    def complete(self, prompt):
        return "ok"


def test_stops_retrying_when_the_next_wait_would_cross_the_deadline():
    clock = FakeClock()
    adapter = FailingAdapter(clock, 20, error_for_status(503))
    with pytest.raises(JudgeServerError):
        ask("hi", adapter, max_attempts=5, deadline=30, sleep=clock.sleep, clock=clock)
    assert adapter.calls == 2


def test_gives_up_at_once_if_retry_after_exceeds_the_budget():
    clock = FakeClock()
    adapter = FailingAdapter(clock, 0, error_for_status(429, retry_after=25))
    with pytest.raises(Exception):
        ask("hi", adapter, max_attempts=3, deadline=10, sleep=clock.sleep, clock=clock)
    assert adapter.calls == 1
    assert clock.now == 0


def test_success_is_unaffected_by_a_tight_deadline():
    clock = FakeClock()
    result = ask("hi", WorkingAdapter(), deadline=1, sleep=clock.sleep, clock=clock)
    assert result.text == "ok"


@pytest.mark.parametrize("bad", [0, -1])
def test_deadline_must_be_positive(bad):
    with pytest.raises(ValueError):
        ask("hi", WorkingAdapter(), deadline=bad)