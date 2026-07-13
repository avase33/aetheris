"""Embeddings-drift and accuracy monitoring.

Computes two complementary drift signals between a reference window and a current
window of embeddings:

* **PSI** (Population Stability Index) over each sample's cosine similarity to the
  reference centroid — the standard ML-monitoring drift metric.
* **Centroid cosine drift** — how far the current distribution's centroid has
  rotated from the reference centroid.

If either exceeds its threshold, drift is flagged; past the retrain threshold it
recommends a CI/CD retrain. All pure Python.
"""

from __future__ import annotations

import math

from ..common.embeddings import centroid, cosine
from ..common.models import DriftReport


def population_stability_index(reference: list[float], current: list[float], bins: int = 10) -> float:
    if not reference or not current:
        return 0.0
    lo, hi = min(reference + current), max(reference + current)
    if hi == lo:
        return 0.0
    width = (hi - lo) / bins
    eps = 1e-6

    def dist(values: list[float]) -> list[float]:
        counts = [0] * bins
        for v in values:
            idx = min(int((v - lo) / width), bins - 1)
            counts[idx] += 1
        return [c / len(values) for c in counts]

    ref_d, cur_d = dist(reference), dist(current)
    psi = 0.0
    for r, c in zip(ref_d, cur_d):
        r, c = max(r, eps), max(c, eps)
        psi += (c - r) * math.log(c / r)
    return psi


class DriftMonitor:
    def __init__(self, psi_threshold: float = 0.2, retrain_threshold: float = 0.25):
        self.psi_threshold = psi_threshold
        self.retrain_threshold = retrain_threshold

    def compute(self, model: str, reference: list[list[float]], current: list[list[float]]) -> DriftReport:
        ref_c = centroid(reference)
        cur_c = centroid(current)
        centroid_drift = round(1.0 - cosine(ref_c, cur_c), 6) if ref_c and cur_c else 0.0

        ref_scores = [cosine(v, ref_c) for v in reference]
        cur_scores = [cosine(v, ref_c) for v in current]
        psi = population_stability_index(ref_scores, cur_scores)

        drifted = psi >= self.psi_threshold or centroid_drift >= self.psi_threshold
        should_retrain = psi >= self.retrain_threshold or centroid_drift >= self.retrain_threshold
        return DriftReport(model=model, psi=psi, centroid_cosine_drift=centroid_drift,
                           drifted=drifted, should_retrain=should_retrain,
                           n_reference=len(reference), n_current=len(current))


class AccuracyMonitor:
    """Rolling accuracy tracker that flags regressions below a baseline."""

    def __init__(self, baseline: float, tolerance: float = 0.05, window: int = 100):
        self.baseline = baseline
        self.tolerance = tolerance
        self.window = window
        self._correct: list[int] = []

    def observe(self, y_true: int, y_pred: int) -> None:
        self._correct.append(1 if y_true == y_pred else 0)
        self._correct = self._correct[-self.window :]

    @property
    def accuracy(self) -> float:
        return sum(self._correct) / len(self._correct) if self._correct else 0.0

    @property
    def regressed(self) -> bool:
        return bool(self._correct) and self.accuracy < self.baseline - self.tolerance
