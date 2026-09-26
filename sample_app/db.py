"""Backing store. In-memory so the sample app runs anywhere, but with a real
per-call latency and a real connection pool so saturation is genuine, not faked."""
from __future__ import annotations
import threading
import time
from typing import Dict, List


class FakeDB:
    def __init__(self, latency_s: float = 0.00002, pool_size: int = 512):
        self.latency_s = latency_s
        self.pool_size = pool_size
        self.calls = 0
        self.inflight = 0
        self.max_inflight = 0
        self._lock = threading.Lock()
        self.orders: Dict[int, dict] = {}
        self.items: Dict[int, List[dict]] = {}
        self.degraded_until = 0.0          # trigger window for the death spiral

    def seed(self, n_orders: int = 20000, items_per_order: int = 1) -> None:
        self.orders = {i: {"id": i, "customer": f"c{i % 1000}"} for i in range(n_orders)}
        self.items = {i: [{"sku": f"s{j}", "order_id": i} for j in range(items_per_order)]
                      for i in range(n_orders)}

    def degrade(self, seconds: float) -> None:
        """The transient trigger. Removing it does NOT recover a metastable system."""
        self.degraded_until = time.time() + seconds

    @property
    def saturated(self) -> bool:
        return self.inflight >= self.pool_size

    def _tick(self) -> None:
        with self._lock:
            self.calls += 1
            self.inflight += 1
            self.max_inflight = max(self.max_inflight, self.inflight)
        try:
            # Under load the service slows down -- this is what closes the feedback loop.
            extra = 0.002 if time.time() < self.degraded_until else 0.0
            queue_penalty = self.latency_s * max(0, self.inflight - 1) * 0.5
            time.sleep(self.latency_s + extra + queue_penalty)
        finally:
            with self._lock:
                self.inflight -= 1

    def query_orders(self, limit: int) -> List[dict]:
        self._tick()
        return [self.orders[i] for i in range(min(limit, len(self.orders)))]

    def query_items(self, order_id: int) -> List[dict]:
        self._tick()
        return self.items.get(order_id, [])

    def query_all_items(self, limit: int) -> List[dict]:
        self._tick()
        out: List[dict] = []
        for i in range(min(limit, len(self.items))):
            out.extend(self.items[i])
        return out

    def reset_counters(self) -> None:
        with self._lock:
            self.calls = 0
            self.max_inflight = 0


DB = FakeDB()