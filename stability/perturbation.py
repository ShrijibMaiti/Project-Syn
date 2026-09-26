"""Inject a diff into the Twin, measure how the margin moves. The differentiable
Twin also gives the gradient directly -- no re-settling needed for direction."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from shared.simulator_iface import SimulatorIface
from shared.verdict import StabilityEvidence
from stability.basin_detector import critical_load, detect


@dataclass
class PerturbationResult:
    before: StabilityEvidence
    after: StabilityEvidence
    margin_drop: Optional[float]
    critical_load_before: Optional[float]
    critical_load_after: Optional[float]
    gradients: Dict[str, float]


def apply_knobs(sim, knobs: Dict[str, float]) -> None:
    import torch
    params = sim.parameters_dict()
    with torch.no_grad():
        for k, v in knobs.items():
            if k in params:
                params[k].copy_(torch.tensor(float(v)))


def evaluate_diff(sim, load: float, new_knobs: Dict[str, float],
                  loads_scan: Optional[List[float]] = None) -> PerturbationResult:
    loads_scan = loads_scan or [0.5 * i for i in range(1, 13)]
    old = sim.parameters()
    before = detect(sim, load)
    cl_before = critical_load(sim, loads_scan)
    grads = sim.sensitivity_all([sim.ceiling() or 50.0], load)

    apply_knobs(sim, new_knobs)
    after = detect(sim, load)
    cl_after = critical_load(sim, loads_scan)
    apply_knobs(sim, old)                         # restore

    drop = None
    if before.margin and after.margin is not None and before.margin > 0:
        drop = float((before.margin - after.margin) / before.margin)
    return PerturbationResult(before, after, drop, cl_before, cl_after, grads)