"""PLANTED FAULT 2 -- algorithmic detonation, two distinct shapes.

VERIFIED (R^2 = 1.0000 on a 2.4-decade sweep):
  list_orders_with_items -> O(n) in time AND db_calls   (N+1: round-trip bound)
  build_order_report     -> O(n^2) in time, O(1) db_calls (nested join: compute bound)

N+1 is NOT quadratic -- it is n round trips instead of one. Calling it O(n^2) is a
common and catchable error; the metric you measure determines the law you recover.
"""
from __future__ import annotations
from typing import List

from sample_app.db import DB
from sample_app.retry_loop import call_with_retries
# The probes import this module and call these functions directly, with no test
# harness to set up state. An unseeded DB makes every complexity measurement
# flat: cost is constant in n, the exponent reads ~0, and the verdict is
# meaningless. Seed on import so every entry point (ci_gate, run_and_store,
# tests) measures a real table.
if not DB.orders:
    DB.seed(20000, 1)


def list_orders_with_items(n: int) -> List[dict]:
    """FAULT 2a -- N+1 queries. O(n) round trips; detonates against the CONNECTION
    POOL ceiling (pool-bound: raising the pool moves the crossing)."""
    orders = DB.query_orders(n)
    return [{**o, "items": DB.query_items(o["id"])} for o in orders]


def build_order_report(n: int) -> List[dict]:
    """FAULT 2b -- nested-loop join with no index. O(n^2) CPU; detonates against the
    REQUEST TIMEOUT / CPU budget (compute-bound: more RAM does not move it)."""
    orders = DB.query_orders(n)
    all_items = DB.query_all_items(n)
    report = []
    for o in orders:                                                   # n
        matched = [it for it in all_items if it["order_id"] == o["id"]]  # x n
        report.append({**o, "items": matched})
    return report


def build_order_report_fixed(n: int) -> List[dict]:
    """The FIXED version: index once, then O(n) lookup. For the false-positive test."""
    orders = DB.query_orders(n)
    index: dict = {}
    for it in DB.query_all_items(n):
        index.setdefault(it["order_id"], []).append(it)
    return [{**o, "items": index.get(o["id"], [])} for o in orders]


def order_with_retries(order_id: int) -> List[dict]:
    """The path that couples FAULT 1 to the DB -- the retry storm's entry point."""
    return call_with_retries(DB.query_items, order_id)