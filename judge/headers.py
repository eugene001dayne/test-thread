import math


def parse_retry_after(value):
    """Return a safe number of seconds to wait, or None if the header is missing or unusable."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    return seconds