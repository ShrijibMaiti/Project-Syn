"""The Twin's contract. Every sensitivity claim in SYN depends on this signature;
changing it later invalidates every downstream read."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional

import numpy as np


class SimulatorIface(ABC):
    """A differentiable dynamical simulator over order parameters."""

    @property
    @abstractmethod
    def dim(self) -> int: ...

    @abstractmethod
    def step(self, x: np.ndarray, load: float) -> np.ndarray:
        """One tick of the dynamics: x_{t+1} = f(x_t, load)."""

    @abstractmethod
    def settle(self, x0: np.ndarray, load: float, steps: int = 3000) -> np.ndarray:
        """Iterate to the fixed point of the basin x0 falls into."""

    @abstractmethod
    def sensitivity(self, x0: np.ndarray, load: float, param: str) -> float:
        """d(collapse-energy)/d(param), computed on the Twin — no production run."""

    @abstractmethod
    def parameters(self) -> Dict[str, float]:
        """Named, perturbable config knobs (retry_gain, pool_size, ...)."""

    def ceiling(self) -> Optional[float]:
        """Discrete resource ceiling (OOM/timeout/throttle). Real systems hit this
        before any asymptote. None means unbounded (only honest for pure models)."""
        return None