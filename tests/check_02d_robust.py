from sample_app.db import DB
from sample_app.order_service import build_order_report, build_order_report_fixed
from telemetry.multiscale_sweep import robust_class, log_spaced

DB.seed(60000, 1)
print("=== standard sweep (20..4000) ===")
for label, fn in [("nested join", build_order_report), ("FIXED", build_order_report_fixed)]:
    r = robust_class(fn, log_spaced(20, 4000, 9), trials=5)
    lo, hi = r["interval"]
    print(f"{label:<13} exp={r['exponent']:.2f} [{lo:.2f},{hi:.2f}]  "
          f"class={r['class']:<10} superlinear={r['superlinear']}  {r['note']}")

print("\n=== wide sweep for FIXED (200..50000) ===")
r = robust_class(build_order_report_fixed, log_spaced(200, 50000, 10), trials=3)
lo, hi = r["interval"]
print(f"{'FIXED wide':<13} exp={r['exponent']:.2f} [{lo:.2f},{hi:.2f}]  "
      f"class={r['class']:<10} superlinear={r['superlinear']}  {r['note']}")
