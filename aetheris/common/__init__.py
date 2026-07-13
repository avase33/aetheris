"""Shared library: models, event bus, embeddings."""

from . import embeddings
from .eventbus import EventBus, InMemoryBus, RedisBus, get_bus
from .models import (
    Alert,
    BoundingBox,
    Detection,
    DriftReport,
    Event,
    Frame,
    Incident,
    RedactionResult,
    RemediationResult,
    RemediationStep,
    ServiceHealth,
    Violation,
    new_id,
)

__all__ = [
    "embeddings", "EventBus", "InMemoryBus", "RedisBus", "get_bus",
    "Event", "Detection", "BoundingBox", "Frame", "Violation", "Alert",
    "Incident", "RemediationResult", "RemediationStep", "RedactionResult",
    "DriftReport", "ServiceHealth", "new_id",
]
