"""What to probe.

SYN cannot guess which functions to measure: the complexity lens needs a callable
parameterised by INPUT SIZE, the stability lens one parameterised by CONCURRENCY.
Those are DIFFERENT AXES, so targets are declared explicitly. (Phase 2 graph
analysis would derive them from the call graph.)"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class ComplexityTarget:
    name: str
    call: Callable[[int], object]          # fn(n) where n = INPUT SIZE
    metric: str = "elapsed_s"
    n_min: int = 20
    n_max: int = 4000
    points: int = 9
    ceiling_name: str = "request_timeout"


@dataclass
class StabilityTarget:
    name: str
    call: Callable[[], None]               # fn() run at fixed CONCURRENCY
    levels: List[int] = field(default_factory=lambda:
        [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 256])
    samples_per_level: int = 40
    repeats: int = 3
    operating_load: Optional[float] = None  # req/s; defaults to 0.85 * measured peak


@dataclass
class ProbeManifest:
    complexity: List[ComplexityTarget] = field(default_factory=list)
    stability: List[StabilityTarget] = field(default_factory=list)
