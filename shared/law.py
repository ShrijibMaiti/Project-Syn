"""Serialized scaling law + confidence + scale-spread flag."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Callable, Dict, Optional

import numpy as np


@dataclass
class ScalingLaw:
    expression: str                      # e.g. "2.0*n**2 + 5.0*n"
    coefficients: Dict[str, float]
    complexity_class: str                # "O(n^2)", "O(n log n)", ...
    r2: float
    confidence: float                    # 0-1, penalized by weak scale spread
    scale_spread_decades: float          # log10(max_n / min_n) actually sampled
    sufficient_evidence: bool            # False => SYN must report UNKNOWN, never a law
    n_min: float = 0.0
    n_max: float = 0.0
    note: str = ""

    def evaluate(self, n):
        if not self.sufficient_evidence:
            return float("nan")
        return float(eval(self.expression, {"__builtins__": {}},
            {"n": float(n), "np": np, "nan": float("nan"), "log": np.log,
            "log2": np.log2, "sqrt": np.sqrt, "exp": np.exp}))

    def as_callable(self) -> Callable[[float], float]:
        return self.evaluate

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def insufficient(reason: str, spread: float = 0.0) -> "ScalingLaw":
        """The honest non-answer. Never fabricate a law from thin data."""
        return ScalingLaw(expression="nan", coefficients={},
                          complexity_class="unknown", r2=0.0, confidence=0.0,
                          scale_spread_decades=spread, sufficient_evidence=False,
                          note=reason)