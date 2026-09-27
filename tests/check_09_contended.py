"""CPU-bound contention under the GIL: the case that taught SYN to sleep.

ContendedService does its coherency work in pure Python, so every request
competes for the GIL. The GIL serialises that work: throughput SATURATES
instead of turning over, so there is no retrograde branch to find, however
strong the coherency term is on paper. That is why the positive testbed models
an EXTERNAL contended resource with a sleep (sample_app.contended_db, check_12).

The sweep stops at N=48: hundreds of CPU-bound threads fighting for the GIL
make the measurement itself crawl. Below the adequacy bar, the gate must answer
UNKNOWN -- the second thing this check verifies.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sample_app.contended import SERVICE  # noqa: E402
from shared.types import RiskLevel  # noqa: E402
from stability.capacity_curve import fit_capacity, measure_latency_curve, verdict  # noqa: E402

levels = [1, 2, 4, 6, 8, 12, 16, 24, 32, 48]
rows = measure_latency_curve(SERVICE.handle, levels, samples_per_level=40, repeats=2)

print("MEASURED (CPU-bound contended service):")
for r in rows:
    print(f"   N={r['n']:>4.0f}  R={r['R'] * 1000:>8.3f}ms  throughput={r['throughput']:>8.0f}/s")

f = fit_capacity(rows)
peak = f"fitted peak {f.peak_throughput:.0f}/s at N={f.peak_n:.0f}" if f.peak_n else "no fitted peak"
print(f"\nkappa={f.kappa:.3e}  p={f.p_value:.2e}  R^2={f.r2:.4f}  {peak}")
v, why = verdict(f, 100.0)
print(f"VERDICT: {v.value} -- {why}\n")

tp = [r["throughput"] for r in rows]
checks = [("throughput saturates rather than collapsing (last level >= 50% of max)",
           tp[-1] >= 0.5 * max(tp)),
          ("narrow sweep -> gate answers UNKNOWN, not PASS", v is RiskLevel.UNKNOWN)]
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
ok = all(ok for _, ok in checks)
print("\nGIL SATURATION + NARROW SWEEP:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
