import json

import pytest

from judge.detail import extract_detail
from judge.errors import error_for_status


def body(obj):
    return json.dumps(obj)


def test_reads_error_message_from_a_json_error_object():
    text = body({"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}})
    assert extract_detail(text) == "The model is overloaded."


def test_reads_an_error_that_is_a_plain_string():
    assert extract_detail(body({"error": "rate limit hit"})) == "rate limit hit"


def test_reads_a_top_level_message():
    assert extract_detail(body({"message": "bad gateway"})) == "bad gateway"


def test_falls_back_to_the_raw_text_when_it_is_not_json():
    assert extract_detail("Service Unavailable") == "Service Unavailable"


def test_empty_or_missing_body_gives_none():
    assert extract_detail("") is None
    assert extract_detail("   ") is None
    assert extract_detail(None) is None


def test_whitespace_is_collapsed():
    assert extract_detail("first\n\n   second\tthird") == "first second third"


def test_long_text_is_cut_to_200_characters():
    result = extract_detail("x" * 5000)
    assert len(result) <= 200
    assert result.endswith("...")


def test_the_exact_key_is_removed():
    text = body({"error": {"message": "Key my-secret-key-123 is invalid"}})
    result = extract_detail(text, secrets=("my-secret-key-123",))
    assert "my-secret-key-123" not in result
    assert "[redacted]" in result


def test_empty_secrets_are_ignored():
    assert extract_detail("plain text", secrets=(None, "")) == "plain text"


@pytest.mark.parametrize(
    "secret",
    [
        "AIza" + "A" * 35,
        "sk-" + "a" * 30,
        "sk-ant-api03-" + "b" * 30,
        "Bearer abcdefghijklmnop",
    ],
)
def test_key_shaped_text_is_removed_even_without_being_told(secret):
    result = extract_detail(f"bad credential {secret} rejected")
    assert secret not in result
    assert "[redacted]" in result


def test_error_message_includes_the_providers_explanation():
    err = error_for_status(503, detail="The model is overloaded.")
    assert "The model is overloaded." in str(err)
    assert "503" in str(err)


def test_error_message_is_unchanged_without_detail():
    assert str(error_for_status(503)) == "The provider had a server error. (HTTP 503)"
    assert str(error_for_status(503, detail=None)) == str(error_for_status(503))