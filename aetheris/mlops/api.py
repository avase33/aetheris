"""FastAPI app for the aetheris-mlops-drift-watcher service."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..common.embeddings import embed
from ..common.eventbus import InMemoryBus
from ..common.models import Event
from ..config import Settings
from ..logging_setup import get_logger
from .drift import DriftMonitor
from .registry import ModelRegistry

log = get_logger("mlops")
settings = Settings.from_env()
bus = InMemoryBus()
monitor = DriftMonitor(settings.drift_psi_threshold, settings.drift_retrain_threshold)
registry = ModelRegistry(os.environ.get("AETHERIS_MLOPS_DB", "aetheris-mlops.db"))

app = FastAPI(title="AETHERIS · mlops-drift-watcher", version="0.1.0",
              description="Embeddings-drift & accuracy observability with retrain triggers.")


class RegisterIn(BaseModel):
    name: str
    version: str
    accuracy: float = Field(..., ge=0, le=1)


class DriftIn(BaseModel):
    model: str
    reference_texts: list[str] = Field(..., min_length=1)
    current_texts: list[str] = Field(..., min_length=1)


@app.get("/health")
def health() -> dict:
    return {"service": "mlops-drift-watcher", "status": "ok",
            "psi_threshold": settings.drift_psi_threshold}


@app.post("/register")
def register(body: RegisterIn) -> dict:
    registry.register(body.name, body.version, body.accuracy)
    return {"registered": body.model_dump(), "active": registry.active(body.name)}


@app.post("/drift")
async def drift(body: DriftIn) -> dict:
    dim = settings.embedding_dim
    ref = [embed(t, dim) for t in body.reference_texts]
    cur = [embed(t, dim) for t in body.current_texts]
    report = monitor.compute(body.model, ref, cur)
    registry.record_drift(report)
    if report.should_retrain:
        log.warning("DRIFT retrain triggered for %s (psi=%.3f)", body.model, report.psi)
        await bus.publish(Event(topic="mlops.retrain", payload=report.to_dict(), source="mlops-drift-watcher"))
    return report.to_dict()


@app.get("/models/{name}")
def models(name: str) -> dict:
    active = registry.active(name)
    if not active:
        raise HTTPException(status_code=404, detail="model not found")
    return {"active": active, "versions": registry.versions(name)}


@app.get("/drift/{model}")
def drift_history(model: str, limit: int = 50) -> list[dict]:
    return registry.drift_history(model, limit)


@app.get("/retrain-events")
def retrain_events(limit: int = 50) -> list[dict]:
    return [e.payload for e in bus.recent("mlops.retrain", limit)]
