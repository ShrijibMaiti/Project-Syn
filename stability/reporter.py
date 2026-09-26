"""Margin + basin -> human-readable warning. Estimates with assumptions, never
'mathematical certainty'."""
from __future__ import annotations
from typing import Optional

from shared.types import ProbeKind, ProbeResult, RiskLevel
from shared.verdict import StabilityEvidence, margin_to_risk


def summarize(ev: StabilityEvidence, drop: Optional[float] = None,
              critical_before: Optional[float] = None,
              critical_after: Optional[float] = None) -> ProbeResult:
    if not ev.bistable:
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.OK,
                           f"No second basin at load {ev.load:g}: single attractor "
                           f"at {ev.fixed_points[0]:.2f}." if ev.fixed_points
                           else f"No verified fixed point at load {ev.load:g}.",
                           evidence=ev.__dict__)

    risk = margin_to_risk(ev.margin, drop)
    bits = [f"Metastable basin detected at load {ev.load:g}: attractors "
            f"{[round(p, 2) for p in ev.fixed_points]}."]
    if ev.margin is not None:
        bits.append(f"Separatrix at {ev.separatrix:.2f}; normalized margin "
                    f"{ev.margin:.3f} from operating point {ev.operating_point:.2f}.")
    if drop is not None:
        bits.append(f"This change reduces the margin by {drop*100:.0f}%.")
    if critical_before is not None and critical_after is not None:
        bits.append(f"Death-spiral threshold moves {critical_before:g} -> "
                    f"{critical_after:g} req/s.")
    bits.append("Early warning, learned and probabilistic -- not a certainty.")
    return ProbeResult(ProbeKind.STABILITY, risk, " ".join(bits), evidence=ev.__dict__)