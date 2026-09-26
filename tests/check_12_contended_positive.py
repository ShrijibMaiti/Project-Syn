"""POSITIVE CASE: a service WITH coherency cost. The counterpart to check_11.

check_11 (FakeDB, no coherency)  -> evidence=False, verdict ok
check_12 (ContendedDB, kappa>0)  -> evidence=True,  headroom collapses to refuse

Together they show the detector discriminates rather than always firing.
Expect ~5-8 minutes: latency at n=256 is multiple seconds by design."""
from sample_app.contended_db import CONTENDED_DB as db
from stability.capacity_curve import (measure_latency_curve, fit_capacity,
                                      analyse_trap, verdict)

levels = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 256]
rows = measure_latency_curve(db.call, levels, samples_per_level=40, repeats=3)

print("MEASURED (retrograde by construction):")
for r in rows:
    print(f"   n={r["n"]:>5.0f}  R={r["R"]*1000:>10.2f}ms  tp={r["throughput"]:>8.1f}/s"
          f"  spread={r["spread"]:.2f}")

peak = max(rows, key=lambda r: r["throughput"])
print(f"\nRAW peak throughput {peak["throughput"]:.1f}/s at n={peak["n"]:.0f}"
      f"   (theoretical n={db.theoretical_peak_n:.1f})")
print(f"collapsed to {rows[-1]["throughput"]:.1f}/s at n={rows[-1]["n"]:.0f}"
      f"  -- retrograde is visible in the RAW DATA, before any fitting")

f = fit_capacity(rows)
print(f"\nsigma={f.sigma:.5f}  kappa={f.kappa:.4e}  CI=[{f.kappa_ci[0]:.2e},{f.kappa_ci[1]:.2e}]")
print(f"  true kappa = {db.coherency_k/db.base_s:.4e}   (coherency_k / base_s)")
print(f"p-value={f.p_value:.2e}  R^2={f.r2:.4f}  levels={f.n_levels}  n_max={f.n_max}")
print(f"adequate={f.adequate_measurement}   EVIDENCE={f.evidence}")
print(f"note: {f.note}")

if f.evidence and f.peak_n:
    print(f"\nfitted peak {f.peak_throughput:.1f}/s at n={f.peak_n:.0f}")
    print(f"\n{"load":>9}{"healthy":>10}{"separatrix":>12}{"headroom":>10}  verdict")
    for frac in [0.3, 0.5, 0.7, 0.85, 0.95]:
        lam = frac * f.peak_throughput
        t = analyse_trap(f, lam)
        v, _ = verdict(f, lam)
        if t.bistable:
            print(f"{lam:>9.1f}{t.healthy_n:>10.1f}{t.separatrix:>12.1f}"
                  f"{t.headroom:>10.2f}  {v.value}")
