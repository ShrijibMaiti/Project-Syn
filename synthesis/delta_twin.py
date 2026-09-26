"""PHASE 2 ONLY -- re-fit only changed nodes + neighborhood (CI latency fix)."""
from __future__ import annotations
from typing import Iterable, Set

from shared.graph_types import CodeGraph


def affected_subgraph(g: CodeGraph, changed: Iterable[str], radius: int = 1) -> Set[str]:
    frontier: Set[str] = set(changed)
    seen: Set[str] = set(frontier)
    for _ in range(radius):
        nxt: Set[str] = set()
        for n in frontier:
            nxt |= set(g.successors(n)) | set(g.predecessors(n))
        frontier = nxt - seen
        seen |= frontier
    return seen