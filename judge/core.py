import random
import time
from dataclasses import dataclass

from judge.errors import JudgeError

BASE_DELAY = 0.5
MAX_DELAY = 30.0
DEFAULT_DEADLINE = 60.0


@dataclass(frozen=True)
class JudgeResult:
    text: str
    provider: str
    model: str
    attempts: int


def _backoff_delay(attempt):
    # attempt 1 -> ~0.5s, 2 -> ~1s, 3 -> ~2s, plus a little random jitter
    return min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY) + random.uniform(0, 0.25)


def ask(
    prompt,
    adapter,
    max_attempts=3,
    sleep=time.sleep,
    deadline=DEFAULT_DEADLINE,
    clock=time.monotonic,
):
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if deadline <= 0:
        raise ValueError("deadline must be positive")

    started = clock()

    for attempt in range(1, max_attempts + 1):
        try:
            text = adapter.complete(prompt)
        except JudgeError as err:
            if not err.retryable or attempt == max_attempts:
                raise
            delay = err.retry_after if err.retry_after is not None else _backoff_delay(attempt)
            delay = min(delay, MAX_DELAY)
            # Do not start another attempt if waiting for it would blow the budget.
            if clock() - started + delay >= deadline:
                raise
            sleep(delay)
            continue
        return JudgeResult(
            text=text,
            provider=adapter.provider,
            model=adapter.model,
            attempts=attempt,
        )