"""Fitted law vs. ACTUAL high-scale runs -- does extrapolation hold?"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from shared.law import ScalingLaw
from telemetry.multiscale_sweep import MultiScaleData


@dataclass
class LawValidation:
    n_holdout: List[float]
    predicted: List[float]
    actual: List[float]
    mape: float
    passed: bool


def validate(law: ScalingLaw, holdout: MultiScaleData,
             max_mape: float = 0.25) -> LawValidation:
    """Fit on low n, validate on HELD-OUT high n. This is the only honest test of
    an extrapolation claim."""
    if not law.sufficient_evidence or len(holdout) == 0:
        return LawValidation([], [], [], float("nan"), False)
    pred = np.array([law.evaluate(n) for n in holdout.n])
    act = holdout.resource
    mape = float(np.mean(np.abs((act - pred) / np.maximum(np.abs(act), 1e-12))))
    return LawValidation(holdout.n.tolist(), pred.tolist(), act.tolist(),
                         mape, bool(mape <= max_mape))


def split(data: MultiScaleData, frac: float = 0.7):
    k = max(2, int(len(data) * frac))
    lo = MultiScaleData(data.n[:k], data.resource[:k], data.metric)
    hi = MultiScaleData(data.n[k:], data.resource[k:], data.metric)
    return lo, hi