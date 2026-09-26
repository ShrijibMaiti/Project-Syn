"""Which complexity regime a path is in, WITHIN tested scales. Combines a structural
prior from the AST with the empirical fit; disagreement is itself a signal."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from complexity.symbolic_regressor import _fit_basis
from synthesis.ast_extractor import FunctionFact
from telemetry.multiscale_sweep import MultiScaleData


@dataclass
class Regime:
    empirical_class: str
    structural_prior: Optional[str]
    r2: float
    agrees: bool


def structural_prior(fact: FunctionFact) -> str:
    if fact.has_recursion and fact.loop_depth >= 1:
        return "O(n^2)"
    if fact.has_recursion:
        return "O(n log n)"
    if fact.calls_in_loop:
        return "O(n^2)"          # N+1 smell: a call inside a loop
    if fact.loop_depth >= 2:
        return "O(n^2)"
    if fact.loop_depth == 1:
        return "O(n)"
    return "O(1)"


def classify(data: MultiScaleData, fact: Optional[FunctionFact] = None) -> Regime:
    cls, _, _, r2 = _fit_basis(data)
    prior = structural_prior(fact) if fact else None
    return Regime(cls, prior, r2, agrees=(prior is None or prior == cls))