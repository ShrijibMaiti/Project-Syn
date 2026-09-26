from synthesis.simulator import RetryLoopTwin
from stability.basin_detector import detect
from shared.verdict import relative_headroom, headroom_to_risk, margin_to_risk

twin = RetryLoopTwin()
print(f"{"load":>6}{"margin":>9}{"headroom":>10}{"old gate":>10}{"new gate":>10}")
for L in [1.0, 2.0, 3.0, 3.5, 3.8]:
    e = detect(twin, L)
    h = relative_headroom(e)
    m = f"{e.margin:.3f}" if e.margin is not None else "--"
    hs = f"{h:.2f}" if h is not None else "--"
    print(f"{L:>6.1f}{m:>9}{hs:>10}{margin_to_risk(e.margin, None).value:>10}"
          f"{headroom_to_risk(h).value:>10}")

lo, hi = 3.5, 4.0
for _ in range(20):
    mid = (lo + hi) / 2
    if detect(twin, mid).bistable: lo = mid
    else: hi = mid
print(f"\ncritical load (healthy basin disappears): {(lo+hi)/2:.4f}")
