import pytest

from judge.errors import (
    JudgeError,
    JudgeAuthError,
    JudgeModelNotFoundError,
    JudgeRateLimitError,
    JudgeServerError,
    JudgeRequestError,
    error_for_status,
)

CASES = [
    (401, JudgeAuthError, False),
    (403, JudgeAuthError, False),
    (404, JudgeModelNotFoundError, False),
    (400, JudgeRequestError, False),
    (429, JudgeRateLimitError, True),
    (500, JudgeServerError, True),
    (502, JudgeServerError, True),
    (503, JudgeServerError, True),
    (504, JudgeServerError, True),
]


@pytest.mark.parametrize("status, expected_class, retryable", CASES)
def test_status_maps_to_the_right_error(status, expected_class, retryable):
    err = error_for_status(status)
    assert type(err) is expected_class
    assert err.retryable is retryable
    assert err.status_code == status


def test_every_error_is_a_judge_error():
    for status, _, _ in CASES:
        assert isinstance(error_for_status(status), JudgeError)


def test_retry_after_is_kept_when_given():
    err = error_for_status(429, retry_after=2.5)
    assert err.retry_after == 2.5


def test_message_names_the_status():
    assert "404" in str(error_for_status(404))