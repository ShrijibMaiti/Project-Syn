"""Gate contract test. The exit code IS the product.

  0 = allowed   1 = refused   2 = could not run

Exit 2 must be distinct from 0: a gate that fails to run and returns 0 silently
approves everything, which is worse than having no gate."""
import json
from sample_app.db import DB
from gateway.ci_gate import main

DB.seed(30000, 1)

clean_manifest = {"syn": {
    "complexity": [{"name": "order_report",
                    "target": "sample_app.order_service:build_order_report_fixed",
                    "n_min": 20, "n_max": 20000, "points": 10}],
    "stability": [{"name": "db_access",
                   "target": "sample_app.contended_db:CLEAN_DB.call",
                   "samples_per_level": 25, "repeats": 2}]}}
with open("syn_clean.json", "w") as fh:
    json.dump(clean_manifest, fh)
with open("syn_bad.json", "w") as fh:
    json.dump({"syn": {"complexity": [{"name": "x", "target": "no.such:thing"}]}}, fh)

print("=" * 60, "\nFAULTY target")
faulty = main(["--commit", "test-faulty"])
print("=" * 60, "\nCLEAN target")
clean = main(["--manifest", "syn_clean.json", "--commit", "test-clean"])
print("=" * 60, "\nMISSING manifest")
missing = main(["--manifest", "does_not_exist.json"])
print("=" * 60, "\nBROKEN target reference")
broken = main(["--manifest", "syn_bad.json"])

checks = [("faulty refuses (exit 1)", faulty == 1),
          ("clean allows (exit 0)", clean == 0),
          ("missing manifest errors (exit 2, NOT 0)", missing == 2),
          ("broken reference errors (exit 2, NOT 0)", broken == 2)]
print("\n" + "=" * 60)
for name, ok in checks:
    print(f"  [{"PASS" if ok else "FAIL"}] {name}")
print(f"\nGATE CONTRACT: {"PASS" if all(o for _, o in checks) else "FAIL"}")
