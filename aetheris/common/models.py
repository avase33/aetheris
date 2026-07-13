"""Shared domain models exchanged across services and on the event bus."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Event bus envelope
# ---------------------------------------------------------------------------
@dataclass
class Event:
    topic: str
    payload: dict[str, Any]
    source: str = "unknown"
    id: str = field(default_factory=lambda: new_id("evt"))
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "topic": self.topic, "source": self.source,
                "ts": self.ts, "payload": self.payload}


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------
@dataclass
class BoundingBox:
    x: float
    y: float
    w: float
    h: float


@dataclass
class Detection:
    label: str
    confidence: float
    box: BoundingBox

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "confidence": round(self.confidence, 4),
                "box": [self.box.x, self.box.y, self.box.w, self.box.h]}


@dataclass
class Frame:
    camera_id: str
    zone: str
    # A compact numeric signature standing in for pixels (keeps the demo offline).
    signature: list[float] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("frame"))
    ts: float = field(default_factory=time.time)


@dataclass
class Violation:
    rule: str
    severity: str  # info | warning | critical
    detail: str
    detections: list[Detection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "severity": self.severity, "detail": self.detail,
                "detections": [d.to_dict() for d in self.detections]}


@dataclass
class Alert:
    camera_id: str
    zone: str
    severity: str
    message: str
    violations: list[Violation] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("alert"))
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "camera_id": self.camera_id, "zone": self.zone,
                "severity": self.severity, "message": self.message, "ts": self.ts,
                "violations": [v.to_dict() for v in self.violations]}


# ---------------------------------------------------------------------------
# Agents / self-healing
# ---------------------------------------------------------------------------
@dataclass
class Incident:
    service: str
    kind: str
    detail: str
    severity: str = "warning"
    id: str = field(default_factory=lambda: new_id("inc"))
    ts: float = field(default_factory=time.time)


@dataclass
class RemediationStep:
    action: str
    result: str
    ok: bool = True


@dataclass
class RemediationResult:
    incident_id: str
    resolved: bool
    steps: list[RemediationStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"incident_id": self.incident_id, "resolved": self.resolved,
                "steps": [{"action": s.action, "result": s.result, "ok": s.ok} for s in self.steps]}


# ---------------------------------------------------------------------------
# Privacy
# ---------------------------------------------------------------------------
@dataclass
class RedactionResult:
    redacted_text: str
    entities: list[dict[str, Any]] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entities)


# ---------------------------------------------------------------------------
# MLOps
# ---------------------------------------------------------------------------
@dataclass
class DriftReport:
    model: str
    psi: float
    centroid_cosine_drift: float
    drifted: bool
    should_retrain: bool
    n_reference: int
    n_current: int

    def to_dict(self) -> dict[str, Any]:
        return {"model": self.model, "psi": round(self.psi, 4),
                "centroid_cosine_drift": round(self.centroid_cosine_drift, 4),
                "drifted": self.drifted, "should_retrain": self.should_retrain,
                "n_reference": self.n_reference, "n_current": self.n_current}


@dataclass
class ServiceHealth:
    service: str
    status: str  # ok | degraded | down
    detail: dict[str, Any] = field(default_factory=dict)
