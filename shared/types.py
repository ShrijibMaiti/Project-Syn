"""Shared dataclasses and enums. Imports nothing from other domains."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RiskLevel(str, Enum):
    OK = "ok"
    WARN = "warn"
    REFUSE = "refuse"
    UNKNOWN = "unknown"          # insufficient evidence — never silently "ok"


class BoundType(str, Enum):
    COMPUTE = "compute"          # ceiling-independent (O(2^n) etc.)
    MEMORY = "memory"            # moves with RAM
    POOL = "pool"                # moves with connection/thread pool size
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class ProbeKind(str, Enum):
    STABILITY = "stability"
    COMPLEXITY = "complexity"


@dataclass
class ProbeResult:
    kind: ProbeKind
    risk: RiskLevel
    summary: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class TwinState:
    """One sample of the macroscopic order-parameter vector."""
    values: List[float]
    t: float = 0.0
    load: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)