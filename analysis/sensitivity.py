"""What would it take? Counterfactuals computed from the MEASURED laws.

A refusal says "no". This module says what would make it "yes": the smallest
change to each measured quantity that moves the verdict across a gate line.
Nothing here is estimated or learned. Every number is algebra on laws the
probes already fitted:

  stability   R(N) = base*(1 + sigma*(N-1) + kappa*N*(N-1))   (USL, per run)
  complexity  cost(n) ~ n^e, anchored at the largest measured n

and every verdict is computed with the gate's OWN rule, so a threshold quoted
here is the exact point where the real gate changes its answer.

EXACT EQUILIBRIA. At offered load L the equilibria are the roots of
L = N / R(N), a quadratic in N:

    L*b*kappa*N^2 + (L*b*(sigma - kappa) - 1)*N + L*b*(1 - sigma) = 0

Smaller root = healthy operating point, larger root = separatrix. The gate
finds these roots on an integer grid and reports each as floor(root) + 0.5, so
headroom here is snapped the same way -- otherwise this page could quote a
headroom of 2.03 (WARN) for a run the gate refused at 2.00. Elasticities use the
unsnapped roots, because a step function has no useful derivative.

ASSUMPTIONS, stated rather than hidden:
  - kappa levers hold base and sigma at their fitted values.
  - load levers hold the whole fitted curve fixed.
  - ceiling crossings extrapolate from the LARGEST MEASURED n; they move if
    the named ceiling moves.
"""
from __future__ import annotations
import math
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

from stability.capacity_curve import (EXTRAPOLATION_LIMIT, FLOOR_MARGIN, HEADROOM_REFUSE,
                                      HEADROOM_WARN)

EXP_WARN, EXP_REFUSE = 1.2, 1.7      # must match orchestration/probes.py
DEFAULT_CEILING_S = 30.0             # gateway timeout assumed for ceiling crossings
GRID_MAX = 199999                    # the gate's root-finding grid is N = 1 .. GRID_MAX

SEVERITY = {"ok": 0, "unknown": 1, "warn": 2, "refuse": 3}
LABEL = {"ok": "PASS", "warn": "WARN", "refuse": "REFUSED", "unknown": "UNKNOWN"}


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Stability: exact equilibria of the fitted USL
# --------------------------------------------------------------------------- #

def exact_roots(load: float, base: float, sigma: float, kappa: float
                ) -> Tuple[Optional[float], Optional[float]]:
    """(healthy, separatrix) as real numbers; (None, None) above capacity."""
    A = load * base * kappa
    B = load * base * (sigma - kappa) - 1.0
    C = load * base * (1.0 - sigma)
    if A <= 0:                                   # no coherency: one equilibrium at most
        denom = 1.0 - load * base * sigma
        return ((C / denom) if denom > 0 else None), None
    disc = B * B - 4 * A * C
    if disc < 0:
        return None, None
    s = math.sqrt(disc)
    return (-B - s) / (2 * A), (-B + s) / (2 * A)


def _snap(r: Optional[float]) -> Optional[float]:
    """Where the gate's integer grid reports this root, or None if it misses it."""
    if r is None or r < 1 or r >= GRID_MAX or float(r).is_integer():
        return None
    return math.floor(r) + 0.5


def peak(base: float, sigma: float, kappa: float) -> Tuple[Optional[float], Optional[float]]:
    """(N*, throughput at N*). None when throughput never turns over."""
    if kappa <= 0:
        return None, None
    n_star = math.sqrt(max(1.0 - sigma, 1e-12) / kappa)
    r = base * (1 + sigma * (n_star - 1) + kappa * n_star * (n_star - 1))
    return n_star, n_star / r


def gate_state(load: float, base: float, sigma: float, kappa: float,
               capacity: Optional[float]) -> Dict[str, Any]:
    """The stability lens verdict at `load`, reproducing the gate's rule."""
    lo, hi = exact_roots(load, base, sigma, kappa)
    lo_s, hi_s = _snap(lo), _snap(hi)
    out = {"load": load, "healthy_n": lo_s, "separatrix": hi_s,
           "healthy_exact": lo, "separatrix_exact": hi, "headroom": None,
           "headroom_exact": (hi - lo) / lo if (lo and hi and lo > 0) else None}
    # Same order as the gate: a separatrix decides first; without one, load at
    # or above capacity is collapse, anything below is simply out of reach.
    if lo_s is None or hi_s is None:
        if capacity is not None and load >= capacity:
            out.update(verdict="refuse", region="above_capacity")
        else:
            out.update(verdict="ok", region="no_separatrix")
        return out
    h = (hi_s - lo_s) / max(lo_s, 1e-9)
    out["headroom"] = h
    v = "refuse" if h <= HEADROOM_REFUSE else "warn" if h <= HEADROOM_WARN else "ok"
    out.update(verdict=v, region="bistable")
    return out


def _sup_load(pred, lo: float, hi: float, iters: int = 80) -> float:
    """Largest load in [lo, hi] where pred(load) holds (pred monotone: true then false)."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if pred(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _max_kappa(pred, hi: float, iters: int = 80) -> float:
    """Largest kappa in [0, hi] where pred(kappa) holds (true at 0, false at hi)."""
    lo = 0.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if pred(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _elasticity(f, x: float, rel: float = 1e-3) -> Optional[float]:
    """d ln f / d ln x by central difference."""
    a, b = f(x * (1 - rel)), f(x * (1 + rel))
    if not a or not b or a <= 0 or b <= 0:
        return None
    return (math.log(b) - math.log(a)) / (math.log(1 + rel) - math.log(1 - rel))


def stability_sensitivity(e: Dict[str, Any], risk: Optional[str]) -> Dict[str, Any]:
    target = e.get("target")
    base, sigma, kappa = _num(e.get("base")), _num(e.get("sigma")), _num(e.get("kappa"))
    floor = _num(e.get("kappa_floor"))
    common = {"target": target, "lens_verdict": risk, "kappa": kappa,
              "kappa_floor": floor, "floor_margin": FLOOR_MARGIN}

    if e.get("adequate") is False:
        return {**common, "mode": "inadequate",
                "reason": ("The sweep was too narrow to fit the law, so no counterfactual "
                           "can be computed from it. Widen the sweep (>=16 levels to N>=256) "
                           "and re-run -- a what-if on an inadequate fit would be invented.")}
    if base is None or sigma is None or kappa is None:
        return {**common, "mode": "missing",
                "reason": "This run was stored without the fitted law. Re-store it."}
    if not e.get("evidence"):
        return {**common, "mode": "no_coherency",
                "reason": ("No coherency term: throughput never turns over, so no load, "
                           "cap or kappa change is needed -- there is no cliff to move away from.")}
    if e.get("exceeds_floor") is False:
        return {**common, "mode": "below_floor",
                "reason": (f"The kappa term is inside the instrument's own noise floor "
                           f"({_num(e.get('floor_ratio')) or 0:.1f}x, needs {FLOOR_MARGIN:g}x), "
                           f"so the gate reports no trap and there is nothing to lever.")}

    n_max = _num(e.get("n_max_measured"))
    if e.get("beyond_range"):
        return {**common, "mode": "beyond_range",
                "reason": (f"The kappa term is statistically real but its fitted peak lies "
                           f"beyond {EXTRAPOLATION_LIMIT:g}x the largest concurrency measured "
                           f"(N={n_max or 0:.0f}). The gate does not act on a cliff it would "
                           f"have to extrapolate that far, so there is nothing to lever.")}

    n_star, capacity_exact = peak(base, sigma, kappa)
    # The gate tests load against the peak IT found on its integer grid (stored
    # with the run); fall back to the exact peak for runs stored without it.
    capacity = _num(e.get("peak_throughput")) or capacity_exact
    load_now = _num(e.get("operating_load")) or (0.85 * capacity if capacity else None)
    if capacity is None or load_now is None:
        return {**common, "mode": "missing", "reason": "No throughput peak could be derived."}

    state = lambda L: gate_state(L, base, sigma, kappa, capacity)  # noqa: E731
    now = state(load_now)

    # Load thresholds: the exact loads where the gate's answer changes.
    lo_edge = capacity * 1e-4
    load_ok_max = _sup_load(lambda L: state(L)["verdict"] == "ok", lo_edge, capacity)
    load_warn_max = _sup_load(lambda L: state(L)["verdict"] != "refuse", lo_edge, capacity)

    # Kappa thresholds at the CURRENT operating load (base, sigma held fixed).
    def verdict_at_kappa(k: float) -> str:
        n_k, cap_k = peak(base, sigma, k) if k > 0 else (None, None)
        if n_k is not None and n_max and n_k > EXTRAPOLATION_LIMIT * n_max:
            return "ok"     # the gate's extrapolation limit, as in verdict()
        return gate_state(load_now, base, sigma, k, cap_k)["verdict"]

    kappa_warn_max = _max_kappa(lambda k: verdict_at_kappa(k) != "refuse", kappa)
    kappa_ok_max = _max_kappa(lambda k: verdict_at_kappa(k) == "ok", kappa)

    def kappa_row(target_k: float, reached_now: bool) -> Dict[str, Any]:
        if reached_now:
            return {"kappa": None, "reduction_pct": 0.0, "already": True}
        ratio = target_k / floor if floor else None
        return {"kappa": target_k, "reduction_pct": 100.0 * (1 - target_k / kappa),
                "already": False, "floor_ratio": ratio,
                "below_floor_margin": (ratio is not None and ratio <= FLOOR_MARGIN)}

    # Dense curve for the chart and the load slider.
    curve = []
    steps = 160
    for i in range(1, steps + 1):
        L = capacity * 1.12 * i / steps
        s = state(L)
        curve.append({"load": L, "headroom": s["headroom"],
                      "headroom_exact": s["headroom_exact"], "verdict": s["verdict"],
                      "region": s["region"], "healthy_n": s["healthy_n"],
                      "separatrix": s["separatrix"]})

    def head_exact_at_load(L):
        return gate_state(L, base, sigma, kappa, capacity)["headroom_exact"]

    def head_exact_at_kappa(k):
        _, cap_k = peak(base, sigma, k)
        return gate_state(load_now, base, sigma, k, cap_k)["headroom_exact"]

    return {
        **common, "mode": "trap_model",
        "law": {"base": base, "sigma": sigma, "kappa": kappa},
        "capacity": capacity, "peak_n": n_star,
        "operating_load": load_now,
        "now": now,
        "thresholds": {"load_ok_max": load_ok_max, "load_warn_max": load_warn_max,
                       "capacity": capacity},
        "levers": {
            "load": {
                "to_lift_refusal": None if now["verdict"] != "refuse" else
                    {"load": load_warn_max, "reduction_pct": 100 * (1 - load_warn_max / load_now)},
                "to_pass": None if now["verdict"] == "ok" else
                    {"load": load_ok_max, "reduction_pct": 100 * (1 - load_ok_max / load_now)},
            },
            "kappa": {
                "to_lift_refusal": kappa_row(kappa_warn_max, now["verdict"] != "refuse"),
                "to_pass": kappa_row(kappa_ok_max, now["verdict"] == "ok"),
            },
            "concurrency_cap": {
                "cap_n": max(1, math.floor(n_star)),
                "throughput_at_cap": (math.floor(n_star) / (base * (
                    1 + sigma * (math.floor(n_star) - 1)
                    + kappa * math.floor(n_star) * (math.floor(n_star) - 1))))
                    if n_star >= 1 else None,
                "separatrix_now": now["separatrix"],
            },
        },
        "elasticity": {
            "headroom_per_load": _elasticity(head_exact_at_load, load_now),
            "headroom_per_kappa": _elasticity(head_exact_at_kappa, kappa),
        },
        "curve": curve,
    }


# --------------------------------------------------------------------------- #
# Complexity: exponent margins and anchored ceiling crossings
# --------------------------------------------------------------------------- #

def _lens_from_exponent(e: float) -> str:
    return "refuse" if e > EXP_REFUSE else "warn" if e > EXP_WARN else "ok"


def complexity_sensitivity(e: Dict[str, Any], risk: Optional[str],
                           ceiling_s: float = DEFAULT_CEILING_S) -> Dict[str, Any]:
    target = e.get("target")
    exp = _num(e.get("exponent"))
    ci = e.get("exponent_ci")
    ci = (float(ci[0]), float(ci[1])) if isinstance(ci, (list, tuple)) and len(ci) == 2 else None
    rows = [r for r in (e.get("rows") or [])
            if _num(r.get("n")) and _num(r.get("elapsed_s")) and r["elapsed_s"] > 0]
    common = {"target": target, "lens_verdict": risk, "exponent": exp, "exponent_ci": ci,
              "thresholds": {"warn": EXP_WARN, "refuse": EXP_REFUSE}, "ceiling_s": ceiling_s}
    if exp is None:
        return {**common, "mode": "inadequate",
                "reason": e.get("note") or "No exponent was recovered for this target."}

    anchor = max(rows, key=lambda r: r["n"]) if rows else None
    n_max = float(anchor["n"]) if anchor else None
    cost_max = float(anchor["elapsed_s"]) if anchor else None

    def crossing(expo: float) -> Optional[float]:
        if not anchor or expo <= 0 or cost_max >= ceiling_s:
            return None
        return n_max * (ceiling_s / cost_max) ** (1.0 / expo)

    superlinear = bool(e.get("superlinear"))
    lens = _lens_from_exponent(exp)
    return {
        **common, "mode": "law",
        "superlinear": superlinear,
        "lens_from_exponent": lens,
        "anchor": {"n": n_max, "cost_s": cost_max},
        "scale_10x": 10 ** exp,                       # 10x the records -> this many x the time
        "scale_10x_ci": (10 ** ci[0], 10 ** ci[1]) if ci else None,
        "margins": {
            "to_warn_line": EXP_WARN - exp,           # negative = already over the line
            "to_refuse_line": EXP_REFUSE - exp,
            "ci_clears_warn": bool(ci and ci[0] > EXP_WARN),
            "ci_clears_refuse": bool(ci and ci[0] > EXP_REFUSE),
        },
        "levers": {
            "to_lift_refusal": None if lens != "refuse" else
                {"exponent": EXP_REFUSE, "scale_10x": 10 ** EXP_REFUSE},
            "to_pass": None if lens == "ok" else
                {"exponent": EXP_WARN, "scale_10x": 10 ** EXP_WARN},
        },
        # Gated only for superlinear growth; extrapolating anything else to a
        # ceiling is not a claim the gate makes.
        "ceiling_crossing": {
            "gated": superlinear,
            "n": crossing(exp) if superlinear else None,
            "n_ci": ((crossing(ci[1]), crossing(ci[0])) if (superlinear and ci) else None),
            "at_warn_line": crossing(EXP_WARN),
            "at_refuse_line": crossing(EXP_REFUSE),
        },
    }


# --------------------------------------------------------------------------- #
# The plan: fewest lens changes that move the OVERALL verdict
# --------------------------------------------------------------------------- #

def _aggregate(levels: List[str]) -> str:
    """The gate's aggregation rule, including concurrence escalation."""
    if not levels:
        return "unknown"
    worst = max(levels, key=lambda v: SEVERITY[v])
    flagged = sum(1 for v in levels if v in ("warn", "refuse"))
    if flagged >= 2 and worst == "warn":
        return "refuse"
    return worst


def plan(lenses: Dict[str, str]) -> Dict[str, Any]:
    """lenses: {lens_name: current_level}. For each target overall verdict, the
    fewest lens changes that reach it (ties broken toward the smaller change)."""
    names = list(lenses)
    current = _aggregate([lenses[n] for n in names])
    options = {n: ([lenses[n]] if lenses[n] in ("ok", "unknown") else
                   [lenses[n]] + [lv for lv in ("warn", "ok")
                                  if SEVERITY[lv] < SEVERITY[lenses[n]]])
               for n in names}

    def best(goal_ok):
        found = None
        for combo in product(*(options[n] for n in names)):
            overall = _aggregate(list(combo))
            if not goal_ok(overall):
                continue
            changes = [(n, lenses[n], c) for n, c in zip(names, combo) if c != lenses[n]]
            cost = (len(changes), sum(SEVERITY[lenses[n]] - SEVERITY[c] for n, _, c in changes))
            if found is None or cost < found[0]:
                found = (cost, overall, changes)
        if found is None:
            return None
        return {"overall": found[1],
                "changes": [{"lens": n, "from": a, "to": b} for n, a, b in found[2]]}

    blockers = [n for n in names if lenses[n] == "unknown"]
    return {
        "current": current,
        "to_lift_refusal": (best(lambda v: SEVERITY[v] <= SEVERITY["warn"])
                            if current == "refuse" else None),
        "to_pass": best(lambda v: v == "ok") if current != "ok" else None,
        "blocked_by_unknown": blockers,
        "escalation_note": ("Two lenses flagging the same change escalates WARN to REFUSED, "
                            "so lifting a refusal can require one lens to reach PASS."),
    }


def analyse_run(run: Dict[str, Any], ceiling_s: float = DEFAULT_CEILING_S) -> Dict[str, Any]:
    v = run.get("verdict", {})
    probes = v.get("probes", []) or []
    risk_of = {}
    for p in probes:
        ev = p.get("evidence") or {}
        risk_of[(p.get("kind"), ev.get("target"))] = p.get("risk")
    evid = v.get("evidence", {}) or {}

    stab = [stability_sensitivity(e, risk_of.get(("stability", e.get("target"))))
            for e in evid.get("stability", []) or []]
    comp = [complexity_sensitivity(e, risk_of.get(("complexity", e.get("target"))), ceiling_s)
            for e in evid.get("complexity", []) or []]

    lenses = {}
    for s in stab:
        lenses[f"stability:{s['target']}"] = s.get("lens_verdict") or "unknown"
    for c in comp:
        lenses[f"complexity:{c['target']}"] = c.get("lens_verdict") or "unknown"
    return {"commit": run.get("commit"), "created_at": run.get("created_at"),
            "verdict": v.get("risk"), "stability": stab, "complexity": comp,
            "plan": plan(lenses) if lenses else None}
