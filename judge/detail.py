import json
import re

MAX_LENGTH = 200
REDACTED = "[redacted]"

# Shapes of common API keys, removed even when we were not told the key.
_KEY_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"\bsk-[0-9A-Za-z_\-]{20,}"),
    re.compile(r"Bearer\s+[0-9A-Za-z._\-]{8,}", re.IGNORECASE),
)


def _message_from(text):
    try:
        data = json.loads(text)
    except (ValueError, RecursionError):
        return text
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(error, str):
            return error
        if isinstance(data.get("message"), str):
            return data["message"]
    return text


def extract_detail(text, secrets=()):
    """A short, single-line, key-free explanation taken from a provider's error body."""
    if not text or not text.strip():
        return None
    message = " ".join(_message_from(text).split())
    for secret in secrets:
        if secret:
            message = message.replace(secret, REDACTED)
    for pattern in _KEY_PATTERNS:
        message = pattern.sub(REDACTED, message)
    if not message:
        return None
    if len(message) > MAX_LENGTH:
        message = message[: MAX_LENGTH - 3] + "..."
    return message