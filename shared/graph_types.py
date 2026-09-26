"""Node/edge schema both synthesis and orchestration read."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Node:
    id: str                       # "module.func"
    module: str
    name: str
    lineno: int = 0
    kind: str = "function"


@dataclass
class Edge:
    src: str
    dst: str
    kind: str = "call"            # call | async | db | http
    weight: float = 1.0


@dataclass
class CodeGraph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    def add_node(self, n: Node) -> None:
        self.nodes[n.id] = n

    def add_edge(self, e: Edge) -> None:
        self.edges.append(e)

    def successors(self, nid: str) -> List[str]:
        return [e.dst for e in self.edges if e.src == nid]

    def predecessors(self, nid: str) -> List[str]:
        return [e.src for e in self.edges if e.dst == nid]

    def reachable_from(self, nid: str) -> Set[str]:
        seen, stack = set(), [nid]
        while stack:
            cur = stack.pop()
            for s in self.successors(cur):
                if s not in seen:
                    seen.add(s); stack.append(s)
        return seen

    def cycles(self) -> List[List[str]]:
        """Dependency cycles — static, exact, cheap. (Note: this is NOT deadlock
        detection; SYN does not claim discrete precursor-free faults.)"""
        out, color, path = [], {}, []

        def dfs(u: str) -> None:
            color[u] = 1; path.append(u)
            for v in self.successors(u):
                if color.get(v, 0) == 0:
                    dfs(v)
                elif color.get(v) == 1:
                    out.append(path[path.index(v):] + [v])
            path.pop(); color[u] = 2

        for n in list(self.nodes):
            if color.get(n, 0) == 0:
                dfs(n)
        return out

    def to_dict(self) -> dict:
        return {"nodes": [n.__dict__ for n in self.nodes.values()],
                "edges": [e.__dict__ for e in self.edges]}