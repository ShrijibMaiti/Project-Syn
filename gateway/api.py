"""FastAPI app: dashboard API for the Manifold Visualizer."""
from __future__ import annotations
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gateway.dashboard_backend import router as dashboard_router

app = FastAPI(title="SYN", description="Guardian of the production manifold")

# Vite dev server + local preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "SYN_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
    ).split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "ok"}
