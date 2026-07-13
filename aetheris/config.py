"""Central configuration resolved from the environment.

Offline-first defaults: an in-memory event bus, a deterministic mock detector,
a mock LLM, and hashing embeddings — so any service boots with zero external
infrastructure. Point the adapters at Kafka/Redis/Triton/Ollama/Postgres for
production via environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = False

    # Event bus: memory | redis | kafka
    bus_backend: str = "memory"
    redis_url: str = "redis://localhost:6379"
    kafka_brokers: str = "localhost:9092"

    # Vision detector: mock | triton
    detector_backend: str = "mock"
    triton_url: str = "localhost:8001"

    # LLM egress: mock | ollama | openai
    llm_backend: str = "mock"
    ollama_url: str = "http://localhost:11434"

    # Data layer
    database_url: str = "sqlite:///aetheris.db"

    # Thresholds
    compliance_min_confidence: float = 0.5
    drift_psi_threshold: float = 0.2
    drift_retrain_threshold: float = 0.25
    embedding_dim: int = 256

    @classmethod
    def from_env(cls) -> "Settings":
        g = os.environ.get
        return cls(
            environment=g("AETHERIS_ENV", "development"),
            log_level=g("AETHERIS_LOG_LEVEL", "INFO"),
            log_json=g("AETHERIS_LOG_JSON", "false").lower() in ("1", "true", "yes"),
            bus_backend=g("AETHERIS_BUS", "memory"),
            redis_url=g("REDIS_URL", "redis://localhost:6379"),
            kafka_brokers=g("KAFKA_BROKERS", "localhost:9092"),
            detector_backend=g("AETHERIS_DETECTOR", "mock"),
            triton_url=g("TRITON_URL", "localhost:8001"),
            llm_backend=g("AETHERIS_LLM", "mock"),
            ollama_url=g("OLLAMA_URL", "http://localhost:11434"),
            database_url=g("DATABASE_URL", "sqlite:///aetheris.db"),
            compliance_min_confidence=float(g("AETHERIS_MIN_CONF", "0.5")),
            drift_psi_threshold=float(g("AETHERIS_PSI", "0.2")),
            drift_retrain_threshold=float(g("AETHERIS_RETRAIN", "0.25")),
            embedding_dim=int(g("AETHERIS_EMBED_DIM", "256")),
        )
