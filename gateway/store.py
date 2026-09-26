"""Persistent run store.

Probes take minutes; the frontend cannot block on them. Runs are executed once
(by CI or manually), persisted here, and served instantly to the UI."""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional

STORE_DIR = os.environ.get("SYN_STORE_DIR", "data/runs")


def _path(commit: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in commit)
    return os.path.join(STORE_DIR, f"{safe}.json")


def save_run(commit, verdict_dict, certificate, timings=None,
             extra: Optional[Dict[str, Any]] = None) -> str:
    """`extra` carries run-scoped artifacts beyond the verdict: the manifest
    targets that were probed and the code-graph snapshot for this commit."""
    os.makedirs(STORE_DIR, exist_ok=True)
    payload = {"commit": commit, "created_at": time.time(),
               "verdict": verdict_dict, "certificate": certificate,
               "timings": timings or {}}
    if extra:
        payload.update(extra)
    p = _path(commit)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return p


def load_run(commit: str) -> Optional[Dict[str, Any]]:
    p = _path(commit)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.isdir(STORE_DIR):
        return []
    out = []
    for fn in os.listdir(STORE_DIR):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue   # "_name.json" are blobs (blind, calibration), not runs
        try:
            with open(os.path.join(STORE_DIR, fn), encoding="utf-8") as fh:
                r = json.load(fh)
            out.append({"commit": r.get("commit"), "created_at": r.get("created_at"),
                        "risk": r.get("verdict", {}).get("risk"),
                        "reasons": r.get("verdict", {}).get("reasons", [])[:2]})
        except Exception:
            continue
    return sorted(out, key=lambda r: r.get("created_at") or 0, reverse=True)[:limit]


def latest_commit() -> Optional[str]:
    runs = list_runs(1)
    return runs[0]["commit"] if runs else None


def save_blob(name: str, payload: Dict[str, Any]) -> str:
    """Non-run artifacts: blind-detection results, calibration."""
    os.makedirs(STORE_DIR, exist_ok=True)
    p = os.path.join(STORE_DIR, f"_{name}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({**payload, "created_at": time.time()}, fh, indent=2, default=str)
    return p


def load_blob(name: str) -> Optional[Dict[str, Any]]:
    p = os.path.join(STORE_DIR, f"_{name}.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)
