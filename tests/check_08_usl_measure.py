"""A sweep too narrow to decide must say so -- never PASS by default.

Measures the live FakeDB over only 10 concurrency levels up to N=64. FakeDB has
no coherency cost, so a PASS would even be the "right" answer -- but a sweep
this narrow cannot distinguish a small kappa from zero, so the gate must return
UNKNOWN (insufficient evidence), not OK. check_11 repeats the measurement over
an adequate sweep (18 levels to N=256) and reaches a real verdict.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sample_app.db import DB  # noqa: E402
from shared.types import RiskLevel  # noqa: E402
from stability.capacity_curve import fit_capacity, measure_latency_curve, verdict  # noqa: E402

DB.seed(2000, 1)
levels = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]
rows = measure_latency_curve(lambda: DB.query_items(1), levels, samples_per_level=60)

print("MEASURED latency vs concurrency (no collapse induced):")
for r in rows:
    print(f"   N={r['n']:>4.0f}  R={r['R'] * 1000:>8.3f}ms  throughput={r['throughput']:>8.0f}/s")

f = fit_capacity(rows)
print(f"\nFITTED USL: base={f.base * 1000:.3f}ms  sigma={f.sigma:.4f}  kappa={f.kappa:.3e}")
print(f"  levels={f.n_levels}  N_max={f.n_max}  adequate={f.adequate_measurement}  p={f.p_value:.2e}")
v, why = verdict(f, 100.0)
print(f"\nVERDICT: {v.value} -- {why}\n")

checks = [("sweep is flagged inadequate (< 16 levels / N_max < 256)", not f.adequate_measurement),
          ("gate answers UNKNOWN, not PASS", v is RiskLevel.UNKNOWN)]
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
ok = all(ok for _, ok in checks)
print("\nNARROW SWEEP -> UNKNOWN:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
