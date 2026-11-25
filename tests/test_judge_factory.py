import pytest

from judge.adapters.anthropic import AnthropicAdapter
from judge.adapters.gemini import GeminiAdapter
from judge.adapters.openai_compat import OpenAICompatAdapter
from judge.errors import JudgeConfigError, JudgeError
from judge.factory import build_adapter


def test_gemini_from_judge_settings():
    adapter = build_adapter(
        {"JUDGE_PROVIDER": "gemini", "JUDGE_MODEL": "m1", "JUDGE_API_KEY": "k1"}
    )
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.model == "m1"
    assert adapter.api_key == "k1"


def test_gemini_needs_a_key():
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({"JUDGE_PROVIDER": "gemini", "JUDGE_MODEL": "m1"})
    assert "JUDGE_API_KEY" in str(info.value)


def test_old_gemini_setup_still_works():
    adapter = build_adapter({"GEMINI_API_KEY": "old-key", "GEMINI_MODEL": "old-model"})
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.model == "old-model"
    assert adapter.api_key == "old-key"


def test_old_gemini_setup_gets_a_default_model():
    adapter = build_adapter({"GEMINI_API_KEY": "old-key"})
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.model


def test_judge_settings_win_over_old_gemini_settings():
    adapter = build_adapter(
        {
            "JUDGE_PROVIDER": "gemini",
            "JUDGE_MODEL": "new-model",
            "JUDGE_API_KEY": "new-key",
            "GEMINI_API_KEY": "old-key",
            "GEMINI_MODEL": "old-model",
        }
    )
    assert adapter.model == "new-model"
    assert adapter.api_key == "new-key"


def test_openai_with_custom_base_url_needs_no_key():
    adapter = build_adapter(
        {
            "JUDGE_PROVIDER": "openai",
            "JUDGE_MODEL": "llama3",
            "JUDGE_BASE_URL": "http://localhost:11434/v1",
        }
    )
    assert isinstance(adapter, OpenAICompatAdapter)
    assert adapter.api_key is None
    assert adapter.base_url == "http://localhost:11434/v1"


def test_hosted_openai_needs_a_key():
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({"JUDGE_PROVIDER": "openai", "JUDGE_MODEL": "m"})
    assert "JUDGE_API_KEY" in str(info.value)


def test_openai_with_a_key_uses_the_default_base_url():
    adapter = build_adapter(
        {"JUDGE_PROVIDER": "openai", "JUDGE_MODEL": "m", "JUDGE_API_KEY": "k"}
    )
    assert isinstance(adapter, OpenAICompatAdapter)
    assert adapter.base_url == "https://api.openai.com/v1"


def test_anthropic_from_judge_settings():
    adapter = build_adapter(
        {"JUDGE_PROVIDER": "anthropic", "JUDGE_MODEL": "m", "JUDGE_API_KEY": "k"}
    )
    assert isinstance(adapter, AnthropicAdapter)
    assert adapter.model == "m"
    assert adapter.api_key == "k"


def test_anthropic_needs_a_key():
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({"JUDGE_PROVIDER": "anthropic", "JUDGE_MODEL": "m"})
    assert "JUDGE_API_KEY" in str(info.value)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_model_is_required_when_there_is_no_default(provider):
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({"JUDGE_PROVIDER": provider, "JUDGE_API_KEY": "k"})
    assert "JUDGE_MODEL" in str(info.value)


def test_empty_values_count_as_missing():
    with pytest.raises(JudgeConfigError):
        build_adapter(
            {"JUDGE_PROVIDER": "anthropic", "JUDGE_MODEL": "", "JUDGE_API_KEY": "k"}
        )


def test_provider_name_ignores_case_and_spaces():
    adapter = build_adapter(
        {"JUDGE_PROVIDER": " Anthropic ", "JUDGE_MODEL": "m", "JUDGE_API_KEY": "k"}
    )
    assert isinstance(adapter, AnthropicAdapter)


def test_unknown_provider_lists_the_valid_ones():
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({"JUDGE_PROVIDER": "banana", "JUDGE_API_KEY": "super-secret"})
    message = str(info.value)
    for name in ("gemini", "openai", "anthropic"):
        assert name in message
    assert "super-secret" not in message


def test_nothing_configured_says_what_to_set():
    with pytest.raises(JudgeConfigError) as info:
        build_adapter({})
    assert "JUDGE_PROVIDER" in str(info.value)


def test_explicit_api_key_beats_the_environment():
    adapter = build_adapter(
        {"JUDGE_PROVIDER": "anthropic", "JUDGE_MODEL": "m", "JUDGE_API_KEY": "env-key"},
        api_key="request-key",
    )
    assert adapter.api_key == "request-key"


def test_config_error_is_a_judge_error_and_not_retryable():
    err = JudgeConfigError("bad setup")
    assert isinstance(err, JudgeError)
    assert err.retryable is False