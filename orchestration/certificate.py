"""The evidence-backed verdict artifact -- refusal (or approval) WITH GROUNDS.

Section headers keep the axes apart: complexity measures resource vs INPUT
SIZE, stability measures latency vs CONCURRENCY.

Three rules this file exists to enforce:

1. ADEQUACY BEFORE EVIDENCE. An inadequate measurement supports no conclusion
   in either direction.

2. MISSING IS NOT ZERO. A value the probe never computed is omitted, never
   defaulted -- `.get("separatrix", 0)` once printed "separatrix n=0, headroom
   0.00" for a probe that stopped before computing either.

3. THE INSTRUMENT HAS A FLOOR. A kappa the F-test accepts but that sits inside
   the calibrated noise floor is reported as OS overhead, not as a trap.

Class labels (O(n^2), ...) are not printed: they flip run-to-run while the
exponent and its interval are stable, and the gate never uses them.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional

from shared.types import RiskLevel
from shared.verdict import Verdict

MIN_LEVELS, MIN_NMAX = 16, 256   # must match stability/capacity_curve.py


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if f == f else None   # NaN -> None
    except (TypeError, ValueError):
        return None


def _complexity_line(e: dict) -> str:
    target = e.get("target", "?")
    exp = _num(e.get("exponent"))
    if exp is None:
        return f"- `{target}`: {e.get('note', 'no result')}"
    ci = e.get("exponent_ci")
    ci_txt = (f" (95% CI [{float(ci[0]):.2f}, {float(ci[1]):.2f}])"
              if isinstance(ci, (list, tuple)) and len(ci) == 2 else "")
    return (f"- `{target}`: exponent **{exp:.2f}**{ci_txt}, "
            f"superlinear={bool(e.get('superlinear'))}")


def _stability_line(e: dict) -> str:
    target = e.get("target", "?")
    kappa = _num(e.get("kappa"))
    if kappa is None:
        return f"- `{target}`: {e.get('note', 'no result')}"

    # 1. adequacy first -- an inadequate sweep supports no conclusion at all
    if e.get("adequate") is False:
        levels = e.get("n_levels")
        nmax = e.get("n_max_measured")
        rng = (f"{levels} levels to N={nmax}"
               if levels is not None and nmax is not None else "too narrow a range")
        return (f"- `{target}`: **measurement inadequate** ({rng}; need "
                f">={MIN_LEVELS} levels to N>={MIN_NMAX}) — no conclusion either way; "
                f"a null result here is not evidence of absence")

    p = _num(e.get("p_value"))
    p_txt = f"p={p:.1e}" if p is not None else "p=?"

    # 2. adequate but no evidence -> absence IS supported
    if not e.get("evidence"):
        return f"- `{target}`: no coherency cost ({p_txt}) — no trap possible"

    # 3. evidence, but inside the instrument's own noise floor -> not the target
    if e.get("exceeds_floor") is False:
        ratio, floor = _num(e.get("floor_ratio")), _num(e.get("kappa_floor"))
        r_txt = f"{ratio:.1f}x" if ratio is not None else "below 10x"
        f_txt = f" (floor kappa={floor:.2e})" if floor is not None else ""
        return (f"- `{target}`: coherency term detected ({p_txt}) but kappa "
                f"{kappa:.2e} is only {r_txt} the instrument's noise floor{f_txt} — "
                f"indistinguishable from OS scheduler overhead; no trap reported")

    # 4. evidence above the floor: print only what was actually computed
    parts = [f"kappa **{kappa:.2e}** ({p_txt})"]
    peak_tp, peak_n = _num(e.get("peak_throughput")), _num(e.get("peak_n"))
    if peak_tp is not None and peak_n is not None:
        parts.append(f"peak {peak_tp:.0f}/s at N={peak_n:.0f}")
    sep, head = _num(e.get("separatrix")), _num(e.get("headroom"))
    if sep is not None:
        parts.append(f"separatrix N={sep:.1f}")
        if head is not None:
            parts.append(f"headroom **{head:.2f}**")
    else:
        parts.append("no separatrix at the operating load")
    ratio = _num(e.get("floor_ratio"))
    if ratio is not None:
        parts.append(f"{ratio:.0f}x the noise floor")
    return f"- `{target}`: " + "; ".join(parts)


def render_markdown(v: Verdict, commit: str, timings=None) -> str:
    label = {RiskLevel.OK: "PASS", RiskLevel.WARN: "WARN",
             RiskLevel.REFUSE: "REFUSED", RiskLevel.UNKNOWN: "UNKNOWN"}[v.risk]
    out = [f"## SYN — merge {label}", "",
           f"`{commit}` · {datetime.now(timezone.utc).isoformat(timespec='seconds')}", ""]

    comp = v.evidence.get("complexity", [])
    if comp:
        out += ["### Complexity (resource vs INPUT SIZE)"]
        out += [_complexity_line(e) for e in comp]
        out.append("")

    stab = v.evidence.get("stability", [])
    if stab:
        out += ["### Stability (latency vs CONCURRENCY)"]
        out += [_stability_line(e) for e in stab]
        out.append("")

    out += ["### Findings"] + [f"- {r}" for r in v.reasons]

    if v.risk is RiskLevel.REFUSE:
        # Only the lenses that actually flagged get a remedy: advice for a
        # problem this run did not measure would be noise on the certificate.
        fixes = []
        for e in comp:
            if e.get("superlinear"):
                fixes.append(f"- `{e.get('target')}` (superlinear): reduce the complexity "
                             "class (index the join, batch the queries).")
        for e in stab:
            if e.get("evidence") and e.get("exceeds_floor") is not False:
                fixes.append(f"- `{e.get('target')}` (coherency cost): reduce shared-resource "
                             "contention, or cap concurrency below the separatrix.")
        if fixes:
            out += ["", "### Remediation"] + fixes
    elif v.risk is RiskLevel.UNKNOWN:
        out += ["", "### What would settle it",
                f"- Widen the sweep to >={MIN_LEVELS} concurrency levels reaching "
                f"N>={MIN_NMAX}, then re-run the gate.",
                "- Until then this change is unverified, not approved. "
                "Use `--fail-on-unknown` to block on it."]

    if timings:
        pretty = ", ".join(f"{k}={vv:.1f}s" for k, vv in timings.items() if vv >= 0)
        out += ["", f"_probe timings: {pretty}_"]
    out += ["", "_Early warning from measured capacity and complexity laws. "
            "Statistical, not certain._"]
    return "\n".join(out)
