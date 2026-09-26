import time
from sample_app.db import DB
from sample_app.order_service import build_order_report, build_order_report_fixed
from telemetry.multiscale_sweep import build, log_spaced
from complexity.symbolic_regressor import fit

DB.seed(6000, 1)
for label, fn in [("nested join", build_order_report), ("FIXED", build_order_report_fixed)]:
    rows = []
    for n in log_spaced(20, 4000, 9):
        DB.reset_counters()
        t0 = time.perf_counter()
        fn(n)
        rows.append({"n": float(n), "elapsed_s": time.perf_counter() - t0})
    law = fit(build(rows, "elapsed_s"), use_pysr=False)
    print(f"\n{label}: {law.complexity_class}  conf={law.confidence:.2f}")
    print(f"  law:  {law.expression}")
    print(f"  note: {law.note}")
    print(f"  n=1e6 -> {law.evaluate(1e6):,.1f}s")
