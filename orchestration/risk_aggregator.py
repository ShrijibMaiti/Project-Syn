"""Probe results -> one verdict.

The aggregator REPORTS what the probes found; the gate (gateway/ci_gate.py)
decides POLICY. In particular, UNKNOWN is never rewritten: "a lens could not
decide" and "a lens measured something borderline" are different facts, and
relabelling UNKNOWN as WARN erased the first one. It also made
`ci_gate --fail-on-unknown` dead code, since the gate could never see UNKNOWN.

Severity order: OK < UNKNOWN < WARN < REFUSE. A definite finding (WARN or
REFUSE) outranks an inconclusive one; an inconclusive one outranks a clean
pass, so missing evidence can never present as approval.
"""
from __future__ import annotations
from typing import Dict, List

from shared.types import ProbeResult, RiskLevel
from shared.verdict import Verdict

ORDER = {RiskLevel.OK: 0, RiskLevel.UNKNOWN: 1, RiskLevel.WARN: 2, RiskLevel.REFUSE: 3}


def aggregate(probes: List[ProbeResult], escalate_on_concurrence: bool = True) -> Verdict:
    if not probes:
        return Verdict(RiskLevel.UNKNOWN, ["no probes ran"], [])

    worst = max(probes, key=lambda p: ORDER[p.risk]).risk

    # CONCURRENCE ESCALATION. Two INDEPENDENT lenses -- complexity (input size)
    # and stability (concurrency) -- flagging the same change is stronger
    # evidence than either alone. Measured: a genuinely faulty target sat at
    # exponent 1.52 (cutoff 1.7) and headroom 2.18 (cutoff 2.0) -- both just
    # under, so max-severity alone gave WARN on a change both lenses flagged.
    concurring = {p.kind for p in probes if p.risk in (RiskLevel.WARN, RiskLevel.REFUSE)}
    escalated = False
    if escalate_on_concurrence and len(concurring) >= 2 and worst is RiskLevel.WARN:
        worst = RiskLevel.REFUSE
        escalated = True

    reasons = [f"[{p.kind.value}/{p.risk.value}] {p.summary}" for p in probes]
    if escalated:
        reasons.insert(0, "[escalated] two independent lenses flagged this change; "
                          "either alone would be WARN")
    evidence: Dict[str, list] = {}
    for p in probes:
        evidence.setdefault(p.kind.value, []).append(p.evidence)
    return Verdict(worst, reasons, probes, evidence)
