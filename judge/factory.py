import math

from judge.adapters.anthropic import AnthropicAdapter
from judge.adapters.gemini import GeminiAdapter
from judge.adapters.openai_compat import OpenAICompatAdapter
from judge.errors import JudgeConfigError

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
PROVIDERS = ("gemini", "openai", "anthropic")


def _get(env, name):
    value = env.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _need_model(provider, model):
    if not model:
        raise JudgeConfigError(
            f"No model set for {provider}. Set JUDGE_MODEL to the model you want to use."
        )
    return model


def _need_key(provider, key, hint=""):
    if not key:
        raise JudgeConfigError(f"No API key set for {provider}. Set JUDGE_API_KEY.{hint}")
    return key


def _timeout(env):
    raw = _get(env, "JUDGE_TIMEOUT")
    if raw is None:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        seconds = None
    if seconds is None or not math.isfinite(seconds) or seconds <= 0:
        raise JudgeConfigError(
            "JUDGE_TIMEOUT must be a positive number of seconds, for example 60."
        )
    return seconds


def build_adapter(env, api_key=None):
    provider = _get(env, "JUDGE_PROVIDER")
    key = (api_key or "").strip() or _get(env, "JUDGE_API_KEY")

    if provider is None:
        if _get(env, "GEMINI_API_KEY") is None:
            raise JudgeConfigError(
                "No judge configured. Set JUDGE_PROVIDER to one of: "
                + ", ".join(PROVIDERS)
                + ", plus JUDGE_MODEL and JUDGE_API_KEY."
            )
        provider = "gemini"
    provider = provider.lower()

    timeout = _timeout(env)
    extra = {} if timeout is None else {"timeout": timeout}

    if provider == "gemini":
        model = _get(env, "JUDGE_MODEL") or _get(env, "GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        key = _need_key(provider, key or _get(env, "GEMINI_API_KEY"))
        return GeminiAdapter(model=model, api_key=key, **extra)

    if provider == "openai":
        model = _need_model(provider, _get(env, "JUDGE_MODEL"))
        base_url = _get(env, "JUDGE_BASE_URL")
        if base_url is None:
            key = _need_key(
                provider, key, hint=" (Or set JUDGE_BASE_URL for a local server that needs no key.)"
            )
        options = {"model": model, "api_key": key, **extra}
        if base_url:
            options["base_url"] = base_url
        return OpenAICompatAdapter(**options)

    if provider == "anthropic":
        model = _need_model(provider, _get(env, "JUDGE_MODEL"))
        key = _need_key(provider, key)
        return AnthropicAdapter(model=model, api_key=key, **extra)

    raise JudgeConfigError(
        f"Unknown JUDGE_PROVIDER '{provider}'. Use one of: " + ", ".join(PROVIDERS) + "."
    )