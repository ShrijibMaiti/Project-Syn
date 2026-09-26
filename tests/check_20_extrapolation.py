"""The gate does not act on a cliff it would have to extrapolate far to find.

Found on a GitHub Actions runner: a flat 10 ms service with no shared state
(blind target s_flat, and the demo-clean CLEAN_DB) fitted kappa ~4e-7 at
p < 0.01 -- scheduler jitter at a few hundred threads -- and the runner's own
no-op calibration showed no evidence, so no noise floor applied. The fitted
"peak" sat at N ~ 1,800 when only N <= 256 was measured, and the gate reported
a trap (a false positive in blind detection, and demo-clean read WARN).

Rule: a trap is gated only if its fitted peak lies within EXTRAPOLATION_LIMIT
(2x) the largest concurrency measured. Synthetic sweeps, runs in seconds:
  - runner-jitter: kappa ~4e-7, evidence True, peak ~1,600  -> OK (beyond range)
  - weak real coherency: kappa ~3.6e-3, peak ~17            -> still flagged
  - faulty: kappa ~1e-2, peak ~10                           -> still flagged
  - kappa ~1e-5 (peak ~316, inside 2x256)                   -> still gated
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from shared.types import RiskLevel  # noqa: E402
from stability.capacity_curve import (EXTRAPOLATION_LIMIT, cliff_in_range,  # noqa: E402
                                      fit_capacity, usl_latency, verdict)
from analysis.sensitivity import stability_sensitivity  # noqa: E402

LEVELS = [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 192, 256]


def sweep(base, sigma, kappa, seed, noise):
    r = np.random.default_rng(seed)
    return [{"n": float(n), "R": float(usl_latency(n, base, sigma, kappa) * (1 + r.normal(0, noise))),
             "throughput": 0.0} for n in LEVELS]


jitter = fit_capacity(sweep(0.010, 0.0, 4e-7, 7, 0.002))
weak = fit_capacity(sweep(0.010, 0.0, 3.6e-3, 2, 0.02))
faulty = fit_capacity(sweep(0.010, 0.0, 1.0e-2, 1, 0.02))
mid = fit_capacity(sweep(0.010, 0.0, 1.0e-5, 4, 0.002))

checks = []
checks.append(("runner jitter passes the F-test (the hazard is real)", jitter.evidence))
vj, whyj = verdict(jitter, load=0.85 * jitter.peak_throughput, kappa_floor=0)
checks.append(("jitter cliff beyond 2x measured N is NOT reported as a trap",
               vj is RiskLevel.OK and "extrapolation" in whyj))
vw, _ = verdict(weak, load=0.85 * weak.peak_throughput, kappa_floor=0)
checks.append(("weak real coherency (peak ~17) is still flagged", vw is not RiskLevel.OK))
vf, _ = verdict(faulty, load=490.0, kappa_floor=0)
checks.append(("faulty checkout (peak ~10) is still REFUSED", vf is RiskLevel.REFUSE))
checks.append(("kappa 1e-5 (peak ~316) stays inside the gated range",
               cliff_in_range(mid.peak_n, mid.n_max)))

# The sensitivity engine agrees with the gate on the rule.
ev = {"target": "jitter", "base": jitter.base, "sigma": jitter.sigma, "kappa": jitter.kappa,
      "evidence": True, "adequate": True, "n_max_measured": jitter.n_max,
      "beyond_range": not cliff_in_range(jitter.peak_n, jitter.n_max)}
checks.append(("sensitivity reports the same case as beyond the measured range",
               stability_sensitivity(ev, "ok")["mode"] == "beyond_range"))

print(f"limit: peak must lie within {EXTRAPOLATION_LIMIT:g}x N_max")
print(f"jitter kappa={jitter.kappa:.2e} p={jitter.p_value:.1e} peak N={jitter.peak_n:.0f}  ->  {vj.value}: {whyj}")
print(f"weak   kappa={weak.kappa:.2e} peak N={weak.peak_n:.0f}  ->  {vw.value}")
print(f"faulty kappa={faulty.kappa:.2e} peak N={faulty.peak_n:.0f}  ->  {vf.value}")
print(f"mid    kappa={mid.kappa:.2e} peak N={mid.peak_n:.0f}\n")
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
ok = all(ok for _, ok in checks)
print("\nEXTRAPOLATION LIMIT ENFORCED:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
