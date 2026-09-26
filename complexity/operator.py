"""PHASE 2 ONLY -- DeepONet for CURVE-VALUED resource (load-shape -> resource-curve).

Scope discipline: this is a WITHIN-REGIME classifier feeding PySR. It is never the
extrapolator. Non-perturbative regimes (GC thrash, pool exhaustion) are invisible in
low-load data; no operator can see across that gap."""
from __future__ import annotations

import torch
import torch.nn as nn


class DeepONet(nn.Module):
    def __init__(self, sensors: int = 32, p: int = 32, hidden: int = 64):
        super().__init__()
        self.branch = nn.Sequential(nn.Linear(sensors, hidden), nn.Tanh(),
                                    nn.Linear(hidden, p))
        self.trunk = nn.Sequential(nn.Linear(1, hidden), nn.Tanh(),
                                   nn.Linear(hidden, p))
        self.bias = nn.Parameter(torch.zeros(1))

    def forward(self, u: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """u: (B, sensors) sampled input-load function. y: (B, 1) query coordinate."""
        return (self.branch(u) * self.trunk(y)).sum(dim=-1, keepdim=True) + self.bias