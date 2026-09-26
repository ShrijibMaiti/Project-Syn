"""THE INTEGRITY TEST. SYN gets 9 anonymised, shuffled targets and no labels.

Three of the negatives are traps for an over-eager detector:
  c_sort        -- O(n log n), superlinear in theory, must NOT be flagged
  c_nplus1      -- a REAL performance fault, but linear; must NOT be flagged
  s_contention  -- pure linear contention; the exact case that caused the old
                   catastrophic false positive

Expect 100% detection, 0% FPR. Takes ~1 minute."""
import time
from validation.blind_detection import run_blind, evaluate

print("SYN receives 9 anonymised, shuffled targets. No labels, no ground truth.\n")
t0 = time.time()
res, truth = run_blind(seed=0)
sc, rows, unknowns = evaluate(res, truth)

print(f"\nelapsed {time.time()-t0:.0f}s")
clean = (sc.detection_rate == 1.0 and sc.false_positive_rate == 0.0 and unknowns == 0)
print(f"BLIND DETECTION: {"PASS" if clean else "REVIEW"}")
if unknowns:
    print(f"  {unknowns} abstention(s) -- widen the measurement range for those targets")
