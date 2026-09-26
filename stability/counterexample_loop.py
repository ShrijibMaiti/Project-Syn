"""Counterexample-guided training (CEGIS-style).

Sampled trajectories only cover states the system happened to visit. The drift
condition can be violated in regions never sampled -- exactly where a bad basin
hides. So: after each training round, SEARCH for violating states and feed them back.

We use gradient ascent on the violation objective (a differentiable stand-in for
the SMT solver used in the formal-verification literature)."""
from __future__ import annotations
from typing import Callable, Optional, Tuple

import torch


def drift(V, f, x: torch.Tensor, load: float) -> torch.Tensor:
    """Discrete-time Foster-Lyapunov drift: dV = V(f(x)) - V(x)."""
    return V(f(x, load)) - V(x)


def violation(V, f, x: torch.Tensor, load: float, alpha: float,
              x_star: torch.Tensor) -> torch.Tensor:
    """> 0 exactly where the drift condition dV <= -alpha*||x-x*||^2 fails."""
    d = x - x_star
    return drift(V, f, x, load) + alpha * (d ** 2).sum(dim=-1)


def find_counterexamples(V, f, x_star: torch.Tensor, load: float, alpha: float,
                         dim: int, n_starts: int = 64, steps: int = 60,
                         lo: float = 0.0, hi: float = 100.0, lr: float = 0.5,
                         keep: int = 32) -> Tuple[torch.Tensor, float]:
    """Gradient-ascend the violation from random starts; return the worst states."""
    x = (lo + (hi - lo) * torch.rand(n_starts, dim)).requires_grad_(True)
    opt = torch.optim.Adam([x], lr=lr)
    for _ in range(steps):
        opt.zero_grad()
        obj = -violation(V, f, x, load, alpha, x_star).sum()   # ascend
        obj.backward()
        opt.step()
        with torch.no_grad():
            x.clamp_(lo, hi)
    with torch.no_grad():
        v = violation(V, f, x, load, alpha, x_star)
        idx = torch.argsort(v, descending=True)[:keep]
        worst = float(v[idx[0]]) if idx.numel() else float("-inf")
        return x[idx].detach(), worst