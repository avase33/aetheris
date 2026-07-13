"""Dependency-free hashing embeddings + vector math for the drift watcher.

Deterministic and offline; swap for a real model (sentence-transformers / an
Ollama or Triton embedding endpoint) by implementing ``embed``.
"""

from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")


def embed(text: str, dim: int = 256) -> list[float]:
    vec = [0.0] * dim
    for tok in _TOKEN.findall(text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    c = [sum(v[j] for v in vectors) / len(vectors) for j in range(dim)]
    norm = math.sqrt(sum(x * x for x in c))
    return [x / norm for x in c] if norm else c


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
