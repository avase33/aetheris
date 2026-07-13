"""The vision-edge pipeline: frame → detect → evaluate → alert (publish)."""

from __future__ import annotations

from ..common.eventbus import EventBus
from ..common.models import Alert, Event, Frame
from ..logging_setup import get_logger
from .compliance import ComplianceEngine
from .detector import Detector

log = get_logger("vision")


class VisionPipeline:
    def __init__(self, detector: Detector, engine: ComplianceEngine, bus: EventBus | None = None):
        self.detector = detector
        self.engine = engine
        self.bus = bus
        self.frames_processed = 0
        self.alerts_raised = 0

    async def process(self, frame: Frame) -> Alert | None:
        self.frames_processed += 1
        detections = self.detector.detect(frame)
        violations = self.engine.evaluate(frame.zone, detections)
        if not violations:
            return None

        severity = self.engine.worst_severity(violations)
        alert = Alert(
            camera_id=frame.camera_id, zone=frame.zone, severity=severity,
            message=f"{len(violations)} compliance violation(s) in {frame.zone}",
            violations=violations,
        )
        self.alerts_raised += 1
        log.warning("ALERT [%s] %s (%s)", severity.upper(), alert.message, frame.camera_id)
        if self.bus is not None:
            await self.bus.publish(Event(topic="vision.alert", payload=alert.to_dict(), source="vision-edge"))
        return alert

    def stats(self) -> dict:
        return {"frames_processed": self.frames_processed, "alerts_raised": self.alerts_raised,
                "detector": self.detector.name}
