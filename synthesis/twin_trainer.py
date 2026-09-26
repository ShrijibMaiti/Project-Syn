"""Fit the Twin's transfer functions to REAL telemetry (contrastive alignment).
The Twin is fit to an independently-instrumented app -- never to its own output."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch

from synthesis.simulator import RetryLoopTwin


@dataclass
class FitReport:
    steps: int
    final_loss: float
    residual_rmse: float
    converged: bool


def fit(twin: RetryLoopTwin, X: np.ndarray, X_next: np.ndarray, loads: np.ndarray,
        steps: int = 2000, lr: float = 1e-2, verbose: bool = False) -> FitReport:
    """One-step prediction loss: || f(x_t, load) - x_{t+1} ||^2."""
    if X.size == 0:
        return FitReport(0, float("nan"), float("nan"), False)
    q = torch.tensor(X[:, 0], dtype=torch.float32)
    qn = torch.tensor(X_next[:, 0], dtype=torch.float32)
    L = torch.tensor(loads, dtype=torch.float32)
    opt = torch.optim.Adam(twin.parameters(), lr=lr)  # nn.Module.parameters()

    loss_val = float("nan")
    for i in range(steps):
        opt.zero_grad()
        pred = twin._step_t(q, L)
        loss = torch.mean((pred - qn) ** 2)
        loss.backward()
        opt.step()
        loss_val = float(loss.detach())
        if verbose and i % 200 == 0:
            print(f"[twin] step {i} loss {loss_val:.5f}")

    with torch.no_grad():
        rmse = float(torch.sqrt(torch.mean((twin._step_t(q, L) - qn) ** 2)))
    return FitReport(steps, loss_val, rmse, converged=rmse < 0.5)