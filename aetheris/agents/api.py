"""FastAPI app for the aetheris-agent-orchestrator service."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..common.eventbus import InMemoryBus
from ..common.models import Incident
from .remediation import PLAYBOOKS, SelfHealingAgent

bus = InMemoryBus()
agent = SelfHealingAgent(bus=bus)

app = FastAPI(title="AETHERIS · agent-orchestrator", version="0.1.0",
              description="Self-healing multi-agent operations.")


class IncidentIn(BaseModel):
    service: str = Field(..., examples=["vision-edge"])
    kind: str = Field(..., examples=["high_cpu"])
    detail: str = ""
    severity: str = "warning"


@app.get("/health")
def health() -> dict:
    return {"service": "agent-orchestrator", "status": "ok", "playbooks": list(PLAYBOOKS)}


@app.post("/heal")
async def heal(inc: IncidentIn) -> dict:
    incident = Incident(service=inc.service, kind=inc.kind, detail=inc.detail, severity=inc.severity)
    result = await agent.heal(incident)
    return result.to_dict()


@app.get("/playbooks")
def playbooks() -> dict:
    return PLAYBOOKS


@app.get("/history")
def history(limit: int = 50) -> list[dict]:
    return [e.payload for e in bus.recent("agents.remediation", limit)]
