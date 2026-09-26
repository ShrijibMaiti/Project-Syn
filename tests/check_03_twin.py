from synthesis.simulator import RetryLoopTwin
from stability.basin_detector import detect

twin = RetryLoopTwin()
print(f"{"load":>6}{"bistable":>10}{"margin":>9}   fixed points")
for L in [2.0, 3.0, 3.5, 4.0, 4.5]:
    e = detect(twin, L)
    m = f"{e.margin:.3f}" if e.margin is not None else "--"
    print(f"{L:>6.1f}{str(e.bistable):>10}{m:>9}   {[round(p,2) for p in e.fixed_points]}")
