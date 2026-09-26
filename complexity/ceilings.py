"""Named resource ceilings + bound classification.

Whether raising a resource moves the detonation point depends entirely on the bound
type -- 'you will detonate regardless of RAM' is FALSE for a memory-bound crossing."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from shared.types import BoundType


@dataclass
class Ceiling:
    name: str
    value: float
    unit: str
    bound: BoundType

    @property
    def movable(self) -> bool:
        return self.bound is not BoundType.COMPUTE

    def caveat(self) -> str:
        return ("compute-bound -- raising resources does not move this crossing"
                if self.bound is BoundType.COMPUTE
                else f"{self.bound.value}-bound -- raising {self.name} moves this crossing")


DEFAULTS: List[Ceiling] = [
    Ceiling("db_connection_pool", 512, "connections", BoundType.POOL),
    Ceiling("heap", 4 * 1024 ** 3, "bytes", BoundType.MEMORY),
    Ceiling("request_timeout", 30.0, "seconds", BoundType.TIMEOUT),
    Ceiling("cpu_budget", 1.0, "seconds/req", BoundType.COMPUTE),
]


def by_name(name: str) -> Ceiling:
    for c in DEFAULTS:
        if c.name == name:
            return c
    raise KeyError(name)


def for_metric(metric: str) -> Ceiling:
    return {"elapsed_s": by_name("request_timeout"),
            "db_calls": by_name("db_connection_pool"),
            "rss_bytes": by_name("heap")}.get(metric, by_name("request_timeout"))