"""Run-scoped artifacts recorded with each stored run: which code every probe
name pointed at, and a static call graph of that code.

Kept free of orchestration imports so the API can use it without loading the
measurement stack."""
from __future__ import annotations
import json
import time


def manifest_refs(path: str) -> dict:
    """{probe name: 'pkg.mod:attr'} straight from the manifest file."""
    try:
        if path.endswith(".toml"):
            try:
                import tomllib
            except ImportError:            # Python < 3.11
                import tomli as tomllib
            with open(path, "rb") as fh:
                doc = tomllib.load(fh)
        else:
            with open(path, encoding="utf-8-sig") as fh:
                doc = json.load(fh)
    except Exception:
        return {}
    syn = doc.get("syn", doc)
    refs = {}
    for lens in ("complexity", "stability"):
        for t in syn.get(lens, []) or []:
            if t.get("name") and t.get("target"):
                refs[t["name"]] = t["target"]
    return refs


def snapshot_graph(project_root: str, refs: dict) -> dict:
    """Static call graph of the packages the manifest points at. Never fails
    the run: a graph error is recorded, not raised."""
    try:
        from analysis.code_graph import build
        g, graph = build(project_root, refs)
        resolution = {ref: list(g.resolve_target_via(ref)) for ref in refs.values()}
        return {"graph": graph, "resolution": resolution, "built_at": time.time()}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
