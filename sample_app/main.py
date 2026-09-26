"""The real system under test. SYN's telemetry comes from instrumenting THIS --
never from the Twin's own output. That separation is the anti-circularity guarantee.

Run:  uvicorn sample_app.main:app --port 8001
"""
from __future__ import annotations
import time

from fastapi import FastAPI, Query

from sample_app.checkout import checkout as run_checkout
from sample_app.db import DB
from sample_app.order_service import (build_order_report, build_order_report_fixed,
                                      list_orders_with_items, order_with_retries)
from sample_app.retry_loop import STATS

app = FastAPI(title="sample-app", description="System under test — contains planted faults")
STARTED = time.time()


@app.on_event("startup")
def _startup() -> None:
    DB.seed(n_orders=20000, items_per_order=1)


@app.get("/metrics")
def metrics():
    """The order-parameter stream. Matches shared/order_state.schema.json.
    NOTE: these are MACROSCOPIC aggregates of fixed dimension -- never per-thread state."""
    s = STATS.snapshot()
    return {"queue_depth": float(DB.inflight),
            "retry_rate": float(s["retry_rate"]),
            "error_rate": float(s["error_rate"]),
            "cache_hit_ratio": 0.0,
            "inflight": float(DB.inflight),
            "db_calls": float(DB.calls),
            "pool_size": float(DB.pool_size),
            "t": time.time() - STARTED}


@app.get("/work")
def work(n: int = Query(default=100, ge=1, le=200000),
         path: str = Query(default="report")):
    """The multiscale sweep hits this. `path` selects which planted fault to exercise."""
    DB.reset_counters()
    t0 = time.perf_counter()
    if path == "n_plus_one":
        rows = list_orders_with_items(n)
    elif path == "fixed":
        rows = build_order_report_fixed(n)
    else:
        rows = build_order_report(n)
    return {"n": n, "path": path, "rows": len(rows),
            "elapsed_s": time.perf_counter() - t0,
            "db_calls": DB.calls, "ops": len(rows)}


@app.post("/checkout")
def checkout(n: int = Query(default=50, ge=1, le=20000)):
    """Checkout path gated by SYN in CI (syn.ci.json)."""
    t0 = time.perf_counter()
    rows = run_checkout(n)
    return {"n": n, "rows": len(rows), "elapsed_s": time.perf_counter() - t0}


@app.get("/order/{order_id}")
def order(order_id: int):
    """Exercises the retry loop -- the metastable path."""
    try:
        return {"items": order_with_retries(order_id)}
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/trigger")
def trigger(seconds: float = 2.0):
    """Fire the TRANSIENT trigger. A healthy system recovers when it passes;
    a metastable one does not. That difference is the whole experiment."""
    DB.degrade(seconds)
    return {"degraded_for": seconds}


@app.post("/reset")
def reset():
    DB.reset_counters()
    STATS.reset()
    DB.degraded_until = 0.0
    return {"status": "reset"}