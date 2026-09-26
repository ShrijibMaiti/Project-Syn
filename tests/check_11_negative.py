"""Re-run the correct-negative with the evidence test and an ADEQUATE range.

FakeDB's latency DOES rise with concurrency (queue_penalty in _tick is linear in
inflight) -- that is sigma, not kappa. The old point-estimate fitter absorbed
that linear growth into the quadratic term and returned REFUSE. The F-test should
now attribute it to sigma and return OK."""
from sample_app.db import DB
from stability.capacity_curve import measure_latency_curve, fit_capacity, verdict

DB.seed(2000, 1)
levels = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 192, 224, 256]
rows = measure_latency_curve(lambda: DB.query_items(1), levels,
                             samples_per_level=60, repeats=3)

print("MEASURED:")
for r in rows:
    print(f"   n={r["n"]:>5.0f}  R={r["R"]*1000:>8.3f}ms  tp={r["throughput"]:>9.0f}/s"
          f"  spread={r["spread"]:.2f}")

f = fit_capacity(rows)
print(f"\nsigma={f.sigma:.5f}  kappa={f.kappa:.3e}  CI=[{f.kappa_ci[0]:.1e},{f.kappa_ci[1]:.1e}]")
print(f"p-value={f.p_value:.5f}   R^2={f.r2:.4f}")
print(f"levels={f.n_levels}  n_max={f.n_max}  adequate={f.adequate_measurement}")
print(f"EVIDENCE for coherency: {f.evidence}")
print(f"note: {f.note}")

v, why = verdict(f, 1000.0)
print(f"\nVERDICT: {v.value} -- {why}")
