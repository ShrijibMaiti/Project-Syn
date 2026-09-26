"""Checkout: the code SYN gates in CI (manifest: syn.ci.json).

This module is the "Try it" surface. It ships HEALTHY, so the gate passes on
main. Each fault is ONE line away -- open a pull request that makes either
change and the SYN gate refuses to merge it, with a certificate on the PR.

  TRY IT (stability lens) -- give the checkout database a coherency cost:
      CHECKOUT_DB = ContendedDB(coherency_k=0.0)
   -> CHECKOUT_DB = ContendedDB(coherency_k=1e-4)

  TRY IT (complexity lens) -- swap the indexed report for the nested-loop one:
      return build_order_report_fixed(n)
   -> return build_order_report(n)
"""
from __future__ import annotations

from sample_app.contended_db import ContendedDB
from sample_app.order_service import build_order_report, build_order_report_fixed  # noqa: F401

# Every checkout writes one shared row. coherency_k is the per-waiter cost of
# keeping that row consistent; 0.0 means concurrent checkouts do not interfere.
CHECKOUT_DB = ContendedDB(coherency_k=0.0)


def monthly_report(n: int):
    """Join n orders to their items for the monthly checkout report."""
    return build_order_report_fixed(n)


def checkout(n: int = 50):
    """One checkout: commit the order row, then refresh the report."""
    CHECKOUT_DB.call()
    return monthly_report(n)
