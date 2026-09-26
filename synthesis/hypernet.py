"""PHASE 2 ONLY -- cross-repo generalization / cold start.

Emits Twin parameters from a graph embedding so an unseen repo gets a usable Twin
without telemetry. DO NOT BUILD THIS BEFORE THE DIRECT-TRAINED TWIN IS PROVEN --
it is the single most tempting way to spend three weeks and prove nothing.
"""
from __future__ import annotations
from typing import Dict

import numpy as np
import torch
import torch.nn as nn

from synthesis.simulator import RetryLoopTwin

KNOBS = ["retry_gain", "retry_thresh", "retry_width", "service_cap", "service_k"]


class HyperNet(nn.Module):
    def __init__(self, embed_dim: int = 32, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(embed_dim, hidden), nn.ReLU(),
                                 nn.Linear(hidden, hidden), nn.ReLU(),
                                 nn.Linear(hidden, len(KNOBS)))

    def forward(self, e: torch.Tensor) -> torch.Tensor:
        return self.net(e)

    def emit_twin(self, embedding: np.ndarray, q_max: float = 100.0) -> RetryLoopTwin:
        with torch.no_grad():
            raw = self(torch.tensor(embedding, dtype=torch.float32)).numpy()
        vals = np.abs(raw) + 1e-2
        return RetryLoopTwin(q_max=q_max, gain=float(vals[0]), thresh=float(vals[1]),
                             width=float(vals[2]), cap=float(vals[3]), k=float(vals[4]))