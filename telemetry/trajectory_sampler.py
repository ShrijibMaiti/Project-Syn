"""(state, next_state) pairs -- the training data for the Lyapunov certificate."""
from __future__ import annotations
from typing import Dict, List, Sequence, Tuple

import numpy as np

from shared.order_params import OrderParams


class TrajectorySampler:
    def __init__(self, params: OrderParams | None = None):
        self.params = params or OrderParams.default()

    def pairs(self, rows: Sequence[Dict[str, float]], max_dt: float = 1.0
              ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (X, X_next, loads). Drops pairs with a time gap > max_dt."""
        X, Xn, L = [], [], []
        for a, b in zip(rows, rows[1:]):
            dt = float(b.get("t", 0.0)) - float(a.get("t", 0.0))
            if not (0 < dt <= max_dt):
                continue
            X.append(self.params.to_vector(a))
            Xn.append(self.params.to_vector(b))
            L.append(float(a.get("load", 0.0)))
        if not X:
            return (np.empty((0, self.params.dim)), np.empty((0, self.params.dim)),
                    np.empty((0,)))
        return np.vstack(X), np.vstack(Xn), np.asarray(L)

    def healthy_equilibrium(self, rows: Sequence[Dict[str, float]],
                            low_load_quantile: float = 0.25) -> np.ndarray:
        """x*: the median state under the lowest-load rows. Pinning V(x*)=0 here is
        what keeps the certificate from collapsing to the trivial solution."""
        if not rows:
            return np.zeros(self.params.dim)
        loads = np.array([float(r.get("load", 0.0)) for r in rows])
        cut = np.quantile(loads, low_load_quantile)
        sel = [r for r, l in zip(rows, loads) if l <= cut] or list(rows)
        return np.median(self.params.matrix(sel), axis=0)