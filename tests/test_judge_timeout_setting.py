import pytest

from judge.errors import JudgeConfigError
from judge.factory import build_adapter

PROVIDERS = ["gemini", "openai", "anthropic"]


def env_for(provider, **extra):
    env = {"JUDGE_PROVIDER": provider, "JUDGE_MODEL": "m", "JUDGE_API_KEY": "k"}
    env.update(extra)
    return env


@pytest.mark.parametrize("provider", PROVIDERS)
def test_timeout_setting_reaches_every_adapter(provider):
    adapter = build_adapter(env_for(provider, JUDGE_TIMEOUT="90"))
    assert adapter.timeout == 90.0


@pytest.mark.parametrize("provider", PROVIDERS)
def test_timeout_unset_keeps_the_adapter_default(provider):
    adapter = build_adapter(env_for(provider))
    assert adapter.timeout == 30.0


def test_blank_timeout_counts_as_unset():
    adapter = build_adapter(env_for("gemini", JUDGE_TIMEOUT="  "))
    assert adapter.timeout == 30.0


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "nan", "inf"])
def test_bad_timeout_is_a_config_error_naming_the_setting(bad):
    with pytest.raises(JudgeConfigError) as info:
        build_adapter(env_for("gemini", JUDGE_TIMEOUT=bad))
    assert "JUDGE_TIMEOUT" in str(info.value)