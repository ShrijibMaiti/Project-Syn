"""Ground-truth validation of the evidence test. This is the gate on everything
downstream: if the F-test cannot separate linear growth from quadratic, every
verdict is suspect.

Expect 6/6 correct on the adequate config, and FALSE on both kappa=0 rows --
that is the false positive (check_08) being fixed."""
import numpy as np
from stability.capacity_curve import fit_capacity, usl_latency

rng = np.random.default_rng(7)
cases = [("sigma=0.05 kappa=0", 0.05, 0.0), ("sigma=0.50 kappa=0", 0.50, 0.0),
         ("sigma=0.05 kappa=1e-4", 0.05, 1e-4), ("sigma=0.05 kappa=1e-3", 0.05, 1e-3),
         ("sigma=0.50 kappa=1e-3", 0.50, 1e-3), ("sigma=0.05 kappa=1e-2", 0.05, 1e-2)]

for label, npts, nmax, reps in [("NARROW  10 levels n<=64", 10, 64, 1),
                                ("ADEQUATE 18 levels n<=256 x5", 18, 256, 5)]:
    ns = np.unique(np.round(np.logspace(0, np.log10(nmax), npts)).astype(float))
    print(f"\n--- {label} ---")
    print(f"{"truth":<24}{"kappa_fit":>11}{"p-value":>11}{"adequate":>10}  evidence?  correct?")
    score = 0
    for lbl, s, k in cases:
        Rt = usl_latency(ns, 0.002, s, k)
        Rs = np.mean([Rt * (1 + 0.05 * rng.standard_normal(len(ns))) for _ in range(reps)], axis=0)
        f = fit_capacity([{"n": float(n), "R": float(r)} for n, r in zip(ns, Rs)])
        ok = (f.evidence == (k > 0))
        score += ok
        print(f"{lbl:<24}{f.kappa:>11.2e}{f.p_value:>11.5f}{str(f.adequate_measurement):>10}"
              f"  {"YES" if f.evidence else "no ":<9}  {"OK" if ok else "** WRONG **"}")
    print(f"  score: {score}/{len(cases)}")
