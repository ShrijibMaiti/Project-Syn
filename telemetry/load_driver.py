"""Drive load across orders of magnitude. Two jobs:
  1. hysteresis sweep (up then down) -> exposes metastability
  2. multi-decade sweep -> gives symbolic regression the scale spread it requires
"""
from __future__ import annotations
import concurrent.futures as cf
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import requests

from telemetry.collector import Collector


@dataclass
class LoadPhase:
    load: float
    duration: float
    rows: List[Dict[str, float]]


class LoadDriver:
    def __init__(self, base_url: str = "http://127.0.0.1:8001",
                 collector: Optional[Collector] = None, workers: int = 32):
        self.base_url = base_url.rstrip("/")
        self.collector = collector or Collector(base_url)
        self.workers = workers

    # -- request generation ------------------------------------------------
    def _fire(self, path: str = "/work") -> None:
        try:
            requests.get(f"{self.base_url}{path}", timeout=5.0)
        except requests.RequestException:
            pass

    def _drive(self, rps: float, duration: float, path: str = "/work") -> None:
        total = max(1, int(rps * duration))
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            for _ in range(total):
                ex.submit(self._fire, path)
                time.sleep(1.0 / max(rps, 1e-6))

    # -- sweeps ------------------------------------------------------------
    def hold(self, load: float, duration: float = 10.0, hz: float = 5.0) -> LoadPhase:
        with cf.ThreadPoolExecutor(max_workers=2) as ex:
            fut = ex.submit(self._drive, load, duration)
            rows = self.collector.collect(duration, hz, load)
            fut.result()
        return LoadPhase(load, duration, rows)

    def hysteresis_sweep(self, loads: List[float], duration: float = 10.0
                         ) -> Dict[str, List[LoadPhase]]:
        """Ramp up then down. If the down-leg settles differently at the same load,
        the system has memory of collapse => a metastable trap."""
        up = [self.hold(L, duration) for L in loads]
        down = [self.hold(L, duration) for L in reversed(loads)]
        return {"up": up, "down": down}

    def multiscale_sweep(self, n_values: Optional[List[int]] = None,
                         path: str = "/work") -> List[Dict[str, float]]:
        """Sample (n, resource) at log-spaced n. Spread beats volume: 10 points over
        5 decades beats 10,000 points all at n~1000."""
        n_values = n_values or [int(x) for x in np.logspace(1, 5, 9)]
        out = []
        for n in n_values:
            t0 = time.perf_counter()
            try:
                r = requests.get(f"{self.base_url}{path}", params={"n": n}, timeout=120)
                r.raise_for_status()
                payload = r.json()
            except requests.RequestException as exc:
                out.append({"n": n, "error": str(exc)}); continue
            out.append({"n": float(n),
                        "elapsed_s": time.perf_counter() - t0,
                        "db_calls": float(payload.get("db_calls", 0)),
                        "ops": float(payload.get("ops", 0))})
        return [r for r in out if "error" not in r]