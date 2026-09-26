"""Document understanding -> order-parameter dimension labels.

Reads READMEs / ADRs / specs so the manifold's axes carry meaning ('dimension 0 is
the DB connection pool') instead of being anonymous indices."""
from __future__ import annotations
import os
import re
from typing import Dict, List, Optional

from shared.order_params import OrderParams

HINTS = {
    "queue_depth": ["queue", "backlog", "pending", "inflight", "in-flight"],
    "retry_rate": ["retry", "retries", "backoff", "re-attempt"],
    "error_rate": ["error rate", "failure rate", "5xx", "errors"],
    "cache_hit_ratio": ["cache hit", "cache-hit", "hit ratio", "cache"],
}


def _read_docs(root: str, exts=(".md", ".rst", ".txt")) -> str:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "venv")]
        for fn in filenames:
            if fn.lower().endswith(exts):
                try:
                    with open(os.path.join(dirpath, fn), errors="ignore") as fh:
                        out.append(fh.read())
                except OSError:
                    continue
    return "\n".join(out)


def label(params: OrderParams, repo_path: str) -> OrderParams:
    text = _read_docs(repo_path).lower()
    for name, hints in HINTS.items():
        if name not in params.names:
            continue
        for h in hints:
            m = re.search(rf"[^.\n]*\b{re.escape(h)}\b[^.\n]*", text)
            if m:
                params.labels[name] = m.group(0).strip()[:160]
                break
    return params


def find_ceilings(repo_path: str) -> Dict[str, float]:
    """Pull declared limits out of config/docs (pool_size=..., max_connections=...)."""
    text = _read_docs(repo_path) + "\n"
    for ext in (".yml", ".yaml", ".ini", ".toml", ".env"):
        for dirpath, _, filenames in os.walk(repo_path):
            for fn in filenames:
                if fn.endswith(ext):
                    try:
                        with open(os.path.join(dirpath, fn), errors="ignore") as fh:
                            text += fh.read() + "\n"
                    except OSError:
                        pass
    out: Dict[str, float] = {}
    for key in ("pool_size", "max_connections", "max_workers", "timeout"):
        m = re.search(rf"{key}\s*[:=]\s*(\d+(?:\.\d+)?)", text, re.I)
        if m:
            out[key] = float(m.group(1))
    return out