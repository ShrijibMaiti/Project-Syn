"""git push -> trigger. The actual entry point."""
from __future__ import annotations
import hashlib
import hmac
import os
from typing import List

from fastapi import APIRouter, Header, HTTPException, Request

from orchestration.main_agent import MainAgent
from platform.api import REPO

router = APIRouter()
SECRET = os.environ.get("SYN_WEBHOOK_SECRET", "")


def _verify(body: bytes, signature: str) -> bool:
    if not SECRET:
        return True
    mac = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={mac}", signature or "")


def _changed_files(payload: dict) -> List[str]:
    files: List[str] = []
    for c in payload.get("commits", []):
        files += c.get("added", []) + c.get("modified", []) + c.get("removed", [])
    return sorted(set(files))


@router.post("/webhook")
async def webhook(request: Request, x_hub_signature_256: str = Header(default="")):
    body = await request.body()
    if not _verify(body, x_hub_signature_256):
        raise HTTPException(401, "bad signature")
    payload = await request.json()
    commit = payload.get("after") or payload.get("head_commit", {}).get("id")
    verdict = MainAgent(REPO).run(commit, _changed_files(payload))
    return {"commit": commit, "risk": verdict.risk.value, "allowed": verdict.allowed}