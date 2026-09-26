"""PHASE 2 ONLY -- Twin state per commit hash for delta-twinning."""
from __future__ import annotations
import json
import os
from typing import Any, Optional


class TwinCache:
    def __init__(self, url: Optional[str] = None, ttl: int = 7 * 24 * 3600):
        self.ttl = ttl
        self._r = None
        url = url or os.environ.get("REDIS_URL")
        if url:
            try:
                import redis
                self._r = redis.from_url(url)
            except Exception:
                self._r = None
        self._mem: dict = {}

    def _key(self, commit: str, name: str) -> str:
        return f"syn:{commit}:{name}"

    def put(self, commit: str, name: str, payload: Any) -> None:
        blob = json.dumps(payload)
        if self._r:
            self._r.setex(self._key(commit, name), self.ttl, blob)
        else:
            self._mem[self._key(commit, name)] = blob

    def get(self, commit: str, name: str) -> Optional[Any]:
        k = self._key(commit, name)
        blob = self._r.get(k) if self._r else self._mem.get(k)
        return json.loads(blob) if blob else None