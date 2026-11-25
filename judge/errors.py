class JudgeError(Exception):
    """Base class for every failure when asking a judge model for a verdict."""

    retryable = False

    def __init__(self, message, status_code=None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class JudgeAuthError(JudgeError):
    """Missing, wrong or unauthorized API key (401/403)."""


class JudgeModelNotFoundError(JudgeError):
    """The model name does not exist (404), for example a retired model."""


class JudgeRequestError(JudgeError):
    """We sent something the provider rejected (400 and other 4xx)."""


class JudgeRateLimitError(JudgeError):
    """Too many requests (429). Worth retrying after a pause."""

    retryable = True


class JudgeServerError(JudgeError):
    """The provider is struggling (5xx). Worth retrying."""

    retryable = True


class JudgeNetworkError(JudgeError):
    """Could not reach the provider at all (timeout, dropped connection, DNS)."""

    retryable = True


class JudgeResponseError(JudgeError):
    """The provider answered, but with nothing usable (blocked prompt, empty text, odd shape)."""


def error_for_status(status_code, retry_after=None):
    if status_code in (401, 403):
        cls = JudgeAuthError
        text = "API key was rejected. Check JUDGE_API_KEY."
    elif status_code == 404:
        cls = JudgeModelNotFoundError
        text = "Model not found. It may be retired or misspelled. Check JUDGE_MODEL."
    elif status_code == 429:
        cls = JudgeRateLimitError
        text = "Rate limited by the provider."
    elif status_code >= 500:
        cls = JudgeServerError
        text = "The provider had a server error."
    else:
        cls = JudgeRequestError
        text = "The provider rejected the request."
    return cls(f"{text} (HTTP {status_code})", status_code=status_code, retry_after=retry_after)