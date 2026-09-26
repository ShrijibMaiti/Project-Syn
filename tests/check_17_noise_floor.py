"""The gate APPLIES the instrument's noise floor -- not just displays it.

Synthetic sweeps shaped like measured runs, so this runs in seconds:
  - FakeDB-like: kappa ~5e-5, statistically real (the F-test accepts it), but
    ~2x the calibrated floor. Must be dismissed BY THE FLOOR -- and must NOT be
    passed merely because an operating load happened to leave no separatrix.
  - Faulty: kappa ~1e-2, ~400x the floor. Must be untouched.
  - No floor known: behaviour identical to before calibration existed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from shared.types import RiskLevel  # noqa: E402
from stability.capacity_curve import fit_capacity, usl_latency, verdict  # noqa: E402

LEVELS = [1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 192, 224, 256]
FLOOR = 2.254e-05   # measured: no-op target through the identical sweep


def sweep(base, sigma, kappa, seed):
    r = np.random.default_rng(seed)
    return [{"n": float(n), "R": float(usl_latency(n, base, sigma, kappa) * (1 + r.normal(0, 0.02))),
             "throughput": 0.0} for n in LEVELS]


fakedb = fit_capacity(sweep(6e-4, 0.004, 5.06e-5, 3))
faulty = fit_capacity(sweep(0.01, 0.0, 9.8e-3, 1))

# The probe's own default operating load: 85% of fitted peak throughput. At this
# load a genuine trap is close, so WITHOUT the floor the FakeDB kappa is reported
# as a real risk -- which is exactly the false positive the floor exists to stop.
load = 0.85 * fakedb.peak_throughput
checks = []
v, why = verdict(fakedb, load=load, kappa_floor=FLOOR)
checks.append(("F-test alone accepts the FakeDB kappa", fakedb.evidence))
checks.append(("floor dismisses FakeDB even where a trap would otherwise be found",
               v is RiskLevel.OK and "noise floor" in why))
v0, why0 = verdict(fakedb, load=load, kappa_floor=0)
checks.append(("without the floor, that same case would NOT pass", v0 is not RiskLevel.OK))
vf, whyf = verdict(faulty, load=450.0, kappa_floor=FLOOR)
checks.append(("faulty target still flagged with the floor applied",
               vf in (RiskLevel.WARN, RiskLevel.REFUSE)))
print(f"FakeDB kappa={fakedb.kappa:.2e} ({fakedb.kappa / FLOOR:.1f}x floor), load {load:.0f}/s  ->  {v.value}: {why}")
print(f"  (same load, no floor  ->  {v0.value}: {why0})")
print(f"Faulty kappa={faulty.kappa:.2e} ({faulty.kappa / FLOOR:.0f}x floor)  ->  {vf.value}: {whyf}\n")

for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print("\nNOISE FLOOR ENFORCED:", "PASS" if all(ok for _, ok in checks) else "FAIL")
