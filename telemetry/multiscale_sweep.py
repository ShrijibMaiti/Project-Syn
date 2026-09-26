"""Turn raw sweep rows into the (n, resource) arrays PySR consumes, and report
the decade spread the guard will check."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np


@dataclass
class MultiScaleData:
    n: np.ndarray
    resource: np.ndarray
    metric: str

    @property
    def decades(self) -> float:
        lo, hi = float(np.min(self.n)), float(np.max(self.n))
        return float(np.log10(hi / lo)) if lo > 0 and hi > lo else 0.0

    def __len__(self) -> int:
        return int(self.n.size)


def build(rows: Sequence[Dict[str, float]], metric: str = "elapsed_s") -> MultiScaleData:
    rows = [r for r in rows if r.get("n", 0) > 0 and metric in r]
    if not rows:
        return MultiScaleData(np.empty(0), np.empty(0), metric)
    rows = sorted(rows, key=lambda r: r["n"])
    return MultiScaleData(np.array([float(r["n"]) for r in rows]),
                          np.array([float(r[metric]) for r in rows]), metric)


def log_spaced(lo: int = 10, hi: int = 100_000, points: int = 9) -> List[int]:
    return sorted({int(x) for x in np.logspace(np.log10(lo), np.log10(hi), points)})

def timed_sweep(fn, n_values, repeats: int = 5, warmup: int = 2, counter=None):
    """Median-of-k timing with warmup.

    Single-shot timing is not reproducible: run-to-run noise is large enough to
    flip the recovered complexity class (observed O(n^2) -> O(n^3) on identical
    code). The median over repeats suppresses scheduler and cache artifacts; the
    warmup pass absorbs first-call import/JIT/page-fault costs. `spread` is
    reported so an unreliable measurement is visible rather than silent.
    """
    import time
    from statistics import median

    rows = []
    for n in n_values:
        for _ in range(warmup):
            fn(n)
        samples = []
        for _ in range(repeats):
            if counter:
                counter()
            t0 = time.perf_counter()
            fn(n)
            samples.append(time.perf_counter() - t0)
        rows.append({"n": float(n), "elapsed_s": float(median(samples)),
                     "t_min": float(min(samples)), "t_max": float(max(samples)),
                     "spread": float(max(samples) / max(min(samples), 1e-12))})
    return rows



def robust_class(fn, n_values, trials: int = 5, repeats: int = 5, warmup: int = 2,
                 metric: str = "elapsed_s"):
    """Classify from the MEDIAN EXPONENT ACROSS TRIALS, with an interval.

    Single-fit class labels are unstable even when the underlying measurement is
    good: the exponent spread (~0.3) straddles discrete class boundaries, so a
    boundary-adjacent fit flips between labels run to run. Reporting the exponent
    with an interval keeps the information the label throws away.
    """
    import numpy as np
    from complexity.symbolic_regressor import _class_from_exponent

    exps = []
    for _ in range(trials):
        rows = timed_sweep(fn, n_values, repeats=repeats, warmup=warmup)
        d = build(rows, metric)
        e = _loglog_exponent_safe(d)
        if e is not None:
            exps.append(e)
    if not exps:
        return {"exponent": None, "class": "unknown", "superlinear": None,
                "note": "no usable timing"}
    med = float(np.median(exps))
    lo, hi = float(np.percentile(exps, 10)), float(np.percentile(exps, 90))
    return {"exponent": med, "interval": (lo, hi), "trials": len(exps),
            "class": _class_from_exponent(med) or f"~n^{med:.2f}",
            "superlinear": med > 1.2,
            "measurable_growth": med > 0.5,
            "note": ("constant overhead dominates the tested range -- widen the sweep"
                     if med <= 0.5 else "ok")}


def _loglog_exponent_safe(d):
    from complexity.symbolic_regressor import _loglog_exponent
    return _loglog_exponent(d)
