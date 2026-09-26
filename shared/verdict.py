"""separatrix-margin -> gate-threshold contract (probe -> aggregator)."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from shared.types import ProbeResult, RiskLevel

# Margin is normalized: (separatrix - operating_point) / scale. Dimensionless.
DEFAULT_THRESHOLDS = {
    "margin_refuse": 0.15,        # below this fraction of headroom => refuse
    "margin_warn": 0.35,
    "margin_drop_refuse": 0.50,   # PR cuts margin by >=50% => refuse
    "margin_drop_warn": 0.20,
    "detonation_refuse_n": 1e5,   # law crosses ceiling inside operating envelope
    "detonation_warn_n": 1e6,
}


@dataclass
class StabilityEvidence:
    bistable: bool
    fixed_points: List[float]
    operating_point: Optional[float]
    separatrix: Optional[float]
    margin: Optional[float]
    margin_before: Optional[float] = None
    margin_drop: Optional[float] = None
    load: float = 0.0


@dataclass
class ComplexityEvidence:
    complexity_class: str
    expression: str
    crossing_n: Optional[float]
    ceiling_name: Optional[str]
    bound_type: str
    sufficient_evidence: bool
    confidence: float = 0.0


@dataclass
class Verdict:
    risk: RiskLevel
    reasons: List[str] = field(default_factory=list)
    probes: List[ProbeResult] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.risk in (RiskLevel.OK, RiskLevel.WARN)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk"] = self.risk.value
        d["probes"] = [{**p.__dict__, "kind": p.kind.value, "risk": p.risk.value}
                       for p in self.probes]
        return d


def margin_to_risk(margin: Optional[float], drop: Optional[float],
                   th: Dict[str, float] = DEFAULT_THRESHOLDS) -> RiskLevel:
    if margin is None:
        return RiskLevel.UNKNOWN
    if margin <= th["margin_refuse"]:
        return RiskLevel.REFUSE
    if drop is not None and drop >= th["margin_drop_refuse"]:
        return RiskLevel.REFUSE
    if margin <= th["margin_warn"] or (drop is not None and drop >= th["margin_drop_warn"]):
        return RiskLevel.WARN
    return RiskLevel.OK

def relative_headroom(ev):
    """(separatrix - operating_point) / operating_point.

    Ceiling-normalized margin is arbitrary: it depends on where the OOM limit
    happens to sit, not on how close the system is to tipping. Relative headroom
    is interpretable ("113% headroom before the death spiral") and ceiling-free.
    Measured on the reference twin: 6.97 -> 2.34 -> 1.13 -> collapse.
    """
    if not ev.bistable or ev.separatrix is None or not ev.operating_point:
        return None
    return float((ev.separatrix - ev.operating_point) / max(ev.operating_point, 1e-9))


# Calibrated against the reference twin. NOT guessed -- see check_03 output.
HEADROOM_THRESHOLDS = {"refuse": 0.75, "warn": 2.0}


def headroom_to_risk(h, drop=None, th=HEADROOM_THRESHOLDS):
    from shared.types import RiskLevel
    if h is None:
        return RiskLevel.UNKNOWN
    if h <= th["refuse"] or (drop is not None and drop >= 0.50):
        return RiskLevel.REFUSE
    if h <= th["warn"] or (drop is not None and drop >= 0.20):
        return RiskLevel.WARN
    return RiskLevel.OK
