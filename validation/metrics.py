"""Scoring: detection rate, false-positive rate, confusion matrix."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Scorecard:
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def detection_rate(self): return self.tp / max(self.tp + self.fn, 1)
    @property
    def false_positive_rate(self): return self.fp / max(self.fp + self.tn, 1)
    @property
    def precision(self): return self.tp / max(self.tp + self.fp, 1)
    @property
    def accuracy(self): return (self.tp + self.tn) / max(self.tp + self.fp + self.tn + self.fn, 1)

    def __str__(self):
        return (f"TP={self.tp} FP={self.fp} TN={self.tn} FN={self.fn}  |  "
                f"detection={self.detection_rate:.0%} FPR={self.false_positive_rate:.0%} "
                f"precision={self.precision:.0%} accuracy={self.accuracy:.0%}")


def score(pairs: List[Tuple[bool, bool]]) -> Scorecard:
    """pairs = [(truth_faulty, syn_flagged), ...]"""
    tp = sum(1 for t, f in pairs if t and f)
    fp = sum(1 for t, f in pairs if not t and f)
    tn = sum(1 for t, f in pairs if not t and not f)
    fn = sum(1 for t, f in pairs if t and not f)
    return Scorecard(tp, fp, tn, fn)
