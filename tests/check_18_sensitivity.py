"""Sensitivity engine: every counterfactual is the REAL gate's answer.

1. Agreement: the engine's verdict equals capacity_curve.verdict() at every
   load -- 1,750 loads across five laws, including a dense band around peak.
2. Levers flip the gate: at the kappa / load the engine quotes, the real gate
   changes its answer; just past it, it does not.
3. Above capacity is a REFUSAL (the gate used to PASS it).
4. The plan respects concurrence escalation: two WARNs are REFUSED, so lifting
   that refusal needs one lens to reach PASS.
Runs in seconds -- synthetic laws, no load generated.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from analysis.sensitivity import gate_state, peak, plan, stability_sensitivity  # noqa: E402
from shared.types import RiskLevel  # noqa: E402
from stability.capacity_curve import CapacityFit, verdict  # noqa: E402

LAWS = [(0.01, 0.0, 9.8e-3), (0.0104, 0.0, 8.13e-3), (0.008, 0.02, 1.5e-4),
        (0.005, 0.1, 2e-3), (0.01, 0.3, 5e-4)]


def grid_peak(base, sigma, kappa):
    g = np.arange(1, 200000, dtype=float)
    C = g / (base * (1 + sigma * (g - 1) + kappa * g * (g - 1)))
    i = int(np.argmax(C))
    return float(g[i]), float(C[i])


def fit_of(base, sigma, kappa):
    pn, pt = grid_peak(base, sigma, kappa)
    return CapacityFit(base, sigma, kappa, (0, 0), 1e-6, 0.99, 256, 20, True, True, pn, pt, "")


checks = []

# 1. agreement ---------------------------------------------------------------
total = mismatch = 0
for base, sigma, kappa in LAWS:
    fit = fit_of(base, sigma, kappa)
    cap = fit.peak_throughput
    for frac in np.concatenate([np.linspace(0.02, 1.3, 300), np.linspace(0.995, 1.005, 50)]):
        L = cap * frac
        g, _ = verdict(fit, L, kappa_floor=0)
        total += 1
        mismatch += g.value != gate_state(L, base, sigma, kappa, cap)["verdict"]
print(f"agreement: {total} loads, {mismatch} disagreements with the gate")
checks.append(("engine verdict == gate verdict at every load", mismatch == 0))

# 2. levers flip the gate ----------------------------------------------------
base, sigma, kappa, load = 0.0104, 0.0, 8.13e-3, 477.0
pn, pt = grid_peak(base, sigma, kappa)
ev = {"target": "db_access", "base": base, "sigma": sigma, "kappa": kappa,
      "evidence": True, "adequate": True, "exceeds_floor": True, "kappa_floor": 2.254e-5,
      "operating_load": load, "peak_throughput": pt, "peak_n": pn}
s = stability_sensitivity(ev, "refuse")
print(f"faulty-shaped run: gate now {s['now']['verdict']} at headroom {s['now']['headroom']:.2f}")


def gate_at_kappa(k):
    return verdict(fit_of(base, sigma, k), load, kappa_floor=0)[0]


def gate_at_load(L):
    return verdict(fit_of(base, sigma, kappa), L, kappa_floor=0)[0]


k_lift = s["levers"]["kappa"]["to_lift_refusal"]["kappa"]
k_pass = s["levers"]["kappa"]["to_pass"]["kappa"]
L_lift = s["levers"]["load"]["to_lift_refusal"]["load"]
L_pass = s["levers"]["load"]["to_pass"]["load"]
print(f"  kappa to lift refusal {k_lift:.3e}: gate {gate_at_kappa(k_lift * 0.999).value}"
      f" / just above {gate_at_kappa(k_lift * 1.02).value}")
print(f"  kappa to pass         {k_pass:.3e}: gate {gate_at_kappa(k_pass * 0.999).value}"
      f" / just above {gate_at_kappa(k_pass * 1.02).value}")
print(f"  load to lift refusal  {L_lift:.1f}/s: gate {gate_at_load(L_lift * 0.999).value}"
      f" / just above {gate_at_load(L_lift * 1.01).value}")
print(f"  load to pass          {L_pass:.1f}/s: gate {gate_at_load(L_pass * 0.999).value}"
      f" / just above {gate_at_load(L_pass * 1.01).value}")
checks += [
    ("kappa lever lifts the refusal exactly at the quoted value",
     gate_at_kappa(k_lift * 0.999) is not RiskLevel.REFUSE
     and gate_at_kappa(k_lift * 1.02) is RiskLevel.REFUSE),
    ("kappa lever passes exactly at the quoted value",
     gate_at_kappa(k_pass * 0.999) is RiskLevel.OK and gate_at_kappa(k_pass * 1.02) is not RiskLevel.OK),
    ("load lever lifts the refusal exactly at the quoted value",
     gate_at_load(L_lift * 0.999) is not RiskLevel.REFUSE
     and gate_at_load(L_lift * 1.01) is RiskLevel.REFUSE),
    ("load lever passes exactly at the quoted value",
     gate_at_load(L_pass * 0.999) is RiskLevel.OK and gate_at_load(L_pass * 1.01) is not RiskLevel.OK),
]

# 3. above capacity ----------------------------------------------------------
v_above, why_above = verdict(fit_of(base, sigma, kappa), pt * 1.1, kappa_floor=0)
print(f"load 10% above capacity: {v_above.value} -- {why_above}")
checks.append(("load above peak capacity is REFUSED, not passed", v_above is RiskLevel.REFUSE))

# 4. escalation-aware plan ---------------------------------------------------
p = plan({"complexity": "warn", "stability": "warn"})
lift = [(c["lens"], c["to"]) for c in p["to_lift_refusal"]["changes"]]
print(f"plan for WARN+WARN (escalated to {p['current']}): lift via {lift}")
checks.append(("two WARNs are REFUSED, and lifting needs a lens to reach PASS",
               p["current"] == "refuse" and any(to == "ok" for _, to in lift)))
checks.append(("an UNKNOWN lens blocks PASS instead of being levered",
               plan({"complexity": "ok", "stability": "unknown"})["to_pass"] is None))

print()
for name, ok in checks:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
print("\nSENSITIVITY ENGINE:", "PASS" if all(ok for _, ok in checks) else "FAIL")
