"""Bistability + separatrix margin. THE alarm.

The signature of metastable risk is NOT 'Vdot > 0' -- a bad basin is a SINK,
entered with Vdot <= 0. Vdot > 0 is blow-up, the opposite failure. The alarm is:
  >= 2 stable fixed points, AND the operating point close to the boundary.

Separatrix is found by bisecting on the ATTRACTOR LABEL (which basin a start
converges to), not on settled value -- bisecting on value returns garbage.
"""
from __future__ import annotations
from typing import List, Optional

import numpy as np

from shared.simulator_iface import SimulatorIface
from shared.verdict import StabilityEvidence
from stability.fixed_points import attractor_index, classify, find_fixed_points


def find_separatrix(sim: SimulatorIface, load: float, fps: List[float],
                    iters: int = 80) -> Optional[float]:
    hi = sim.ceiling() or max(fps) * 2 or 100.0
    lo = 0.0
    a_lo, a_hi = (attractor_index(sim, lo, load, fps),
                  attractor_index(sim, hi, load, fps))
    if a_lo == a_hi:
        return None                     # both ends fall to the same attractor
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if attractor_index(sim, mid, load, fps) == a_lo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def detect(sim: SimulatorIface, load: float,
           operating_point: Optional[float] = None) -> StabilityEvidence:
    fps = find_fixed_points(sim, load)
    stable = [p for p in fps if classify(sim, load, p).stable]
    pts = stable or fps
    bistable = len(pts) >= 2

    if not bistable:
        return StabilityEvidence(bistable=False, fixed_points=pts,
                                 operating_point=(pts[0] if pts else None),
                                 separatrix=None, margin=None, load=load)

    op = operating_point if operating_point is not None else pts[0]
    sep = find_separatrix(sim, load, pts)
    margin = None
    if sep is not None:
        scale = (sim.ceiling() or max(pts)) or 1.0
        margin = float(max(0.0, (sep - op)) / scale)     # normalized, dimensionless
    return StabilityEvidence(bistable=True, fixed_points=pts, operating_point=float(op),
                             separatrix=(float(sep) if sep is not None else None),
                             margin=margin, load=load)


def critical_load(sim: SimulatorIface, loads: List[float]) -> Optional[float]:
    """Lowest load at which a second basin appears. A PR that LOWERS this is the
    early warning: 'this change makes the death spiral reachable sooner.'"""
    for L in sorted(loads):
        if detect(sim, L).bistable:
            return float(L)
    return None

def effective_operating_point(sim, load, steps: int = 3000):
    """Where the system ACTUALLY settles from an empty queue.

    A fixed point can exist mathematically yet be unreachable: at load 3.8 the
    twin has a genuine healthy fixed point at 2.68, but one tick from q=0
    overshoots it (+load lands at 3.93) and the trajectory diverges to collapse.
    Assuming the lowest-valued fixed point is the operating point therefore
    reports headroom the system cannot use.
    """
    import numpy as np
    return float(sim.settle(np.array([0.0]), load, steps)[0])


def reachable_from_cold(sim, load, fp, tol: float = 0.5, steps: int = 3000) -> bool:
    return abs(effective_operating_point(sim, load, steps) - fp) <= tol
