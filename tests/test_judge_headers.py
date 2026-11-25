import pytest

from judge.headers import parse_retry_after


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2", 2.0),
        ("1.5", 1.5),
        ("0", 0.0),
        (None, None),
        ("abc", None),
        ("", None),
        ("-1", None),
        ("nan", None),
        ("inf", None),
        ("Wed, 21 Oct 2026 07:28:00 GMT", None),
    ],
)
def test_parse_retry_after(raw, expected):
    assert parse_retry_after(raw) == expected