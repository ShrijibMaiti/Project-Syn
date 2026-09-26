"""Spread beats volume.

PySR cannot separate n*log(n) from n^1.5 from n^2 unless the samples span enough
decades. Ten points across five decades beats ten thousand points all at n~1000.
When spread is insufficient SYN reports UNKNOWN -- it never fabricates a law.

Sufficiency depends on POINTS + DECADES only. Discriminability is ADVISORY: O(n)
vs O(n log n) are near-inseparable at any realistic spread, and letting that veto
an otherwise sound fit rejects good data.
"""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from telemetry.multiscale_sweep import MultiScaleData

MIN_DECADES = 2.0
MIN_POINTS = 5


@dataclass
class SpreadReport:
    decades: float
    points: int
    sufficient: bool
    discriminable: bool
    reason: str


def _candidates(n):
    return {"O(n)": n, "O(n log n)": n * np.log2(np.maximum(n, 2)),
            "O(n^1.5)": n ** 1.5, "O(n^2)": n ** 2}


def confusable_pair(n: np.ndarray, noise_frac: float = 0.05):
    """Which two candidate laws are hardest to tell apart over this range?
    Returns (pair, is_discriminable, separation). ADVISORY ONLY."""
    names = list(_candidates(n))
    curves = []
    for v in _candidates(n).values():
        v = np.asarray(v, dtype=float)
        rng = v.max() - v.min()
        curves.append((v - v.min()) / rng if rng > 0 else v * 0)
    worst = (1e9, None)
    for i, a in enumerate(curves):
        for j in range(i + 1, len(curves)):
            sep = float(np.max(np.abs(a - curves[j])))
            if sep < worst[0]:
                worst = (sep, (names[i], names[j]))
    return worst[1], worst[0] > noise_frac, worst[0]


def check(data: MultiScaleData, min_decades: float = MIN_DECADES) -> SpreadReport:
    d, p = data.decades, len(data)
    if p < MIN_POINTS:
        return SpreadReport(d, p, False, False, f"only {p} points (need {MIN_POINTS})")
    if d < min_decades:
        return SpreadReport(d, p, False, False,
                            f"only {d:.2f} decades of spread (need {min_decades})")
    pair, disc, sep = confusable_pair(data.n)
    reason = ("ok" if disc else
              f"closest pair {pair[0]} vs {pair[1]} separated by only {sep:.3f}")
    return SpreadReport(d, p, True, disc, reason)