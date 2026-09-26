"""PLANTED FAULT 1 -- the death spiral.

Unbounded retry-on-timeout with NO jitter and NO circuit breaker. Above a trigger
load the retries themselves sustain the overload: the system stays collapsed after
the trigger is removed. This is the bad stable basin SYN is built to see.

The dynamics match the verified Twin: an S-shaped retry gain that is silent when
healthy and floods under stress, against a saturating drain.
"""
from __future__ import annotations
import threading
import time
from typing import Any, Callable

from sample_app.db import DB


class RetryStats:
    def __init__(self) -> None:
        self.attempts = 0
        self.retries = 0
        self.failures = 0
        self.successes = 0
        self._lock = threading.Lock()

    def snapshot(self) -> dict:
        with self._lock:
            total = max(self.attempts, 1)
            return {"retry_rate": self.retries / total,
                    "error_rate": self.failures / total,
                    "attempts": self.attempts, "retries": self.retries}

    def reset(self) -> None:
        with self._lock:
            self.attempts = self.retries = self.failures = self.successes = 0


STATS = RetryStats()

MAX_RETRIES = 6          # FAULT: high ceiling, no backoff, no jitter
TIMEOUT_S = 0.05         # FAULT: aggressive timeout -> fires early under mild load


def call_with_retries(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """FAULT: retries immediately, with no jitter and no circuit breaker.
    Every retry adds load to the very resource that is already struggling."""
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        with STATS._lock:
            STATS.attempts += 1
            if attempt > 0:
                STATS.retries += 1
        start = time.perf_counter()
        try:
            if DB.saturated:
                raise TimeoutError("pool exhausted")
            result = fn(*args, **kwargs)
            if time.perf_counter() - start > TIMEOUT_S:
                raise TimeoutError("slow call")
            with STATS._lock:
                STATS.successes += 1
            return result
        except (TimeoutError, RuntimeError) as exc:
            last_exc = exc
            continue                      # FAULT: no sleep, no backoff -- retry storm
    with STATS._lock:
        STATS.failures += 1
    raise last_exc or RuntimeError("exhausted retries")


def healthy_call(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """The FIXED version, for the false-positive test: capped retries with backoff
    and a circuit breaker. Raises the basin threshold out of the operating range."""
    for attempt in range(2):
        try:
            if DB.saturated:
                raise TimeoutError("pool exhausted")
            return fn(*args, **kwargs)
        except TimeoutError:
            time.sleep(0.01 * (2 ** attempt))     # backoff
    raise TimeoutError("circuit open")