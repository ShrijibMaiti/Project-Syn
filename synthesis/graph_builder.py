"""AST facts -> CodeGraph (the Twin's topology)."""
from __future__ import annotations
from typing import Dict, List

from shared.graph_types import CodeGraph, Edge, Node
from synthesis.ast_extractor import FunctionFact, extract_tree

DB_HINTS = {"execute", "query", "fetch", "fetchall", "fetchone", "get", "select"}


def build(facts: Dict[str, FunctionFact]) -> CodeGraph:
    g = CodeGraph()
    by_name: Dict[str, List[str]] = {}
    for fid, f in facts.items():
        g.add_node(Node(id=fid, module=f.module, name=f.name, lineno=f.lineno))
        by_name.setdefault(f.name, []).append(fid)

    for fid, f in facts.items():
        for callee in set(f.calls):
            for target in by_name.get(callee, []):
                if target != fid:
                    kind = "db" if callee in DB_HINTS else "call"
                    w = 2.0 if callee in f.calls_in_loop else 1.0
                    g.add_edge(Edge(src=fid, dst=target, kind=kind, weight=w))
    return g


def build_from_path(root: str) -> CodeGraph:
    return build(extract_tree(root))


def hot_paths(g: CodeGraph, facts: Dict[str, FunctionFact]) -> List[str]:
    """Nodes whose structure suggests superlinear cost -- the complexity probe's
    candidates. Structural prior only; the LAW comes from telemetry + PySR."""
    out = []
    for fid, f in facts.items():
        if f.loop_depth >= 2 or f.has_recursion or f.calls_in_loop:
            out.append(fid)
    return out