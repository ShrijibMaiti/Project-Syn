"""Candidate targets with GROUND TRUTH.

Ground truth here is read ONLY by the scoring harness. SYN receives an anonymised,
shuffled list and never sees `is_faulty`, `trap`, `why`, or the real target names.

SCOPE -- state this plainly to judges: this validates CLASSIFICATION (given N
unlabeled candidates, which are risky?). It does NOT validate TARGET SELECTION
in a large repo -- choosing which of 10,000 functions to probe is a graph-analysis
problem deferred to Phase 2. Conflating the two is an overclaim.

TRAPS: three negatives are built specifically to fool an over-eager detector --
an O(n log n) sort (superlinear in theory), an N+1 pattern (a real fault, but
linear), and pure linear contention (the exact case that produced an earlier
catastrophic false positive). They are flagged explicitly with `trap=True` so the
dashboard never has to infer them from description text.
"""
from __future__ import annotations
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, List

# --- COMPLEXITY candidates: REAL algorithms, not hard-coded timings ---

def _linear_scan(n: int):
    return sum(1 for _ in range(n))

def _sort_nlogn(n: int):
    data = [(i * 7919) % max(n, 1) for i in range(n)]
    data.sort()
    return data[-1] if data else 0

def _nested_quadratic(n: int):
    """Nested-loop join with no index: for each item, scan all items."""
    a = list(range(n)); b = list(range(n))
    hits = 0
    for x in a:
        for y in b:
            if y == x:
                hits += 1
                break
    return hits

def _indexed_linear(n: int):
    """The FIXED version: index once, then O(n) lookup."""
    idx = {y: y for y in range(n)}
    return sum(1 for x in range(n) if x in idx)

def _n_plus_one(n: int):
    """N+1: one 'query' per record. A REAL performance fault, but LINEAR.
    SYN gates on SUPERLINEARITY, so the correct answer is CLEAN. Included
    deliberately to prove SYN does not over-flag."""
    total = 0
    for _ in range(n):
        total += sum(range(3))
    return total


# --- STABILITY candidates: sleep-based so the GIL does not serialise them ---

class _Service:
    """base + sigma_k*n (contention, NO trap) + coherency_k*n^2 (trap)."""
    def __init__(self, base_s=0.008, sigma_k=0.0, coherency_k=0.0):
        self.base_s = base_s
        self.sigma_k = sigma_k
        self.coherency_k = coherency_k
        self.inflight = 0
        self._lock = threading.Lock()

    def call(self):
        with self._lock:
            n = self.inflight
            self.inflight += 1
        try:
            time.sleep(self.base_s + self.sigma_k * n + self.coherency_k * (n ** 2))
        finally:
            with self._lock:
                self.inflight -= 1


@dataclass
class Candidate:
    id: str
    kind: str                      # "complexity" | "stability"
    call: Callable
    is_faulty: bool                # GROUND TRUTH -- never shown to SYN
    why: str
    n_max: int = 4000
    trap: bool = False             # GROUND TRUTH -- built to fool an over-eager detector


def build_catalog() -> List[Candidate]:
    return [
        Candidate("c_quadratic", "complexity", _nested_quadratic, True,
                  "nested-loop join, O(n^2)", n_max=3000),
        Candidate("c_linear", "complexity", _linear_scan, False,
                  "linear scan, O(n)", n_max=200000),
        Candidate("c_sort", "complexity", _sort_nlogn, False,
                  "sort, O(n log n) -- borderline, must NOT trip superlinear",
                  n_max=200000, trap=True),
        Candidate("c_indexed", "complexity", _indexed_linear, False,
                  "indexed lookup, O(n)", n_max=200000),
        Candidate("c_nplus1", "complexity", _n_plus_one, False,
                  "N+1 -- real fault but LINEAR; must not be flagged",
                  n_max=100000, trap=True),
        Candidate("s_coherent_strong", "stability", _Service(coherency_k=1.5e-4).call, True,
                  "strong coherency cost, kappa>0"),
        Candidate("s_coherent_weak", "stability", _Service(coherency_k=4e-5).call, True,
                  "weak coherency cost, kappa>0"),
        Candidate("s_contention", "stability", _Service(sigma_k=6e-4).call, False,
                  "pure CONTENTION (linear) -- the hard negative, must not be flagged",
                  trap=True),
        Candidate("s_flat", "stability", _Service().call, False,
                  "constant service time, no contention"),
    ]


def anonymise(cands: List[Candidate], seed: int = 0):
    """Shuffle and strip every label. Returns (blind_list, truth_map).

    The blind list carries ONLY what SYN may see: an alias, the lens kind, the
    callable, and its sweep range. is_faulty, trap, why and the real id stay in
    truth_map, which only the scoring harness reads."""
    rng = random.Random(seed)
    shuffled = cands[:]
    rng.shuffle(shuffled)
    blind, truth = [], {}
    for i, c in enumerate(shuffled):
        alias = f"target_{i:02d}"
        blind.append({"alias": alias, "kind": c.kind, "call": c.call, "n_max": c.n_max})
        truth[alias] = c
    return blind, truth