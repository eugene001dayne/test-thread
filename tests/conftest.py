import pytest

JUDGE_SETTINGS = (
    "JUDGE_PROVIDER",
    "JUDGE_MODEL",
    "JUDGE_API_KEY",
    "JUDGE_BASE_URL",
    "JUDGE_TIMEOUT",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
)


@pytest.fixture(autouse=True)
def no_real_judge_settings(monkeypatch):
    """main.py loads .env at import; tests must never inherit a real key from it."""
    for name in JUDGE_SETTINGS:
        monkeypatch.delenv(name, raising=False)