"""Simple client-side rate limiting and retry with exponential backoff."""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

RETRYABLE_HINTS = (
    "ratelimit",
    "rate_limit",
    "429",
    "overloaded",
    "529",
    "timeout",
    "temporarily",
    "apiconnection",
    "internalserver",
    "503",
    "502",
)


class RateLimiter:
    """Enforce a minimum interval between calls (requests per minute). ``rpm <= 0`` disables."""

    def __init__(
        self,
        requests_per_minute: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._clock = clock
        self._sleep = sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> float:
        """Block until the next call is allowed. Returns seconds slept."""
        if not self.interval:
            return 0.0
        with self._lock:
            now = self._clock()
            delay = max(0.0, self._next - now)
            if delay:
                self._sleep(delay)
            self._next = max(now, self._next) + self.interval
            return delay


def is_retryable(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(h in text for h in RETRYABLE_HINTS)


def with_retries(
    fn: Callable[[], T],
    retries: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn``; on retryable errors back off ``base_delay * 2**n`` (+ jitter) and retry."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below when not retryable
            if attempt >= retries or not is_retryable(exc):
                raise
            sleep(base_delay * (2**attempt) + random.uniform(0, 0.5))
            attempt += 1
