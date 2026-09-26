"""The Differentiable Digital Twin.

Dynamics over macroscopic order parameters. Differentiable end-to-end, so a diff
injected at one node yields d(collapse-energy)/d(knob) by autodiff -- no prod run.

CEILING: real systems hit a discrete resource ceiling (OOM / timeout / throttle)
before any asymptote. Without it the collapsed basin runs to infinity and fixed-point
detection fails. Verified: with the ceiling the collapsed attractor is a genuine
fixed point and the separatrix margin shrinks monotonically with load.
"""
from __future__ import annotations
from typing import Dict, Optional

import numpy as np
import torch

from shared.simulator_iface import SimulatorIface
from synthesis.transfer_functions import GatedGain, SaturatingDrain


class RetryLoopTwin(torch.nn.Module, SimulatorIface):
    """Single-order-parameter Twin (queue pressure at a service with a retry loop).
    The minimal system that exhibits genuine metastability."""

    def __init__(self, q_max: float = 100.0, gain: float = 6.0, thresh: float = 5.0,
                 width: float = 1.0, cap: float = 10.0, k: float = 3.0):
        torch.nn.Module.__init__(self)
        self.retries = GatedGain(gain, thresh, width)
        self.drain = SaturatingDrain(cap, k)
        self.q_max = float(q_max)

    # -- SimulatorIface ----------------------------------------------------
    @property
    def dim(self) -> int:
        return 1

    def ceiling(self) -> Optional[float]:
        return self.q_max

    def _step_t(self, q: torch.Tensor, load: torch.Tensor) -> torch.Tensor:
        nxt = q + load + self.retries(q) - self.drain(q)
        return torch.clamp(nxt, min=0.0, max=self.q_max)

    def step(self, x, load: float):
        q = torch.as_tensor(np.atleast_1d(x)[0], dtype=torch.float32)
        out = self._step_t(q, torch.as_tensor(float(load)))
        return np.array([float(out.detach())])

    def settle(self, x0, load: float, steps: int = 3000):
        q = torch.as_tensor(float(np.atleast_1d(x0)[0]), dtype=torch.float32)
        L = torch.as_tensor(float(load))
        for _ in range(steps):
            q = self._step_t(q, L)
        return np.array([float(q.detach())])

    def settle_t(self, q0: float, load: float, steps: int = 300) -> torch.Tensor:
        """Differentiable settle -- keeps the graph for sensitivity."""
        q = torch.as_tensor(float(q0), dtype=torch.float32)
        L = torch.as_tensor(float(load))
        for _ in range(steps):
            q = self._step_t(q, L)
        return q

    def parameters_dict(self) -> Dict[str, torch.nn.Parameter]:
        return {"retry_gain": self.retries._gain, "retry_thresh": self.retries.thresh,
                "retry_width": self.retries._width,
                "service_cap": self.drain._cap, "service_k": self.drain._k}

    def parameters(self) -> Dict[str, float]:   # type: ignore[override]
        return {k: float(v.detach()) for k, v in self.parameters_dict().items()}

    def sensitivity(self, x0, load: float, param: str) -> float:
        """d(collapse-energy)/d(param) by autodiff through the dynamics."""
        knobs = self.parameters_dict()
        if param not in knobs:
            raise KeyError(f"unknown knob {param!r}; have {list(knobs)}")
        self.zero_grad(set_to_none=True)
        q = self.settle_t(float(np.atleast_1d(x0)[0]), load)
        energy = q * q
        g = torch.autograd.grad(energy, knobs[param], retain_graph=False,
                                allow_unused=True)[0]
        return 0.0 if g is None else float(g)

    def sensitivity_all(self, x0, load: float) -> Dict[str, float]:
        return {k: self.sensitivity(x0, load, k) for k in self.parameters_dict()}