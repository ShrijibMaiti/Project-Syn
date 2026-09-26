"""PHASE 2 ONLY. Graph -> fixed-size embedding, consumed by hypernet.
Not required to prove the Phase-1 thesis. Kept to one file deliberately."""
from __future__ import annotations
import numpy as np
from shared.graph_types import CodeGraph


def embed(g: CodeGraph, dim: int = 32) -> np.ndarray:
    """Cheap structural embedding: degree stats + cycle count + size.
    Phase 2 replaces this with a learned GNN encoder."""
    n = max(len(g.nodes), 1)
    out_deg = np.array([len(g.successors(i)) for i in g.nodes] or [0], dtype=float)
    in_deg = np.array([len(g.predecessors(i)) for i in g.nodes] or [0], dtype=float)
    feats = [len(g.nodes), len(g.edges), len(g.edges) / n,
             out_deg.mean(), out_deg.max(), out_deg.std(),
             in_deg.mean(), in_deg.max(), in_deg.std(), len(g.cycles())]
    v = np.zeros(dim, dtype=float)
    v[:min(dim, len(feats))] = feats[:dim]
    return v