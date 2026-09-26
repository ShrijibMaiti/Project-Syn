"""Symbolic regression -> the closed-form law. THE core of the complexity lens.

Division of labour that makes extrapolation honest:
  - a fit identifies the regime WITHIN tested scales
  - symbolic regression extracts the LAW
  - the FORMULA extrapolates, because O(n^2) genuinely predicts n=1e6 from structure
Never ask a neural net to extrapolate across a control parameter.

TWO INDEPENDENT SELECTORS, because neither is reliable alone:
  - basis fit: raw R^2 lets constant overhead + noise pick the class at small n
  - tail exponent: needs the measured range to actually BE asymptotic
Disagreement lowers confidence and is REPORTED -- never silently resolved.
"""
from __future__ import annotations
from typing import Dict, Tuple

import numpy as np

from complexity.scale_spread_guard import check
from shared.law import ScalingLaw
from telemetry.multiscale_sweep import MultiScaleData

BASIS: Dict[str, Tuple[str, object]] = {
    "O(1)":       ("{a}",             lambda n: np.ones_like(n)),
    "O(log n)":   ("{a}*log2(n)",     lambda n: np.log2(np.maximum(n, 2))),
    "O(n)":       ("{a}*n",           lambda n: n),
    "O(n log n)": ("{a}*n*log2(n)",   lambda n: n * np.log2(np.maximum(n, 2))),
    "O(n^1.5)":   ("{a}*n**1.5",      lambda n: n ** 1.5),
    "O(n^2)":     ("{a}*n**2",        lambda n: n ** 2),
    "O(n^3)":     ("{a}*n**3",        lambda n: n ** 3),
}


def _loglog_exponent(data: MultiScaleData, min_points: int = 4):
    """Exponent from the ASYMPTOTIC TAIL: slope of log(y) vs log(n) over the top
    half of n, where the leading term dominates and constant overhead is irrelevant.
    (Subtracting an estimated offset instead badly distorts the small-n points.)"""
    n, y = np.asarray(data.n, float), np.asarray(data.resource, float)
    if n.size < min_points:
        return None
    k = max(min_points, n.size // 2)
    idx = np.argsort(n)[-k:]
    n, y = n[idx], y[idx]
    m = (n > 0) & (y > 0)
    if m.sum() < 3:
        return None
    return float(np.polyfit(np.log(n[m]), np.log(y[m]), 1)[0])

def _loglog_exponent_ci(data, min_points: int = 4):
    """Standard error of the asymptotic-tail slope -> 95% CI on the exponent.
    The UI reports the exponent as an interval, never a bare point estimate."""
    n, y = np.asarray(data.n, float), np.asarray(data.resource, float)
    if n.size < min_points:
        return None
    k = max(min_points, n.size // 2)
    idx = np.argsort(n)[-k:]
    n, y = n[idx], y[idx]
    m = (n > 0) & (y > 0)
    if m.sum() < 3:
        return None
    x, ly = np.log(n[m]), np.log(y[m])
    slope, intercept = np.polyfit(x, ly, 1)
    resid = ly - (slope * x + intercept)
    dof = max(len(x) - 2, 1)
    se = float(np.sqrt(np.sum(resid ** 2) / dof / max(np.sum((x - x.mean()) ** 2), 1e-18)))
    return (float(slope - 1.96 * se), float(slope + 1.96 * se))

def _class_from_exponent(e, tol: float = 0.35):
    if e is None:
        return None
    for name, target in [("O(1)", 0.0), ("O(n)", 1.0), ("O(n^1.5)", 1.5),
                         ("O(n^2)", 2.0), ("O(n^3)", 3.0)]:
        if abs(e - target) <= tol:
            return name
    if 1.0 < e < 1.35:
        return "O(n log n)"
    return None


def _fit_basis(data: MultiScaleData):
    n, y = data.n, data.resource
    best = ("unknown", 0.0, 0.0, -np.inf)
    for name, (_, fn) in BASIS.items():
        A = np.vstack([fn(n), np.ones_like(n)]).T
        try:
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        pred = A @ coef
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2)) or 1e-12
        r2 = 1.0 - ss_res / ss_tot
        if r2 > best[3]:
            best = (name, float(coef[0]), float(coef[1]), r2)
    return best


def _confidence(r2: float, decades: float) -> float:
    return float(np.clip(max(r2, 0.0) * np.clip(decades / 4.0, 0.0, 1.0), 0.0, 1.0))


def fit(data: MultiScaleData, use_pysr: bool = True,
        min_decades: float = 2.0) -> ScalingLaw:
    sp = check(data, min_decades)
    if not sp.sufficient:
        return ScalingLaw.insufficient(sp.reason, sp.decades)

    if use_pysr:
        try:
            from pysr import PySRRegressor
            model = PySRRegressor(niterations=40, binary_operators=["+", "*", "/"],
                                  unary_operators=["log", "square", "sqrt"],
                                  model_selection="best", progress=False, verbosity=0)
            model.fit(data.n.reshape(-1, 1), data.resource)
            expr = str(model.sympy()).replace("x0", "n")
            pred = model.predict(data.n.reshape(-1, 1))
            ss_res = float(np.sum((data.resource - pred) ** 2))
            ss_tot = float(np.sum((data.resource - data.resource.mean()) ** 2)) or 1e-12
            r2 = 1.0 - ss_res / ss_tot
            cls, _, _, _ = _fit_basis(data)
            return ScalingLaw(expr, {}, cls, r2, _confidence(r2, sp.decades),
                              sp.decades, True, float(data.n.min()),
                              float(data.n.max()), "PySR")
        except Exception:
            pass  # Julia backend missing / failed -> analytic fallback

    cls, a, b, r2 = _fit_basis(data)
    exp = _loglog_exponent(data)
    cls_exp = _class_from_exponent(exp)
    agree = (cls_exp is None) or (cls_exp == cls)
    expr = BASIS[cls][0].format(a=f"{a:.6g}") + f" + {b:.6g}"
    conf = _confidence(r2, sp.decades) * (1.0 if agree else 0.4)
    note = ("analytic basis fit" if agree else
            f"CLASS UNCERTAIN: basis fit says {cls}, tail exponent "
            f"{exp:.2f} suggests {cls_exp}. Widen the sweep before trusting "
            f"extrapolation.")
    return ScalingLaw(expr, {"a": a, "b": b}, cls, r2, conf, sp.decades, True,
                      float(data.n.min()), float(data.n.max()), note)