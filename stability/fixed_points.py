"""Find and classify the attractors of the learned dynamics.

VERIFIED against the built twin. Three things this gets right that a naive version
does not:
  1. generous RELATIVE clustering (a tight tolerance splits one attractor into
     several near-duplicates)
  2. a residual check f(p) == p -- settle() output alone yields artifacts
  3. requires a ceiling on the simulator, else the collapsed basin diverges and
     never registers as a fixed point
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from shared.simulator_iface import SimulatorIface


@dataclass
class FixedPoint:
    value: float
    stable: bool
    at_ceiling: bool


def find_fixed_points(sim: SimulatorIface, load: float, rtol: float = 0.02,
                      atol: float = 0.05, resid_tol: float = 1e-3,
                      n_starts: int = 25, steps: int = 3000) -> List[float]:
    hi = sim.ceiling() or 1e4
    starts = np.concatenate([[0.0], np.logspace(-2, np.log10(hi), n_starts)])
    pts = sorted(float(sim.settle(np.array([s]), load, steps)[0]) for s in starts)
    pts = [p for p in pts if np.isfinite(p)]
    if not pts:
        return []

    clusters: List[List[float]] = [[pts[0]]]
    for p in pts[1:]:
        ref = clusters[-1][-1]
        if abs(p - ref) > max(atol, rtol * max(abs(p), abs(ref))):
            clusters.append([p])
        else:
            clusters[-1].append(p)

    out = []
    for c in clusters:
        p = float(np.mean(c))
        if abs(float(sim.step(np.array([p]), load)[0]) - p) < resid_tol:
            out.append(p)                       # must actually satisfy f(p) = p
    return out


def classify(sim: SimulatorIface, load: float, p: float, h: float = 1e-3) -> FixedPoint:
    """Discrete-time stability: |f'(p)| < 1."""
    fp = (float(sim.step(np.array([p + h]), load)[0]) -
          float(sim.step(np.array([p - h]), load)[0])) / (2 * h)
    ceil = sim.ceiling()
    return FixedPoint(value=p, stable=abs(fp) < 1.0,
                      at_ceiling=ceil is not None and abs(p - ceil) < 1e-6)


def attractor_index(sim: SimulatorIface, q0: float, load: float,
                    fps: List[float], steps: int = 3000) -> int:
    end = float(sim.settle(np.array([q0]), load, steps)[0])
    return int(np.argmin([abs(end - fp) for fp in fps]))