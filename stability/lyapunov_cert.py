"""Neural Lyapunov certificate -- NOT a PINN.

f is LEARNED, so there is no governing PDE residual to be 'physics-informed' by.
What this is: a learned energy function over macroscopic order parameters,
structurally positive-definite, trained against the Foster-Lyapunov drift condition
with a counterexample loop."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np
import torch

from stability.counterexample_loop import find_counterexamples, violation
from stability.pd_parameterization import PDLyapunov


@dataclass
class CertReport:
    rounds: int
    final_loss: float
    worst_violation: float
    certified: bool
    nontrivial: bool
    note: str = ""


class LyapunovCertificate:
    def __init__(self, dim: int, x_star: np.ndarray, alpha: float = 1e-3,
                 eps: float = 1e-2, hidden: int = 64):
        self.V = PDLyapunov(dim, hidden=hidden, eps=eps)
        self.x_star = torch.tensor(np.asarray(x_star, dtype=np.float32))
        self.V.set_equilibrium(self.x_star)
        self.alpha = float(alpha)
        self.dim = dim

    def train(self, f: Callable[[torch.Tensor, float], torch.Tensor], load: float,
              X: Optional[np.ndarray] = None, rounds: int = 8, steps: int = 400,
              lr: float = 1e-3, hi: float = 100.0, verbose: bool = False
              ) -> CertReport:
        opt = torch.optim.Adam(self.V.parameters(), lr=lr)
        pool = (torch.tensor(X, dtype=torch.float32) if X is not None and len(X)
                else (hi * torch.rand(256, self.dim)))
        loss_val, worst = float("nan"), float("inf")

        for r in range(rounds):
            for _ in range(steps):
                opt.zero_grad()
                v = violation(self.V, f, pool, load, self.alpha, self.x_star)
                loss = torch.relu(v).mean()
                loss.backward()
                opt.step()
                loss_val = float(loss.detach())

            ce, worst = find_counterexamples(self.V, f, self.x_star, load,
                                             self.alpha, self.dim, hi=hi)
            if verbose:
                print(f"[cert] round {r} loss={loss_val:.6f} worst_violation={worst:.6f}")
            if worst <= 0:
                break
            pool = torch.cat([pool, ce], dim=0)[-2048:]

        nontrivial = self.V.is_nontrivial(pool)
        return CertReport(rounds=r + 1, final_loss=loss_val, worst_violation=worst,
                          certified=bool(worst <= 0), nontrivial=bool(nontrivial),
                          note="certified over the sampled region only; not a global proof")

    def energy(self, x: np.ndarray) -> float:
        with torch.no_grad():
            return float(self.V(torch.tensor(np.atleast_2d(x), dtype=torch.float32))[0])