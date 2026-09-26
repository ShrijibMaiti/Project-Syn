from synthesis.simulator import RetryLoopTwin
from stability.fixed_points import find_fixed_points, classify
from stability.basin_detector import detect
import numpy as np

twin = RetryLoopTwin()
for L in [3.5, 3.7, 3.8, 3.85, 3.9]:
    raw = find_fixed_points(twin, L)
    loose = find_fixed_points(twin, L, rtol=0.005, atol=0.01)
    ev = detect(twin, L)
    print(f"load={L:.2f}  default={[round(p,2) for p in raw]}  "
          f"tight_tol={[round(p,2) for p in loose]}  bistable={ev.bistable}")

print("\nsettled values from cold vs hot start (ground truth):")
for L in [3.8, 3.85, 3.9]:
    cold = float(twin.settle(np.array([0.0]), L)[0])
    hot = float(twin.settle(np.array([99.0]), L)[0])
    print(f"  load={L:.2f}  cold={cold:.3f}  hot={hot:.3f}  distinct={abs(cold-hot)>0.5}")
