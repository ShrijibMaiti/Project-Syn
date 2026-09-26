import time
from sample_app.db import DB
from sample_app.order_service import (list_orders_with_items, build_order_report,
                                      build_order_report_fixed)
from telemetry.multiscale_sweep import build, log_spaced
from complexity.symbolic_regressor import fit, _loglog_exponent

DB.seed(6000, 1)
cases = [("N+1", list_orders_with_items, "db_calls"),
         ("nested join", build_order_report, "elapsed_s"),
         ("FIXED", build_order_report_fixed, "elapsed_s")]

print(f"{"path":<14}{"class":<12}{"R^2":>8}{"exp":>6}{"conf":>7}")
for label, fn, metric in cases:
    rows = []
    for n in log_spaced(20, 4000, 9):
        DB.reset_counters()
        t0 = time.perf_counter()
        fn(n)
        rows.append({"n": float(n), "elapsed_s": time.perf_counter() - t0,
                     "db_calls": float(DB.calls)})
    d = build(rows, metric)
    law = fit(d, use_pysr=False)
    print(f"{label:<14}{law.complexity_class:<12}{law.r2:>8.4f}"
          f"{_loglog_exponent(d):>6.2f}{law.confidence:>7.2f}")
