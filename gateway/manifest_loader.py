"""Load a ProbeManifest from syn.toml / syn.json.

The CI gate cannot import arbitrary callables safely, so targets are declared as
'module:function' strings and resolved at run time. This is also the seam where
Phase-2 graph analysis would DERIVE targets instead of reading them."""
from __future__ import annotations
import importlib
import json
import os
from typing import Any, Callable, Dict, List

from orchestration.targets import ComplexityTarget, ProbeManifest, StabilityTarget

DEFAULT_PATHS = ["syn.toml", "syn.json", ".syn.json"]


def _resolve(ref: str) -> Callable:
    """'module:attr' -> callable. Supports 'module:obj.method'."""
    if ":" not in ref:
        raise ValueError(f"target must be 'module:attr', got {ref!r}")
    mod_name, attr_path = ref.split(":", 1)
    obj: Any = importlib.import_module(mod_name)
    for part in attr_path.split("."):
        obj = getattr(obj, part)
    if not callable(obj):
        raise TypeError(f"{ref} is not callable")
    return obj


def _load_raw(path: str) -> Dict[str, Any]:
    if path.endswith(".toml"):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def find_manifest(explicit=None):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    for p in DEFAULT_PATHS:
        if os.path.exists(p):
            return p
    return None


def load(path: str) -> ProbeManifest:
    raw = _load_raw(path)
    syn = raw.get("syn", raw)
    comp: List[ComplexityTarget] = []
    for t in syn.get("complexity", []):
        comp.append(ComplexityTarget(
            name=t["name"], call=_resolve(t["target"]),
            metric=t.get("metric", "elapsed_s"),
            n_min=int(t.get("n_min", 20)), n_max=int(t.get("n_max", 4000)),
            points=int(t.get("points", 10))))
    stab: List[StabilityTarget] = []
    for t in syn.get("stability", []):
        kw = {}
        if "levels" in t:
            kw["levels"] = [int(x) for x in t["levels"]]
        stab.append(StabilityTarget(
            name=t["name"], call=_resolve(t["target"]),
            samples_per_level=int(t.get("samples_per_level", 25)),
            repeats=int(t.get("repeats", 2)),
            operating_load=t.get("operating_load"), **kw))
    return ProbeManifest(complexity=comp, stability=stab)
