"""Parallel probe execution.

The two lenses share nothing but the target process, and stability is MINUTES long
while complexity is seconds. Running them concurrently is why this layer exists.

CAVEAT: both probes load the machine. Against the SAME target, running them
concurrently distorts both -- stability's latency curve picks up complexity's CPU
load. Use serialize=True when targets share a resource."""
from __future__ import annotations
import concurrent.futures as cf
import time
from typing import Callable, Dict, List, Tuple

from shared.types import ProbeKind, ProbeResult, RiskLevel

Probe = Callable[[], ProbeResult]


def run_probes(probes: Dict[str, Probe], timeout: float = 1800.0,
               serialize: bool = False) -> Tuple[List[ProbeResult], Dict[str, float]]:
    results: List[ProbeResult] = []
    timings: Dict[str, float] = {}

    if serialize:
        for name, fn in probes.items():
            t0 = time.time()
            try:
                results.append(fn())
            except Exception as exc:
                results.append(_failed(name, exc))
            timings[name] = time.time() - t0
        return results, timings

    t_all = time.time()
    with cf.ThreadPoolExecutor(max_workers=max(len(probes), 1)) as ex:
        futures = {ex.submit(_timed, name, fn): name for name, fn in probes.items()}
        try:
            for fut in cf.as_completed(futures, timeout=timeout):
                name = futures[fut]
                try:
                    res, dt = fut.result()
                    results.append(res)
                    timings[name] = dt
                except Exception as exc:
                    results.append(_failed(name, exc))
                    timings[name] = -1.0
        except cf.TimeoutError:
            for fut, name in futures.items():
                if not fut.done():
                    results.append(_failed(name, TimeoutError(f"exceeded {timeout}s")))
    timings["_wall"] = time.time() - t_all
    return results, timings


def _timed(name: str, fn: Probe):
    t0 = time.time()
    return fn(), time.time() - t0


def _failed(name: str, exc: Exception) -> ProbeResult:
    kind = ProbeKind.STABILITY if "stab" in name.lower() else ProbeKind.COMPLEXITY
    return ProbeResult(kind, RiskLevel.UNKNOWN, f"probe {name} failed: {exc}",
                       evidence={"target": name, "note": f"failed: {exc}"},
                       error=str(exc))
