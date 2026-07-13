"""Object detectors for the vision-edge service.

``MockDetector`` is deterministic and offline: it turns a frame's compact numeric
signature into plausible detections, so compliance rules can fire in tests and
demos without a GPU. ``TritonDetector`` is the production adapter.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from ..common.models import BoundingBox, Detection, Frame

# Signature slots the mock detector interprets (index -> semantic meaning).
_SLOTS = ["person", "hardhat", "fire", "smoke", "vehicle", "spill", "intrusion", "temp"]


class Detector(ABC):
    name: str = "detector"

    @abstractmethod
    def detect(self, frame: Frame) -> list[Detection]: ...


def _signature(frame: Frame) -> list[float]:
    if frame.signature:
        return (frame.signature + [0.0] * len(_SLOTS))[: len(_SLOTS)]
    # Deterministic pseudo-signature from ids so demos are reproducible.
    seed = int(hashlib.md5(f"{frame.camera_id}:{frame.zone}:{frame.id}".encode()).hexdigest(), 16)
    return [((seed >> (i * 8)) & 0xFF) / 255.0 for i in range(len(_SLOTS))]


class MockDetector(Detector):
    name = "mock"

    def __init__(self, min_confidence: float = 0.5):
        self.min_confidence = min_confidence

    def detect(self, frame: Frame) -> list[Detection]:
        s = _signature(frame)
        out: list[Detection] = []

        def add(label: str, conf: float, i: int) -> None:
            if conf >= self.min_confidence:
                out.append(Detection(label, conf, BoundingBox(0.1 * i, 0.1 * i, 0.2, 0.3)))

        person = s[0]
        if person >= 0.5:
            add("person", person, 0)
            # A person with a low "hardhat" signal => detected as not wearing PPE.
            if s[1] < 0.4:
                add("person_no_hardhat", 1.0 - s[1], 1)
            else:
                add("person_hardhat", s[1], 1)
        if s[2] >= 0.75:
            add("fire", s[2], 2)
        if s[3] >= 0.7:
            add("smoke", s[3], 3)
        if s[4] >= 0.6:
            add("vehicle", s[4], 4)
        if s[5] >= 0.7:
            add("spill", s[5], 5)
        return out


class TritonDetector(Detector):  # pragma: no cover - needs Triton
    name = "triton"

    def __init__(self, url: str, model: str = "yolov8"):
        self.url = url
        self.model = model
        try:
            import tritonclient.grpc  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("pip install 'aetheris[triton]' for the Triton detector") from exc

    def detect(self, frame: Frame) -> list[Detection]:
        raise NotImplementedError("wire Triton Inference Server gRPC here")


def get_detector(backend: str = "mock", min_confidence: float = 0.5, **kwargs) -> Detector:
    if backend == "triton":
        return TritonDetector(kwargs.get("url", "localhost:8001"))
    return MockDetector(min_confidence=min_confidence)
