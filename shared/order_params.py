"""Order-parameter vocabulary. THE dimensionality fix: 3-8 aggregate signals of
FIXED dimension. Never per-thread/per-lock microstate (runtime-varying dimension,
no fixed manifold). doc_parser labels these; every probe reads them."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence
import json
import os

import numpy as np

from shared.types import TwinState

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "order_state.schema.json")

# Canonical order. Index position is the contract — do not reorder without a migration.
DEFAULT_PARAMS: List[str] = [
    "queue_depth",
    "retry_rate",
    "error_rate",
    "cache_hit_ratio",
]


@dataclass
class OrderParams:
    names: List[str]
    healthy: np.ndarray            # x* : the healthy equilibrium
    labels: Dict[str, str]         # human labels (doc_parser fills these)

    @classmethod
    def default(cls, healthy: Sequence[float] | None = None) -> "OrderParams":
        n = len(DEFAULT_PARAMS)
        h = np.zeros(n) if healthy is None else np.asarray(healthy, dtype=float)
        if h.shape != (n,):
            raise ValueError(f"healthy must have shape ({n},), got {h.shape}")
        return cls(names=list(DEFAULT_PARAMS), healthy=h,
                   labels={k: k.replace("_", " ") for k in DEFAULT_PARAMS})

    @property
    def dim(self) -> int:
        return len(self.names)

    def to_vector(self, row: Dict[str, float]) -> np.ndarray:
        return np.array([float(row.get(k, 0.0)) for k in self.names], dtype=float)

    def to_state(self, row: Dict[str, float]) -> TwinState:
        return TwinState(values=self.to_vector(row).tolist(),
                         t=float(row.get("t", 0.0)), load=float(row.get("load", 0.0)))

    def from_vector(self, x: Sequence[float]) -> Dict[str, float]:
        return {k: float(v) for k, v in zip(self.names, x)}

    def matrix(self, rows: Sequence[Dict[str, float]]) -> np.ndarray:
        return np.vstack([self.to_vector(r) for r in rows]) if rows else np.empty((0, self.dim))

    def schema(self) -> dict:
        with open(SCHEMA_PATH) as fh:
            return json.load(fh)