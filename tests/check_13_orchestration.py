"""THE END-TO-END TEST: both lenses, both faults, one verdict.

ASSERTS DETECTION, NOT SEVERITY. Severity depends on `operating_load`, a deployment
fact SYN does not know (it defaults to 0.85*peak). The invariant that matters is:
faulty target -> both lenses flag it; fixed target -> both lenses clear it."""
import time
from sample_app.db import DB
from sample_app.order_service import build_order_report, build_order_report_fixed
from sample_app.contended_db import ContendedDB
from orchestration.targets import ComplexityTarget, StabilityTarget, ProbeManifest
from orchestration.main_agent import MainAgent

DB.seed(20000, 1)
faulty_db = ContendedDB()
clean_db = ContendedDB(coherency_k=0.0)
LEVELS = [1, 2, 3, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 200, 256]


def run(label, comp_fn, stab_db, operating_frac=0.95):
    m = ProbeManifest(
        complexity=[ComplexityTarget("order_report", comp_fn,
                                     n_min=50, n_max=12000, points=10)],
        stability=[StabilityTarget("db_access", stab_db.call, levels=LEVELS,
                                   samples_per_level=25, repeats=2)])
    agent = MainAgent(m, serialize=True)
    t0 = time.time()
    v, ctx = agent.run(commit=label)
    print(f"\n{"="*70}\n{label}  ->  {v.risk.value.upper()}   ({time.time()-t0:.0f}s)")
    for r in v.reasons:
        print("   " + r)
    return v, ctx, agent


v1, c1, a1 = run("FAULTY (nested join + coherency)", build_order_report, faulty_db)
v2, c2, a2 = run("FIXED  (indexed join + no coherency)", build_order_report_fixed, clean_db)

print("\n" + "=" * 70)
print(a1.certificate(v1, c1))

# --- the invariants that actually matter ---
fc = v1.evidence["complexity"][0]
fs = v1.evidence["stability"][0]
kc = v2.evidence["complexity"][0]
ks = v2.evidence["stability"][0]

checks = [
    ("faulty: complexity flags superlinear", fc.get("superlinear") is True),
    ("faulty: stability finds coherency",    fs.get("evidence") is True),
    ("fixed:  complexity NOT superlinear",   kc.get("superlinear") is not True),
    ("fixed:  stability finds NO coherency", ks.get("evidence") is not True),
    ("faulty verdict is worse than fixed",   v1.risk.value != "ok" and v2.risk.value == "ok"),
]
print()
for name, passed in checks:
    print(f"  [{"PASS" if passed else "FAIL"}] {name}")
print(f"\nfaulty exponent={fc.get("exponent")}  kappa={fs.get("kappa"):.2e}"
      f"   |   fixed exponent={kc.get("exponent")}  p={ks.get("p_value"):.3f}")
print(f"\nOVERALL: {"PASS" if all(p for _, p in checks) else "FAIL"}")
