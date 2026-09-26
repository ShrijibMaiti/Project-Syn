"""Per-edge transfer functions: the Twin's building blocks.

Two families, both differentiable:
  SaturatingDrain -- service capacity that saturates (drain)
  GatedGain       -- S-shaped feedback that stays silent when healthy and floods
                     under stress (this is what MANUFACTURES a second basin)
A pure MLP edge is available but the parametric forms are preferred: they are
interpretable, need far less data, and keep the fixed-point structure readable.
"""
from __future__ import annotations
from typing import Dict

import torch
import torch.nn as nn


class SaturatingDrain(nn.Module):
    """cap * x / (x + k) -- Michaelis-Menten style service capacity."""
    def __init__(self, cap: float = 10.0, k: float = 3.0):
        super().__init__()
        self._cap = nn.Parameter(torch.tensor(float(cap)))
        self._k = nn.Parameter(torch.tensor(float(k)))

    @property
    def cap(self): return torch.nn.functional.softplus(self._cap)

    @property
    def k(self): return torch.nn.functional.softplus(self._k) + 1e-3

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.clamp(x, min=0.0)
        return self.cap * x / (x + self.k)


class GatedGain(nn.Module):
    """gain * sigmoid((x - thresh) / width) -- the retry/feedback loop."""
    def __init__(self, gain: float = 6.0, thresh: float = 5.0, width: float = 1.0):
        super().__init__()
        self._gain = nn.Parameter(torch.tensor(float(gain)))
        self.thresh = nn.Parameter(torch.tensor(float(thresh)))
        self._width = nn.Parameter(torch.tensor(float(width)))

    @property
    def gain(self): return torch.nn.functional.softplus(self._gain)

    @property
    def width(self): return torch.nn.functional.softplus(self._width) + 1e-3

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.gain * torch.sigmoid((x - self.thresh) / self.width)


class MLPEdge(nn.Module):
    """Fallback for edges with no known functional form."""
    def __init__(self, dim_in: int = 1, hidden: int = 16):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim_in, hidden), nn.Tanh(),
                                 nn.Linear(hidden, hidden), nn.Tanh(),
                                 nn.Linear(hidden, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 1:
            x = x.unsqueeze(-1)
        return self.net(x).squeeze(-1)


def named_knobs(module: nn.Module, prefix: str = "") -> Dict[str, torch.Tensor]:
    out: Dict[str, torch.Tensor] = {}
    for name, p in module.named_parameters():
        out[f"{prefix}{name}".lstrip("."), ] = p  # type: ignore[index]
    return {k[0]: v for k, v in out.items()}