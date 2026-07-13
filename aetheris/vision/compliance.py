"""Compliance rules engine — turns detections into policy violations."""

from __future__ import annotations

from ..common.models import Detection, Violation

# Default restricted zones where any person is a violation.
DEFAULT_RESTRICTED = {"substation", "reactor", "server-hot-aisle"}


class ComplianceEngine:
    def __init__(self, restricted_zones: set[str] | None = None):
        self.restricted_zones = restricted_zones or set(DEFAULT_RESTRICTED)

    def evaluate(self, zone: str, detections: list[Detection]) -> list[Violation]:
        labels = {d.label for d in detections}
        by_label = {d.label: d for d in detections}
        violations: list[Violation] = []

        if "person_no_hardhat" in labels:
            violations.append(Violation(
                rule="PPE_HARD_HAT", severity="critical",
                detail="Person detected without required hard hat (PPE).",
                detections=[by_label["person_no_hardhat"]]))

        if "fire" in labels or "smoke" in labels:
            dets = [by_label[k] for k in ("fire", "smoke") if k in by_label]
            violations.append(Violation(
                rule="FIRE_SMOKE", severity="critical",
                detail="Fire or smoke detected in the monitored area.", detections=dets))

        if zone in self.restricted_zones and "person" in labels:
            violations.append(Violation(
                rule="RESTRICTED_ZONE", severity="warning",
                detail=f"Person detected in restricted zone '{zone}'.",
                detections=[by_label["person"]]))

        if "vehicle" in labels and zone in self.restricted_zones:
            violations.append(Violation(
                rule="UNAUTHORIZED_VEHICLE", severity="warning",
                detail=f"Vehicle detected in restricted zone '{zone}'.",
                detections=[by_label["vehicle"]]))

        if "spill" in labels:
            violations.append(Violation(
                rule="CHEMICAL_SPILL", severity="warning",
                detail="Possible spill detected — dispatch cleanup.",
                detections=[by_label["spill"]]))

        return violations

    @staticmethod
    def worst_severity(violations: list[Violation]) -> str:
        order = {"info": 0, "warning": 1, "critical": 2}
        return max((v.severity for v in violations), key=lambda s: order.get(s, 0), default="info")
