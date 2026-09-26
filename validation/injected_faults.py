"""Catalog of PLANTED pathologies + ground truth.

CORRECTED after measurement: N+1 is O(n), not O(n^2). The quadratic fault is the
nested-loop join. Each fault names the METRIC it manifests in -- the metric
determines the recovered law and the bound type."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InjectedFault:
    id: str
    kind: str                      # "metastable" | "complexity"
    location: str                  # ground truth -- never given to SYN
    metric: str                    # which telemetry column carries the signal
    description: str
    expect: Dict[str, object] = field(default_factory=dict)
    fixed_variant: Optional[str] = None     # must NOT be flagged


CATALOG: List[InjectedFault] = [
    InjectedFault(
        id="retry_storm", kind="metastable",
        location="retry_loop.call_with_retries", metric="queue_depth",
        description=("Unbounded retry-on-timeout, no jitter, no circuit breaker. "
                     "Retries sustain the overload, so the system stays collapsed "
                     "after the trigger is removed."),
        expect={"bistable": True, "hysteresis": True, "max_critical_load": 5.0},
        fixed_variant="retry_loop.healthy_call"),

    InjectedFault(
        id="n_plus_one", kind="complexity",
        location="order_service.list_orders_with_items", metric="db_calls",
        description=("One query per order (N+1). VERIFIED O(n) round trips -- a "
                     "constant-factor disaster, NOT a quadratic."),
        expect={"complexity_class": "O(n)", "min_r2": 0.95,
                "ceiling": "db_connection_pool", "bound": "pool"}),

    InjectedFault(
        id="nested_join", kind="complexity",
        location="order_service.build_order_report", metric="elapsed_s",
        description=("Nested-loop join with no index: for each order, scan every "
                     "item. VERIFIED O(n^2) in time, O(1) in db_calls."),
        expect={"complexity_class": "O(n^2)", "min_r2": 0.95,
                "ceiling": "request_timeout", "bound": "compute"},
        fixed_variant="order_service.build_order_report_fixed"),
]


def by_kind(kind: str) -> List[InjectedFault]:
    return [f for f in CATALOG if f.kind == kind]


def by_id(fid: str) -> Optional[InjectedFault]:
    return next((f for f in CATALOG if f.id == fid), None)