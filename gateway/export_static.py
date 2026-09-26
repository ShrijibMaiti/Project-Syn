"""Export every API response for every stored run as static JSON files.

The live dashboard needs no server: CI publishes these files to the `syn-runs`
branch and the frontend (static mode, VITE_DATA_BASE_URL) fetches them.
Responses are produced by calling the SAME handler functions the FastAPI
server uses, so the static site and the API can never disagree.

PATH MAPPING (must match frontend/src/api/client.js `staticPath`):
  strip the leading "/", drop `commit=latest`, sort the query keys, append
  "__<key>-<value>" per parameter, then ".json".
    /verdict/demo-faulty                 -> verdict/demo-faulty.json
    /stability/default?commit=pr-7-abc   -> stability/default__commit-pr-7-abc.json
    /sensitivity?commit=latest&ceiling_s=30 -> sensitivity__ceiling_s-30.json

    SYN_STORE_DIR=published/runs python -m gateway.export_static --out published/api
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from urllib.parse import parse_qsl, urlsplit

CEILINGS = (1, 5, 30, 60)   # the Sensitivity page's ceiling switch


def static_path(path: str) -> str:
    parts = urlsplit(path)
    q = [(k, v) for k, v in parse_qsl(parts.query)
         if not (k == "commit" and v == "latest")]
    suffix = "".join(f"__{k}-{v}" for k, v in sorted(q))
    return parts.path.lstrip("/") + suffix + ".json"


def export(out_dir: str, quiet: bool = False) -> int:
    from fastapi import HTTPException
    from gateway import analysis_api as an
    from gateway import dashboard_backend as db
    from gateway import store

    tmp = out_dir.rstrip("/") + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    written = 0

    def put(path, fn, *a, **kw):
        nonlocal written
        try:
            payload = fn(*a, **kw)
        except HTTPException:
            return          # the API would 404 here; the file is simply absent
        dest = os.path.join(tmp, static_path(path))
        os.makedirs(os.path.dirname(dest) or tmp, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, default=str, separators=(",", ":"))
        written += 1

    runs = store.list_runs(200)
    put("/runs", db.runs, limit=200)
    put("/blind", db.blind)
    put("/calibration", db.calibration)
    put("/landing", db.landing)
    put("/health", db.health)

    for c in ["latest"] + [r["commit"] for r in runs if r.get("commit")]:
        q = "" if c == "latest" else f"?commit={c}"
        put(f"/verdict/{c}", db.verdict, c)
        put(f"/stability/default{q}", db.stability, "default", c)
        put(f"/complexity/default{q}", db.complexity, "default", c)
        put(f"/evidence{q}", db.evidence, c, "default")
        put(f"/riskmap?commit={c}", an.riskmap, c)
        for s in CEILINGS:
            put(f"/sensitivity?commit={c}&ceiling_s={s}", an.sensitivity, c, float(s))

    # Swap in atomically so a half-written export is never published.
    shutil.rmtree(out_dir, ignore_errors=True)
    os.replace(tmp, out_dir)
    if not quiet:
        print(f"export_static: {len(runs)} runs -> {written} files in {out_dir}")
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="syn-export-static")
    ap.add_argument("--out", default="published/api")
    args = ap.parse_args(argv)
    export(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
