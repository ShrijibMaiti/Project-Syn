from synthesis.simulator import RetryLoopTwin
from stability.basin_detector import detect, reachable_from_cold

twin = RetryLoopTwin()
lo, hi = 3.5, 4.0
for _ in range(25):
    mid = (lo + hi) / 2
    ev = detect(twin, mid)
    fp = ev.fixed_points[0] if ev.fixed_points else None
    if fp is not None and reachable_from_cold(twin, mid, fp):
        lo = mid
    else:
        hi = mid
print(f"operational critical load (healthy basin unreachable): {(lo+hi)/2:.4f}")
print("existence-based estimate was 3.9053 -- the gap is the unsafe margin")
