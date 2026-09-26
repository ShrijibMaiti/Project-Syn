"""Does the fitter recover a KNOWN kappa? If not, nothing downstream is trustworthy.

Expect: clean data recovers kappa exactly at every magnitude. With 5% noise,
small kappa is MISSED while R^2 stays 0.99+ -- R^2 is not a validity check.
"""
import numpy as np
from stability.capacity_curve import fit_capacity, usl_latency

ns = np.array([1, 2, 4, 8, 12, 16, 24, 32, 48, 64], float)
rng = np.random.default_rng(0)

print(f"{"true kappa":>11}{"noise":>7}{"fit kappa":>12}{"rel err":>9}{"R^2":>8}{"trust":>7}  retrograde?")
for true_k in [0.0, 1e-5, 1e-4, 1e-3, 1e-2]:
    for noise in [0.0, 0.05]:
        Rt = usl_latency(ns, 0.002, 0.05, true_k)
        Rs = Rt * (1 + noise * rng.standard_normal(len(ns)))
        rows = [{"n": float(n), "R": float(r)} for n, r in zip(ns, Rs)]
        f = fit_capacity(rows)
        err = "n/a" if true_k == 0 else f"{abs(f.kappa - true_k) / true_k * 100:.1f}%"
        print(f"{true_k:>11.0e}{noise:>7.0%}{f.kappa:>12.3e}{err:>9}{f.r2:>8.4f}"
              f"{str(f.trustworthy):>7}  {"YES n=%.0f" % f.peak_n if f.peak_n else "no"}")

print("\n--- detectability rule: kappa_min ~ sigma / n_max ---")
for nmax in [64, 256, 1024]:
    grid = np.unique(np.round(np.logspace(0, np.log10(nmax), 12)).astype(float))
    line = f"n_max={nmax:>5}  floor={0.05/nmax:.1e}  "
    for true_k in [1e-5, 1e-4, 1e-3]:
        Rs = usl_latency(grid, 0.002, 0.05, true_k) * (1 + 0.05 * rng.standard_normal(len(grid)))
        f = fit_capacity([{"n": float(n), "R": float(r)} for n, r in zip(grid, Rs)])
        ok = abs(f.kappa - true_k) / true_k < 0.5
        line += f"k={true_k:.0e}:{"OK " if ok else "MISS"}  "
    print(line)
