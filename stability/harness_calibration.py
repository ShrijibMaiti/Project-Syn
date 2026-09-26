"""Measure the MEASUREMENT APPARATUS's own coherency cost.

Above ~100 OS threads the scheduler contributes superlinear latency of its own.
SYN correctly detects this -- but it belongs to the harness, not the target.
Measured on a dev machine: a trivial no-op target produced kappa=5.4e-05 at
p=0.0005, latency rising 71% between n=96 and n=128.

Any target whose kappa does not clearly exceed this floor is indistinguishable
from scheduler noise, and must not be reported as a trap."""
from __future__ import annotations
import time

from stability.capacity_curve import measure_latency_curve, fit_capacity

# A target with NO coherency cost by construction: a fixed sleep, no shared state.
def _noop(sleep_s: float = 0.0008):
    def call():
        time.sleep(sleep_s)
    return call


def calibrate(levels=None, samples_per_level: int = 40, repeats: int = 3,
              sleep_s: float = 0.0008):
    """Returns (kappa_floor, fit). Run this ONCE per machine, per level set."""
    levels = levels or [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 192, 224, 256]
    rows = measure_latency_curve(_noop(sleep_s), levels,
                                 samples_per_level=samples_per_level, repeats=repeats)
    fit = fit_capacity(rows)
    # If the harness itself shows evidence, that kappa is the noise floor.
    floor = fit.kappa if fit.evidence else 0.0
    return floor, fit, rows


def exceeds_floor(target_kappa: float, floor: float, margin: float = 10.0) -> bool:
    """Target kappa must exceed the harness floor by a clear margin to be real."""
    return floor <= 0.0 or target_kappa > floor * margin
