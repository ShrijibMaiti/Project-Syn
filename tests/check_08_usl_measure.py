"""Measure the capacity curve on the live sample_app, fit USL, render a verdict.

EXPECTED RESULT: kappa ~ 0. FakeDB is a sleep behind a lock with no coherency
cost, so no trap exists and SYN must SAY SO rather than invent a cliff. This is
the correct-negative test.
"""
from sample_app.db import DB
from stability.capacity_curve import (measure_latency_curve, fit_capacity,
                                      analyse_trap, verdict)

DB.seed(2000, 1)
levels = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64]
rows = measure_latency_curve(lambda: DB.query_items(1), levels, samples_per_level=80)

print("MEASURED latency vs concurrency (no collapse induced):")
for r in rows:
    print(f"   n={r["n"]:>4.0f}  R={r["R"]*1000:>8.3f}ms  p90={r["R_p90"]*1000:>8.3f}ms"
          f"  throughput={r["throughput"]:>8.0f}/s")

f = fit_capacity(rows)
print(f"\nFITTED USL: base={f.base*1000:.3f}ms  sigma={f.sigma:.4f}  kappa={f.kappa:.3e}")
print(f"  R^2={f.r2:.4f}   detectability floor kappa_min={f.kappa_min:.2e}")
print(f"  retrograde={f.retrograde}  trustworthy={f.trustworthy}")
print(f"  note: {f.note}")

if f.retrograde and f.peak_n:
    print(f"  peak throughput {f.peak_throughput:.0f}/s at n={f.peak_n:.0f}")
    print(f"\n{"load":>9}{"healthy":>10}{"separatrix":>12}{"headroom":>10}  verdict")
    for frac in [0.3, 0.5, 0.7, 0.85, 0.95]:
        lam = frac * f.peak_throughput
        t = analyse_trap(f, lam)
        v, why = verdict(f, lam)
        if t.bistable:
            print(f"{lam:>9.0f}{t.healthy_n:>10.1f}{t.separatrix:>12.1f}"
                  f"{t.headroom:>10.2f}  {v.value}")
else:
    v, why = verdict(f, 100.0)
    print(f"\nVERDICT: {v.value} -- {why}")
