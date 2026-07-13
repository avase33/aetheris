"""FastAPI app for the aetheris-vision-edge service."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..common.eventbus import InMemoryBus
from ..common.models import Frame
from ..config import Settings
from .compliance import ComplianceEngine
from .detector import get_detector
from .pipeline import VisionPipeline

settings = Settings.from_env()
bus = InMemoryBus()
pipeline = VisionPipeline(
    detector=get_detector(settings.detector_backend, settings.compliance_min_confidence),
    engine=ComplianceEngine(),
    bus=bus,
)

app = FastAPI(title="AETHERIS · vision-edge", version="0.1.0",
              description="Edge computer-vision compliance monitoring & alerting.")


class FrameIn(BaseModel):
    camera_id: str = Field(..., examples=["cam-12"])
    zone: str = Field(..., examples=["substation"])
    signature: list[float] = Field(default_factory=list,
                                   description="8-slot feature vector: person,hardhat,fire,smoke,vehicle,spill,intrusion,temp")


@app.get("/health")
def health() -> dict:
    return {"service": "vision-edge", "status": "ok", "detector": settings.detector_backend}


@app.post("/process")
async def process(frame: FrameIn) -> dict:
    alert = await pipeline.process(Frame(camera_id=frame.camera_id, zone=frame.zone, signature=frame.signature))
    if alert is None:
        return {"status": "clear"}
    return {"status": "violation", "alert": alert.to_dict()}


@app.get("/alerts")
def alerts(limit: int = 50) -> list[dict]:
    return [e.payload for e in bus.recent("vision.alert", limit)]


@app.get("/stats")
def stats() -> dict:
    return pipeline.stats()
