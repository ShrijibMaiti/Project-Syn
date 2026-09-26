"""A service with GENUINE coherency cost -- the positive case for kappa>0.

Every operation must synchronise with all other in-flight operations (a shared
version counter each worker scans). Cost per op grows with concurrency, so total
coherency cost grows as N^2 -- exactly the USL kappa term. This is what a lock
convoy, a contended cache line, or single-row write contention looks like.
"""
from __future__ import annotations
import threading
import time


class ContendedService:
    def __init__(self, base_work: int = 400, coherency_work: int = 60):
        self.base_work = base_work
        self.coherency_work = coherency_work
        self.inflight = 0
        self.done = 0
        self._lock = threading.Lock()
        self._versions = [0] * 256

    def handle(self) -> None:
        with self._lock:
            self.inflight += 1
            n = self.inflight
        try:
            acc = 0
            for i in range(self.base_work):          # fixed per-request work
                acc += i * i
            for _ in range(n):                        # COHERENCY: scales with concurrency
                for j in range(self.coherency_work):
                    acc += self._versions[j % 256]
            with self._lock:
                self._versions[self.done % 256] += 1  # invalidate for everyone
        finally:
            with self._lock:
                self.inflight -= 1
                self.done += 1


SERVICE = ContendedService()
