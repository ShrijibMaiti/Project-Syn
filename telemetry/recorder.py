"""Persist captured runs to data/, keyed by commit hash."""
from __future__ import annotations
import json
import os
import subprocess
from typing import Any, Dict, List, Optional

DATA_DIR = os.environ.get("SYN_DATA_DIR", "data")


def current_commit(default: str = "workdir") -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return default


class Recorder:
    def __init__(self, data_dir: str = DATA_DIR, commit: Optional[str] = None):
        self.commit = commit or current_commit()
        self.dir = os.path.join(data_dir, self.commit)
        os.makedirs(self.dir, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.dir, f"{name}.jsonl")

    def write(self, name: str, rows: List[Dict[str, Any]]) -> str:
        p = self._path(name)
        with open(p, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        return p

    def read(self, name: str) -> List[Dict[str, Any]]:
        p = self._path(name)
        if not os.path.exists(p):
            return []
        with open(p) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def exists(self, name: str) -> bool:
        return os.path.exists(self._path(name))