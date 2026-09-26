"""Wrap each lens as a ProbeResult. Every probe degrades to UNKNOWN on failure --
never silently to OK. Failed probes still carry their target name so the
certificate can name what went unmeasured.

Both probes emit their RAW MEASURED ROWS alongside the fit. The dashboard plots
data points, not just a fitted curve.

NOISE FLOOR: the stability probe records the floor comparison WITH the run
(kappa_floor, floor_ratio, exceeds_floor), so the certificate, the API and the
dashboard all report the floor that was actually applied at gate time.

NOTATION: lowercase n is INPUT SIZE (complexity lens); uppercase N is
CONCURRENCY (stability lens). Every user-facing string keeps them apart."""
from __future__ import annotations
from typing import Dict

from shared.types import ProbeKind, ProbeResult, RiskLevel
from orchestration.targets import ComplexityTarget, StabilityTarget


def complexity_probe(t: ComplexityTarget) -> ProbeResult:
    from telemetry.multiscale_sweep import build, log_spaced, timed_sweep
    from complexity.symbolic_regressor import (fit, _loglog_exponent,
                                               _loglog_exponent_ci)
    try:
        ns = log_spaced(t.n_min, t.n_max, t.points)
        rows = timed_sweep(t.call, ns, repeats=5, warmup=2)
        d = build(rows, t.metric)
        law = fit(d, use_pysr=False)
        exp = _loglog_exponent(d)
        exp_ci = _loglog_exponent_ci(d)
    except Exception as exc:
        return ProbeResult(ProbeKind.COMPLEXITY, RiskLevel.UNKNOWN,
                           f"{t.name}: probe failed: {exc}",
                           evidence={"target": t.name, "note": f"failed: {exc}"},
                           error=str(exc))
    if not law.sufficient_evidence:
        return ProbeResult(ProbeKind.COMPLEXITY, RiskLevel.UNKNOWN,
                           f"{t.name}: insufficient evidence -- {law.note}",
                           evidence={"target": t.name, "note": law.note,
                                     "rows": rows})
    # Gate on SUPERLINEARITY, not on a class label: labels flip run-to-run while
    # the exponent is stable.
    superlinear = exp is not None and exp > 1.2
    risk = (RiskLevel.REFUSE if (superlinear and exp > 1.7)
            else RiskLevel.WARN if superlinear else RiskLevel.OK)
    ci_txt = f" CI[{exp_ci[0]:.2f},{exp_ci[1]:.2f}]" if exp_ci else ""
    return ProbeResult(
        ProbeKind.COMPLEXITY, risk,
        f"{t.name}: exponent {exp:.2f}{ci_txt} "
        f"({law.scale_spread_decades:.1f} decades)"
        + ("  SUPERLINEAR" if superlinear else ""),
        evidence={"target": t.name, "exponent": exp, "exponent_ci": exp_ci,
                  "class": law.complexity_class, "expression": law.expression,
                  "r2": law.r2, "superlinear": bool(superlinear),
                  "confidence": law.confidence,
                  "decades": law.scale_spread_decades,
                  "n_min": law.n_min, "n_max": law.n_max,
                  "rows": rows})          # raw measured points for the chart


def stability_probe(t: StabilityTarget) -> ProbeResult:
    from stability.capacity_curve import (measure_latency_curve, fit_capacity,
                                          analyse_trap, verdict, load_kappa_floor,
                                          floor_comparison, cliff_in_range)
    try:
        rows = measure_latency_curve(t.call, t.levels,
                                     samples_per_level=t.samples_per_level,
                                     repeats=t.repeats)
        f = fit_capacity(rows)
    except Exception as exc:
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.UNKNOWN,
                           f"{t.name}: probe failed: {exc}",
                           evidence={"target": t.name, "note": f"failed: {exc}"},
                           error=str(exc))
    raw_peak = max(rows, key=lambda r: r["throughput"]) if rows else None
    floor = load_kappa_floor()
    exceeds, ratio = floor_comparison(f.kappa, floor)
    ev: Dict = {"target": t.name, "kappa": f.kappa, "kappa_ci": list(f.kappa_ci),
                "p_value": f.p_value, "sigma": f.sigma, "evidence": f.evidence,
                "adequate": f.adequate_measurement,
                "raw_peak_tp": raw_peak["throughput"] if raw_peak else None,
                "raw_peak_n": raw_peak["n"] if raw_peak else None,
                "base": f.base, "r2": f.r2,
                "n_levels": f.n_levels, "n_max_measured": f.n_max,
                "kappa_floor": floor or None, "floor_ratio": ratio,
                "exceeds_floor": exceeds,
                "rows": rows}             # raw measured points for the chart
    if not f.adequate_measurement:
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.UNKNOWN,
                           f"{t.name}: {f.note}", evidence=ev)
    if not f.evidence:
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.OK,
                           f"{t.name}: {f.note}", evidence=ev)
    if exceeds is False:
        # Statistically real, but inside the instrument's own noise: not the target.
        _, why = verdict(f, 0.0, kappa_floor=floor)
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.OK,
                           f"{t.name}: {why}", evidence=ev)
    ev["beyond_range"] = not cliff_in_range(f.peak_n, f.n_max)
    if ev["beyond_range"]:
        # Statistically real, but the cliff is far outside what was measured.
        _, why = verdict(f, 0.0, kappa_floor=floor)
        ev.update({"peak_n": f.peak_n, "peak_throughput": f.peak_throughput})
        return ProbeResult(ProbeKind.STABILITY, RiskLevel.OK,
                           f"{t.name}: {why}", evidence=ev)
    load = t.operating_load if t.operating_load is not None else 0.85 * f.peak_throughput
    tr = analyse_trap(f, load)
    v, why = verdict(f, load, kappa_floor=floor)
    ev.update({"peak_n": f.peak_n, "peak_throughput": f.peak_throughput,
               "operating_load": load, "healthy_n": tr.healthy_n,
               "separatrix": tr.separatrix, "headroom": tr.headroom})
    floor_txt = f" ({ratio:.0f}x noise floor)" if ratio is not None else ""
    summary = (f"{t.name}: coherency detected (kappa={f.kappa:.2e}, p={f.p_value:.1e}){floor_txt}; "
               f"peak {f.peak_throughput:.0f}/s at N={f.peak_n:.0f}; at load {load:.0f}/s "
               f"separatrix N={tr.separatrix:.1f}, headroom {tr.headroom:.2f}"
               if tr.bistable else f"{t.name}: {why}")
    return ProbeResult(ProbeKind.STABILITY, v, summary, evidence=ev)
