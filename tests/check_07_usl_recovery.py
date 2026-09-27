"""Does the fitter recover a KNOWN kappa? If not, nothing downstream is trustworthy.

Synthetic USL curves with a known kappa, fitted with the gate's own fitter.
Expect: clean data recovers kappa closely at every magnitude the sweep can
resolve. With 5% noise, small kappa is lost while R^2 stays 0.99+ -- which is
why SYN decides on the nested F-test, never on R^2.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from stability.capacity_curve import fit_capacity, usl_latency  # noqa: E402

NS = np.array([1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 256], float)
rng = np.random.default_rng(0)
checks = []

print(f"{'true kappa':>11}{'noise':>7}{'fit kappa':>12}{'rel err':>9}{'R^2':>8}{'p':>10}  evidence  peak")
for true_k in [0.0, 1e-5, 1e-4, 1e-3, 1e-2]:
    for noise in [0.0, 0.05]:
        Rt = usl_latency(NS, 0.002, 0.05, true_k)
        Rs = Rt * (1 + noise * rng.standard_normal(len(NS)))
        f = fit_capacity([{"n": float(n), "R": float(r)} for n, r in zip(NS, Rs)])
        rel = None if true_k == 0 else abs(f.kappa - true_k) / true_k
        err = "n/a" if rel is None else f"{rel * 100:.1f}%"
        peak = f"N={f.peak_n:.0f}" if f.peak_n else "none"
        print(f"{true_k:>11.0e}{noise:>7.0%}{f.kappa:>12.3e}{err:>9}{f.r2:>8.4f}"
              f"{f.p_value:>10.1e}  {str(f.evidence):<8}  {peak}")
        if noise == 0.0:
            if true_k == 0.0:
                checks.append(("kappa=0, clean: no coherency evidence", not f.evidence))
            elif true_k >= 1e-4:
                checks.append((f"kappa={true_k:.0e}, clean: recovered within 5%", rel < 0.05))

print()
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
ok = all(ok for _, ok in checks)
print("\nKAPPA RECOVERY:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
