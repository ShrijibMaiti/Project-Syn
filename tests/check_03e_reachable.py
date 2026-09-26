from synthesis.simulator import RetryLoopTwin
from stability.basin_detector import detect, effective_operating_point, reachable_from_cold
from shared.verdict import relative_headroom, headroom_to_risk

twin = RetryLoopTwin()
print(f"{"load":>6}{"fixed points":>22}{"cold settles":>14}{"healthy reachable":>19}{"verdict":>9}")
for L in [2.0, 3.0, 3.5, 3.7, 3.8, 3.9]:
    ev = detect(twin, L)
    cold = effective_operating_point(twin, L)
    healthy = ev.fixed_points[0] if ev.fixed_points else None
    reach = reachable_from_cold(twin, L, healthy) if healthy is not None else False
    risk = headroom_to_risk(relative_headroom(ev)) if reach else "REFUSE(unreachable)"
    r = risk.value if hasattr(risk, "value") else risk
    print(f"{L:>6.2f}{str([round(p,2) for p in ev.fixed_points]):>22}"
          f"{cold:>14.2f}{str(reach):>19}{r:>9}")
