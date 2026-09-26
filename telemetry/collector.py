"""Instrument sample_app -> order-state stream. This is where SYN's dataset is born:
telemetry comes from a REAL running app, never from the Twin (that would be circular)."""
from __future__ import annotations
import time
from typing import Dict, Iterator, List, Optional

import requests

from shared.order_params import OrderParams


class Collector:
    def __init__(self, base_url: str = "http://127.0.0.1:8001",
                 params: Optional[OrderParams] = None, timeout: float = 2.0):
        self.base_url = base_url.rstrip("/")
        self.params = params or OrderParams.default()
        self.timeout = timeout

    def sample(self, load: float = 0.0) -> Dict[str, float]:
        r = requests.get(f"{self.base_url}/metrics", timeout=self.timeout)
        r.raise_for_status()
        row = r.json()
        row["t"] = time.time()
        row["load"] = load
        return row

    def stream(self, seconds: float, hz: float = 5.0, load: float = 0.0
               ) -> Iterator[Dict[str, float]]:
        n = int(seconds * hz)
        dt = 1.0 / hz
        t0 = time.time()
        for _ in range(n):
            try:
                row = self.sample(load)
                row["t"] = time.time() - t0
                yield row
            except requests.RequestException as exc:
                yield {"t": time.time() - t0, "load": load, "error": str(exc),
                       "queue_depth": float("nan")}
            time.sleep(dt)

    def collect(self, seconds: float, hz: float = 5.0, load: float = 0.0
                ) -> List[Dict[str, float]]:
        return [r for r in self.stream(seconds, hz, load) if "error" not in r]