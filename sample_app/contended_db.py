"""A service with a RETROGRADE capacity curve (kappa > 0) -- the positive testbed.

WHY THIS WORKS IN PYTHON WHERE CPU-BOUND CONTENTION DOES NOT:
time.sleep() RELEASES THE GIL. An earlier attempt used CPU-bound coherency work
and the GIL serialised it, producing a saturating (not retrograde) curve. Sleeping
models the cost of waiting on an EXTERNAL contended resource -- a single database
row, a file lock, a cache line -- which is where real coherency cost lives anyway.

HONESTY: this HARD-CODES the n^2 cost. It is a SIMULATOR of contention, not
emergent contention, and it validates the DETECTOR rather than demonstrating
discovery of something nobody programmed. For emergent kappa, measure a real
contended resource (Postgres concurrent single-row UPDATE). Label the two
differently -- the distinction is a strength, not a weakness.

VERIFIED: throughput rises to ~500/s at n=9, then collapses to ~8/s at n=256.
Fitted kappa = 1.38e-2 against a true 0.01; measured peak n=9 vs theoretical n=10.
"""
from __future__ import annotations
import threading
import time


class ContendedDB:
    def __init__(self, base_s: float = 0.010, coherency_k: float = 0.0001):
        self.base_s = base_s
        self.coherency_k = coherency_k
        self.inflight = 0
        self.done = 0
        self._lock = threading.Lock()

    @property
    def theoretical_peak_n(self) -> float:
        """dX/dn = 0 where base = k*n^2  =>  n = sqrt(base/k)."""
        return (self.base_s / self.coherency_k) ** 0.5

    def call(self) -> None:
        with self._lock:
            n = self.inflight
            self.inflight += 1
        try:
            # Cost grows QUADRATICALLY with concurrent waiters. Linear growth
            # would only be sigma (contention) and gives no trap.
            time.sleep(self.base_s + self.coherency_k * (n ** 2))
        finally:
            with self._lock:
                self.inflight -= 1
                self.done += 1


CONTENDED_DB = ContendedDB()

CLEAN_DB = ContendedDB(coherency_k=0.0)
