"""Does the Twin actually mirror the real system? Report the residual; a Twin that
does not track reality invalidates every downstream claim."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence

import numpy as np

from shared.order_params import OrderParams
from shared.simulator_iface import SimulatorIface


@dataclass
class IsomorphismReport:
    one_step_rmse: float
    settled_error: float
    passed: bool
    note: str = ""


def one_step_residual(sim: SimulatorIface, X: np.ndarray, X_next: np.ndarray,
                      loads: np.ndarray) -> float:
    if X.size == 0:
        return float("nan")
    preds = np.array([sim.step(x, float(l))[0] for x, l in zip(X, loads)])
    return float(np.sqrt(np.mean((preds - X_next[:, 0]) ** 2)))


def settled_residual(sim: SimulatorIface, real_settled: Dict[float, float]) -> float:
    """Compare the Twin's attractor to the real app's observed settled state."""
    if not real_settled:
        return float("nan")
    errs = [abs(float(sim.settle(np.array([0.0]), L)[0]) - q)
            for L, q in real_settled.items()]
    return float(np.mean(errs))


def check(sim: SimulatorIface, X: np.ndarray, X_next: np.ndarray, loads: np.ndarray,
          real_settled: Dict[float, float] | None = None,
          rmse_tol: float = 0.5, settle_tol: float = 2.0) -> IsomorphismReport:
    r1 = one_step_residual(sim, X, X_next, loads)
    r2 = settled_residual(sim, real_settled or {})
    ok = (np.isnan(r1) or r1 <= rmse_tol) and (np.isnan(r2) or r2 <= settle_tol)
    return IsomorphismReport(r1, r2, bool(ok),
                             "" if ok else "Twin does not track reality; "
                                           "downstream claims are not supported")