"""PR-check state machine, kept separate from agent glue so the platform's process
model cannot collide with it."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class Stage(str, Enum):
    RECEIVED = "received"
    PROBING = "probing"
    AGGREGATING = "aggregating"
    DONE = "done"
    FAILED = "failed"


@dataclass
class RunContext:
    commit: str
    stage: Stage = Stage.RECEIVED
    artifacts: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)

    def advance(self, s: Stage) -> "RunContext":
        self.stage = s
        return self

    def fail(self, m: str) -> "RunContext":
        self.errors.append(m)
        self.stage = Stage.FAILED
        return self

    @property
    def ok(self) -> bool:
        return self.stage is not Stage.FAILED
