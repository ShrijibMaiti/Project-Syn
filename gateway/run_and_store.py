"""Execute a full run and persist it for the dashboard.

CI (or you) calls this. The API never measures -- it serves.

Each stored run also records:
  - manifest.refs  -- which code each probe name pointed at for THIS run
                      (demo-faulty and demo-clean share names, not targets)
  - code_graph     -- a static call graph of the probed packages, snapshotted
                      at store time so each run's risk map shows its own code
"""
from __future__ import annotations
import argparse
import os

from analysis.snapshot import manifest_refs, snapshot_graph
from gateway import store
from gateway.manifest_loader import find_manifest, load
from orchestration.main_agent import MainAgent


def run_and_store(manifest_path=None, commit="workdir", serialize=True):
    # The sample app's DB must be populated or every complexity probe measures
    # an empty table: flat cost, exponent ~0, and a meaningless verdict.
    try:
        from sample_app.db import DB
        DB.seed(20000, 1)
    except Exception:
        pass

    path = find_manifest(manifest_path)
    if not path:
        raise SystemExit("no manifest found")
    agent = MainAgent(load(path), serialize=serialize)
    verdict, ctx = agent.run(commit=commit)
    cert = agent.certificate(verdict, ctx)

    refs = manifest_refs(path)
    project_root = os.path.dirname(os.path.abspath(path))
    extra = {"manifest": {"path": os.path.basename(path), "refs": refs},
             "code_graph": snapshot_graph(project_root, refs)}
    store.save_run(commit, verdict.to_dict(), cert, ctx.timings, extra=extra)
    return verdict, cert


def store_blind(seed_list=(0, 1, 2)):
    from validation.blind_detection import run_blind, evaluate
    seeds = []
    for s in seed_list:
        res, truth = run_blind(seed=s, verbose=False)
        sc, rows, unk = evaluate(res, truth, verbose=False)
        seeds.append({"seed": s,
                      "scorecard": {"tp": sc.tp, "fp": sc.fp, "tn": sc.tn, "fn": sc.fn,
                                    "detection_rate": sc.detection_rate,
                                    "false_positive_rate": sc.false_positive_rate,
                                    "precision": sc.precision, "accuracy": sc.accuracy},
                      "abstentions": unk,
                      "targets": [{"alias": a, "true_id": cid, "faulty": tf,
                                   "flagged": fl, "outcome": mark.strip(),
                                   "detail": d, "why": why,
                                   "trap": bool(getattr(truth[a], "trap", False))}
                                  for a, cid, tf, fl, mark, d, why in rows]})
    store.save_blob("blind", {"seeds": seeds})
    return seeds


def store_calibration():
    from stability.harness_calibration import calibrate
    floor, fit, rows = calibrate()
    store.save_blob("calibration", {
        "kappa_floor": floor, "margin": 10.0,
        "harness_fit": {"kappa": fit.kappa, "p_value": fit.p_value,
                        "sigma": fit.sigma, "evidence": fit.evidence},
        "points": [{"n": r["n"], "latency_s": r["R"],
                    "throughput": r["throughput"], "spread": r.get("spread")}
                   for r in rows],
        "note": ("Measured with a no-op target: zero coherency by construction. "
                 "Any kappa below floor*margin is indistinguishable from OS "
                 "scheduler overhead and must not be reported as a trap.")})
    return floor


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="syn-run")
    ap.add_argument("--commit", default="workdir")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args()
    v, _ = run_and_store(a.manifest, a.commit)
    print(f"stored run {a.commit}: {v.risk.value}")
    if a.calibrate:
        print(f"stored calibration: floor={store_calibration():.3e}")
    if a.blind:
        print(f"stored blind results for {len(store_blind())} seeds")
