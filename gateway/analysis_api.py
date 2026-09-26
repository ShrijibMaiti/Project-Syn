"""Read-only API for the two analysis views: Sensitivity and the Risk Map.

Both are computed from what a stored run already contains -- the fitted laws
and the code-graph snapshot. Nothing here runs a measurement."""
from __future__ import annotations
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from gateway import store

router = APIRouter(prefix="/api")


def _resolve(commit: str) -> Dict[str, Any]:
    c = None if commit in (None, "", "latest") else commit
    c = c or store.latest_commit()
    if not c:
        raise HTTPException(404, "no runs stored yet — run the gate first")
    run = store.load_run(c)
    if not run:
        raise HTTPException(404, f"no run for commit {c}")
    return run


def _meta(run: Dict[str, Any]) -> Dict[str, Any]:
    return {"commit": run.get("commit"), "created_at": run.get("created_at"),
            "verdict": (run.get("verdict") or {}).get("risk")}


@router.get("/sensitivity")
def sensitivity(commit: str = "latest",
                ceiling_s: float = Query(30.0, gt=0, le=86400)):
    """What would it take to flip this run's verdict -- computed exactly from
    the laws the probes fitted, with the gate's own decision rule."""
    from analysis.sensitivity import analyse_run
    run = _resolve(commit)
    return {**_meta(run), **analyse_run(run, ceiling_s=ceiling_s)}


@router.get("/riskmap")
def riskmap(commit: str = "latest"):
    """Static call graph of the probed code, measured results on the nodes that
    were measured, and the blast radius of every flagged node."""
    from analysis.code_graph import build, overlay
    run = _resolve(commit)
    refs = (run.get("manifest") or {}).get("refs") or {}
    snap = run.get("code_graph") or {}
    notes = []

    if snap.get("graph"):
        graph = snap["graph"]
        table = {ref: tuple(v) for ref, v in (snap.get("resolution") or {}).items()}
        resolver = lambda ref: table.get(ref, (None, None))  # noqa: E731
        source = "snapshot"
    else:
        # Run stored before graphs were recorded: build from the current source.
        if snap.get("error"):
            notes.append(f"Graph snapshot failed at store time: {snap['error']}")
        live_refs = refs
        if not live_refs:
            from analysis.snapshot import manifest_refs
            live_refs = manifest_refs("syn.json") if os.path.exists("syn.json") else {}
            notes.append("This run was stored before code graphs and manifest targets were "
                         "recorded, so no measured result can be placed on the graph. "
                         "Re-store it with `python -m gateway.run_and_store`.")
        if not live_refs:
            raise HTTPException(404, "no manifest targets available to build a graph from")
        g, graph = build(os.getcwd(), live_refs)
        resolver = g.resolve_target_via
        source = "live"
        notes.append("Graph built from the CURRENT source, not a snapshot of this run's code.")

    ov = overlay(graph, run, refs, resolver)
    return {**_meta(run), "source": source, "notes": notes, "refs": refs,
            "graph": graph, "overlay": ov}
