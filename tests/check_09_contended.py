"""Positive case: measure a service WITH coherency cost. Expect kappa > 0,
trustworthy, and a separatrix that shrinks as load rises."""
from sample_app.contended import SERVICE
from stability.capacity_curve import (measure_latency_curve, fit_capacity,
                                      analyse_trap, verdict)

levels = [1, 2, 4, 6, 8, 12, 16, 24, 32, 48]
rows = measure_latency_curve(SERVICE.handle, levels, samples_per_level=60)

print("MEASURED (contended service):")
for r in rows:
    print(f"   n={r["n"]:>4.0f}  R={r["R"]*1000:>8.3f}ms  throughput={r["throughput"]:>8.0f}/s")

f = fit_capacity(rows)
print(f"\nkappa={f.kappa:.3e}  floor={f.kappa_min:.2e}  R^2={f.r2:.4f}")
print(f"retrograde={f.retrograde}  trustworthy={f.trustworthy}")
print(f"note: {f.note}")

if f.retrograde and f.peak_n:
    print(f"peak {f.peak_throughput:.0f}/s at n={f.peak_n:.0f}")
    print(f"\n{"load":>9}{"healthy":>10}{"separatrix":>12}{"headroom":>10}  verdict")
    for frac in [0.3, 0.5, 0.7, 0.85, 0.95]:
        lam = frac * f.peak_throughput
        t = analyse_trap(f, lam)
        v, _ = verdict(f, lam)
        if t.bistable:
            print(f"{lam:>9.0f}{t.healthy_n:>10.1f}{t.separatrix:>12.1f}"
                  f"{t.headroom:>10.2f}  {v.value}")
