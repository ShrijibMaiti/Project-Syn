"""Measure this machine's harness noise floor, then re-read check_11 against it."""
from stability.harness_calibration import calibrate, exceeds_floor

floor, fit, rows = calibrate()
print("HARNESS CALIBRATION (a no-op target, zero coherency by construction)")
for r in rows:
    print(f"   n={r["n"]:>5.0f}  R={r["R"]*1000:>8.3f}ms  tp={r["throughput"]:>9.0f}/s"
          f"  spread={r["spread"]:.2f}")
print(f"\nharness kappa={fit.kappa:.3e}  p={fit.p_value:.5f}  evidence={fit.evidence}")
print(f"NOISE FLOOR = {floor:.3e}")
if floor > 0:
    print("\n  The harness itself shows coherency above ~100 threads (OS scheduler).")
    print("  Targets must exceed this floor by 10x to count as a real trap.")

print("\nRe-reading measured targets against the floor:")
for name, k in [("FakeDB (should be CLEAN)", 5.35e-05),
                ("ContendedDB (should be FAULTY)", 1.13e-02)]:
    verdict = "REAL TRAP" if exceeds_floor(k, floor) else "indistinguishable from harness noise"
    print(f"  {name:<32} kappa={k:.2e}  -> {verdict}")
