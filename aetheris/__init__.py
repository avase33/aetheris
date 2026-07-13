"""AETHERIS — Autonomous Enterprise Thermal, Environmental & Robotic Infrastructure System.

A production-grade, enterprise-scale monorepo of decoupled microservices around a
core gateway:

* **vision-edge** — edge computer-vision compliance monitoring + alerting
* **agent-orchestrator** — self-healing multi-agent operations
* **data-privacy-proxy** — PII-masking firewall for LLM egress
* **mlops-drift-watcher** — embeddings-drift + accuracy observability with retrain triggers

Every service is a FastAPI app sharing a common event-bus/model library. The
whole platform is **offline-first**: deterministic mocks stand in for GPU
detectors, brokers, and LLMs, so it runs and is fully testable with no external
infrastructure — with real adapters (Triton/PyTorch, Kafka/Redis, Ollama,
pgvector) wired in for production.
"""

from .version import __version__

__all__ = ["__version__"]
