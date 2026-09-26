"""Where does the law cross a NAMED ceiling? Reported as an estimate with its
assumption -- never 'the exact detonation point'."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from complexity.ceilings import Ceiling, for_metric
from shared.law import ScalingLaw
from shared.types import ProbeKind, ProbeResult, RiskLevel
from shared.verdict import ComplexityEvidence, DEFAULT_THRESHOLDS


@dataclass
class Detonation:
    crossing_n: Optional[float]
    ceiling: Ceiling
    law: ScalingLaw


def crossing(law: ScalingLaw, ceiling: Ceiling, n_hi: float = 1e9) -> Optional[float]:
    """Bisect for f(n) = ceiling.value on [n_min, n_hi]."""
    if not law.sufficient_evidence:
        return None
    lo = max(law.n_min, 1.0)
    try:
        if law.evaluate(lo) >= ceiling.value:
            return lo
        if law.evaluate(n_hi) < ceiling.value:
            return None                      # never crosses in a sane range
    except Exception:
        return None
    for _ in range(200):
        mid = np.sqrt(lo * n_hi)             # geometric bisection over decades
        try:
            v = law.evaluate(mid)
        except Exception:
            return None
        if v < ceiling.value:
            lo = mid
        else:
            n_hi = mid
        if n_hi / lo < 1.0001:
            break
    return float(np.sqrt(lo * n_hi))


def estimate(law: ScalingLaw, metric: str = "elapsed_s",
             ceiling: Optional[Ceiling] = None) -> Detonation:
    c = ceiling or for_metric(metric)
    return Detonation(crossing(law, c), c, law)


def to_probe(det: Detonation, th=DEFAULT_THRESHOLDS) -> ProbeResult:
    law, c, n = det.law, det.ceiling, det.crossing_n
    ev = ComplexityEvidence(law.complexity_class, law.expression, n, c.name,
                            c.bound.value, law.sufficient_evidence, law.confidence)
    if not law.sufficient_evidence:
        return ProbeResult(ProbeKind.COMPLEXITY, RiskLevel.UNKNOWN,
                           f"Insufficient evidence to certify a scaling law: {law.note}",
                           evidence=ev.__dict__)
    if n is None:
        return ProbeResult(ProbeKind.COMPLEXITY, RiskLevel.OK,
                           f"Estimated {law.complexity_class}; no crossing of "
                           f"{c.name} within the sane range.", evidence=ev.__dict__)
    risk = (RiskLevel.REFUSE if n <= th["detonation_refuse_n"]
            else RiskLevel.WARN if n <= th["detonation_warn_n"] else RiskLevel.OK)
    return ProbeResult(ProbeKind.COMPLEXITY, risk,
                       f"Estimated {law.complexity_class} (fit {law.expression}, "
                       f"R^2={law.r2:.3f}, {law.scale_spread_decades:.1f} decades). "
                       f"Crosses {c.name}={c.value:g} {c.unit} near n~{n:,.0f} "
                       f"({c.caveat()}).", evidence=ev.__dict__)