"""THE anti-trivial-solution fix.

A naive Lyapunov loss L = L_data + relu(-V) + relu(Vdot) is globally minimized by
V == 0: both penalties vanish, and there is NO ground-truth label for V because
FINDING V is the task. The certificate learns to detect nothing.

Fix (Chang et al. 2019; Abate et al.): make V structurally positive-definite with
V(x*) = 0 by construction, so V == 0 is not in the hypothesis class at all.

    V(x) = || phi(x) - phi(x*) ||^2  +  eps * || x - x* ||^2

The eps term is what makes it STRICTLY positive away from x*: even if the network
phi collapses to a constant, V(x) = eps*||x-x*||^2 > 0. Collapse is impossible.
"""
from __future__ import annotations

import torch
import torch.nn as nn


class PDLyapunov(nn.Module):
    def __init__(self, dim: int, hidden: int = 64, eps: float = 1e-2):
        super().__init__()
        if eps <= 0:
            raise ValueError("eps must be > 0 -- it is the anti-collapse guarantee")
        self.phi = nn.Sequential(nn.Linear(dim, hidden), nn.Tanh(),
                                 nn.Linear(hidden, hidden), nn.Tanh(),
                                 nn.Linear(hidden, hidden))
        self.eps = float(eps)
        self.register_buffer("x_star", torch.zeros(dim))

    def set_equilibrium(self, x_star: torch.Tensor) -> None:
        self.x_star = torch.as_tensor(x_star, dtype=torch.float32).clone()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(0)
        d = x - self.x_star
        p = self.phi(x) - self.phi(self.x_star.unsqueeze(0))
        return (p ** 2).sum(dim=-1) + self.eps * (d ** 2).sum(dim=-1)

    # -- guarantees, assertable in tests ----------------------------------
    def at_equilibrium(self) -> float:
        with torch.no_grad():
            return float(self(self.x_star.unsqueeze(0))[0])

    def is_nontrivial(self, x_samples: torch.Tensor, min_spread: float = 1e-3) -> bool:
        """V must actually vary over the state space. Guards against a degenerate
        certificate even though the parameterization makes exact collapse impossible."""
        with torch.no_grad():
            v = self(x_samples)
        return bool((v.max() - v.min()).item() > min_spread)