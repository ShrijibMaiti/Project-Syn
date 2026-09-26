"""Read-only API for the Manifold Visualizer.

Serves PERSISTED run results. Probes take minutes, so nothing here executes a
measurement -- runs are produced by CI (or `syn-run`) and stored, then served
instantly. Every endpoint returns the raw measured points alongside the fit, so
the UI plots DATA, not just a curve."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import os

from fastapi import APIRouter, HTTPException, Query

from gateway import store

router = APIRouter(prefix="/api")


def _probe_block(run: Dict[str, Any], kind: str) -> List[Dict[str, Any]]:
    return (run.get("verdict", {}).get("evidence", {}) or {}).get(kind, []) or []


def _resolve(commit: Optional[str]) -> Dict[str, Any]:
    c = commit or store.latest_commit()
    if not c:
        raise HTTPException(404, "no runs stored yet — run the gate first")
    run = store.load_run(c)
    if not run:
        raise HTTPException(404, f"no run for commit {c}")
    return run


def _pick(blocks: List[Dict[str, Any]], target: str) -> Optional[Dict[str, Any]]:
    """Exact target match, else the first block when the UI asks for 'default'."""
    return (next((b for b in blocks if b.get("target") == target), None)
            or (blocks[0] if target == "default" and blocks else None))


@router.get("/runs")
def runs(limit: int = Query(50, ge=1, le=200)):
    return {"runs": store.list_runs(limit)}


@router.get("/verdict/{commit}")
def verdict(commit: str):
    run = _resolve(None if commit == "latest" else commit)
    v = run["verdict"]
    return {"commit": run["commit"], "created_at": run["created_at"],
            "risk": v["risk"], "reasons": v["reasons"],
            "probes": v.get("probes", []), "certificate": run["certificate"],
            "timings": run.get("timings", {})}


@router.get("/stability/{target}")
def stability(target: str, commit: str = "latest"):
    """Capacity curve. x-axis = N (CONCURRENCY). Never conflate with complexity's n."""
    run = _resolve(None if commit == "latest" else commit)
    e = _pick(_probe_block(run, "stability"), target)
    if not e:
        raise HTTPException(404, f"no stability probe for target {target!r}")
    rows = e.get("rows", [])
    return {
        "axis": "N", "axis_label": "concurrency (N)", "target": e.get("target"),
        "points": [{"n": r["n"], "latency_s": r["R"],
                    "throughput": r["throughput"], "spread": r.get("spread")}
                   for r in rows],
        "fit": {"base": e.get("base"), "sigma": e.get("sigma"),
                "kappa": e.get("kappa"), "kappa_ci": e.get("kappa_ci"),
                "p_value": e.get("p_value"), "r2": e.get("r2")},
        "evidence": e.get("evidence"), "adequate": e.get("adequate"),
        "peak": {"n": e.get("peak_n"), "throughput": e.get("peak_throughput")},
        "raw_peak": {"n": e.get("raw_peak_n"), "throughput": e.get("raw_peak_tp")},
        "trap": {"operating_load": e.get("operating_load"),
                 "healthy_n": e.get("healthy_n"),
                 "separatrix": e.get("separatrix"),
                 "headroom": e.get("headroom")},
        "measurement": {"levels": e.get("n_levels"), "n_max": e.get("n_max_measured")},
        "note": e.get("note"),
    }


@router.get("/complexity/{target}")
def complexity(target: str, commit: str = "latest"):
    """Scaling law. x-axis = n (INPUT SIZE). Never conflate with stability's N."""
    run = _resolve(None if commit == "latest" else commit)
    e = _pick(_probe_block(run, "complexity"), target)
    if not e:
        raise HTTPException(404, f"no complexity probe for target {target!r}")
    rows = e.get("rows", [])
    return {
        "axis": "n", "axis_label": "input size (n)", "target": e.get("target"),
        "points": [{"n": r["n"], "resource": r.get("elapsed_s"),
                    "spread": r.get("spread")} for r in rows],
        "law": {"expression": e.get("expression"), "class": e.get("class"),
                "exponent": e.get("exponent"),
                "exponent_ci": e.get("exponent_ci"),
                "r2": e.get("r2"), "confidence": e.get("confidence")},
        "superlinear": e.get("superlinear"),
        "measurement": {"decades": e.get("decades"),
                        "n_min": e.get("n_min"), "n_max": e.get("n_max")},
        "note": e.get("note"),
    }


@router.get("/evidence")
def evidence(commit: str = "latest", target: str = "default"):
    """M0 vs M1 comparison, kappa CI, adequacy — the statistical detail."""
    s = stability(target, commit)
    # The floor that was APPLIED at gate time is recorded with the run. Prefer
    # it: runs come from different machines (laptop, CI runners) and each has
    # its own floor. The store-wide calibration is only a fallback for runs
    # recorded before the floor was stored per run.
    e = _pick(_probe_block(_resolve(None if commit == "latest" else commit),
                           "stability"), target) or {}
    floor = e.get("kappa_floor")
    if floor is None:
        floor = (store.load_blob("calibration") or {}).get("kappa_floor")
    k = s["fit"]["kappa"]
    return {
        "target": s["target"],
        "models": {
            "M0": {"label": "no coherency",
                   "form": "R(N) = base·(1 + σ(N−1))"},
            "M1": {"label": "coherency",
                   "form": "R(N) = base·(1 + σ(N−1) + κN(N−1))"},
        },
        "sigma": s["fit"]["sigma"], "kappa": k, "kappa_ci": s["fit"]["kappa_ci"],
        "p_value": s["fit"]["p_value"], "r2": s["fit"]["r2"],
        "evidence": s["evidence"], "adequate": s["adequate"],
        "measurement": s["measurement"],
        "trap": s["trap"],
        "noise_floor": floor,
        "floor_ratio": e.get("floor_ratio"),
        "exceeds_floor": (e["exceeds_floor"] if e.get("exceeds_floor") is not None
                          else None if not floor or k is None
                          else bool(k > floor * 10)),
        "r2_caveat": ("R^2 is NOT the decision criterion: under relative-error "
                      "weighting it can read 1.0000 while kappa is badly wrong. "
                      "The nested F-test decides."),
    }


@router.get("/blind")
def blind():
    b = store.load_blob("blind")
    if not b:
        raise HTTPException(404, "no blind-detection results stored — "
                                 "run `syn-run --blind`")
    return b


@router.get("/calibration")
def calibration():
    c = store.load_blob("calibration")
    if not c:
        raise HTTPException(404, "no calibration stored — "
                                 "run `syn-run --calibrate`")
    return c


@router.get("/landing")
def landing():
    """Proof numbers for the marketing page, composed from the stored run, the
    blind-detection results, and the harness calibration. Nothing here is
    hand-written: if no run is stored this 404s rather than inventing numbers."""
    # The landing page tells the refusal story, so it shows the showcase run
    # (SYN_LANDING_RUN, default demo-faulty) when that run exists -- a real
    # measurement like any other -- and the latest run otherwise.
    showcase = os.environ.get("SYN_LANDING_RUN", "demo-faulty")
    run = store.load_run(showcase) if showcase else None
    run = run or _resolve(None)
    v = run["verdict"]
    c = (_probe_block(run, "complexity") or [{}])[0]
    st = (_probe_block(run, "stability") or [{}])[0]
    blind_blob = store.load_blob("blind") or {}
    cal = store.load_blob("calibration") or {}
    seeds = blind_blob.get("seeds", [])
    sc = seeds[0]["scorecard"] if seeds else {}

    # The traps: targets that are NOT faulty yet were correctly cleared. These
    # are the cases built to fool an over-eager detector.
    traps = []
    if seeds:
        for t in seeds[0].get("targets", []):
            if not t.get("faulty") and t.get("outcome") == "OK":
                traps.append({"id": t.get("alias"), "truth": t.get("why"),
                              "measure": t.get("detail"), "decision": "PASS"})

    return {
        "commit": run["commit"], "risk": v["risk"],
        "complexity": {"target": c.get("target"), "exponent": c.get("exponent"),
                       "exponent_ci": c.get("exponent_ci"),
                       "superlinear": c.get("superlinear"),
                       "decades": c.get("decades")},
        "stability": {"target": st.get("target"), "kappa": st.get("kappa"),
                      "p_value": st.get("p_value"),
                      "peak_n": st.get("peak_n"),
                      "peak_throughput": st.get("peak_throughput"),
                      "separatrix": st.get("separatrix"),
                      "headroom": st.get("headroom"),
                      "levels": st.get("n_levels")},
        "blind": {"seeds": len(seeds), **sc},
        "calibration": {"kappa_floor": cal.get("kappa_floor"),
                        "margin": cal.get("margin")},
        "traps": traps[:3],
    }


@router.get("/health")
def health():
    return {"status": "ok", "runs": len(store.list_runs(200))}