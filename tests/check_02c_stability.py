from statistics import median
from collections import Counter
from sample_app.db import DB
from sample_app.order_service import build_order_report, build_order_report_fixed
from telemetry.multiscale_sweep import build, log_spaced, timed_sweep
from complexity.symbolic_regressor import fit, _loglog_exponent

DB.seed(6000, 1)
for label, fn in [("nested join", build_order_report), ("FIXED", build_order_report_fixed)]:
    classes, exps = [], []
    for trial in range(5):
        rows = timed_sweep(fn, log_spaced(20, 4000, 9), repeats=5, warmup=2)
        d = build(rows, "elapsed_s")
        law = fit(d, use_pysr=False)
        classes.append(law.complexity_class)
        exps.append(_loglog_exponent(d))
    print(f"\n{label}")
    print(f"  classes over 5 trials: {Counter(classes).most_common()}")
    print(f"  exponents: {[round(e, 2) for e in exps]}  median={median(exps):.2f}")
    print("  STABLE" if len(set(classes)) == 1 else "  UNSTABLE - noise is flipping the class")
