<div align="center">

# 🛰️ AETHERIS

### Autonomous Enterprise Thermal, Environmental & Robotic Infrastructure System

A production-grade platform that fuses **edge computer vision**, **self-healing multi-agent operations**, a **PII-masking privacy firewall**, and **real-time MLOps drift monitoring** into one unified infrastructure system for industrial complexes, data centers, and corporate campuses.

[![CI](https://github.com/avase33/aetheris/actions/workflows/ci.yml/badge.svg)](https://github.com/avase33/aetheris/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009485)](https://fastapi.tiangolo.com)
[![Kubernetes](https://img.shields.io/badge/deploy-Kubernetes-326ce5)](deploy/k8s/aetheris.yaml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![core deps](https://img.shields.io/badge/core%20runtime%20deps-0-brightgreen)](pyproject.toml)

</div>

---

```
                  [ AETHERIS CORE GATEWAY ]
                             │
       ┌─────────────────────┼─────────────────────┐
       ▼                     ▼                     ▼
[ vision-edge ]      [ agent-orchestrator ]  [ mlops-drift-watcher ]
 Edge CV & compliance   Self-healing agents    Drift + retrain triggers
                             │
                      [ data-privacy-proxy ]
                       PII firewall for LLM egress
```

AETHERIS is a **monorepo of four decoupled microservices** behind a core gateway,
sharing one common library (domain models + event bus + embeddings). Each service
is an independent FastAPI app; they coordinate over an event bus.

It's **offline-first**: deterministic mocks stand in for the GPU detector, the
message broker, and the LLM, so the whole platform runs, demos, and passes CI
with **zero external infrastructure** — then swaps in Triton/PyTorch, Kafka/Redis,
Ollama, and Postgres/pgvector for production via env vars.

```bash
pip install -e .
python -m aetheris demo        # end-to-end walkthrough across all four services
```

## 🧱 The services

| Service | Does | Highlights |
|---|---|---|
| **`vision-edge`** | Edge CV compliance monitoring + alerting | Pluggable detector (mock ↔ Triton), rules engine (PPE / fire / restricted-zone / spill), event-published alerts |
| **`agent-orchestrator`** | Self-healing operations | **State-graph** workflow (diagnose → act → verify → retry/escalate) with per-incident playbooks |
| **`data-privacy-proxy`** | PII firewall for LLM egress | Detects & masks email/phone/**Luhn-checked cards**/SSN/IP/keys; forwards only sanitized text; rehydrates locally |
| **`mlops-drift-watcher`** | Model observability | **PSI + centroid-cosine drift** over embedding windows; auto retrain triggers; SQLite model registry |
| **`core-gateway`** | Unified entry point | Aggregates downstream health, service catalog, landing page |

## 🚀 Run it

### Offline demo (no infra)
```bash
python -m aetheris demo
```
```
[1] vision-edge — ALERT [critical] 2 compliance violation(s) in substation
      - PPE_HARD_HAT: Person detected without required hard hat (PPE).
      - RESTRICTED_ZONE: Person detected in restricted zone 'substation'.
[2] agent-orchestrator — OK scale_out_replicas / OK restart_unhealthy_pod → resolved=True
[3] data-privacy-proxy — masked 4 entities before egress
[4] mlops-drift-watcher — PSI=0.83 centroid_drift=0.91 drifted=True retrain=True
```

### Run a single service
```bash
pip install -e ".[server]"
aetheris serve gateway        # or: vision | agents | privacy | mlops
# → http://127.0.0.1:8000/docs
```

### The whole platform (Docker Compose)
```bash
docker compose -f deploy/docker-compose.yml up --build
# gateway :8000  +  4 services  +  redis  +  postgres
```

### Kubernetes
```bash
kubectl apply -f deploy/k8s/aetheris.yaml   # Deployments, Services, probes, limits, HPA
```

## 🔌 Example calls

```bash
# Vision: submit an edge frame signature -> compliance verdict
curl -X POST localhost:8000/process -H 'content-type: application/json' \
  -d '{"camera_id":"cam-12","zone":"substation","signature":[0.95,0.05,0,0,0,0,0,0]}'

# Privacy: only sanitized text ever leaves the network
curl -X POST localhost:8000/complete -H 'content-type: application/json' \
  -d '{"prompt":"email jane@corp.com, SSN 123-45-6789, card 4111 1111 1111 1111"}'

# Self-healing: remediate an incident
curl -X POST localhost:8000/heal -H 'content-type: application/json' \
  -d '{"service":"vision-edge","kind":"high_cpu"}'

# Drift: compare reference vs current embeddings
curl -X POST localhost:8000/drift -H 'content-type: application/json' \
  -d '{"model":"thermal-v1","reference_texts":["nominal ..."],"current_texts":["anomaly ..."]}'
```

## 🛠️ Tech stack

**Orchestration:** Kubernetes (+HPA), Docker, docker-compose, GitHub Actions ·
**AI/ML:** PyTorch/**Triton** (detector adapter), **Ollama** (LLM egress),
hashing embeddings + PSI drift · **Agents:** LangGraph-style async state graph ·
**Data/Eventing:** **Kafka**/**Redis** event bus, **PostgreSQL/pgvector**,
SQLite · **API:** FastAPI + Pydantic — all optional behind offline mocks.

## 🔬 Tested

Every service core is covered by tests that need **no network and no deps** —
the CV pipeline & compliance rules, the self-healing state graph, the PII
redactor (including Luhn validation and the "no raw PII leaves" guarantee), the
drift math (PSI + centroid), and the event bus. Each FastAPI app is smoke-tested
with `TestClient`, and the Kubernetes manifests are validated in CI.

```bash
pip install -e ".[dev,server]"
pytest -q
```

CI runs the suite on Python 3.10–3.12, runs the offline demo, imports every
service app, builds the Docker image, and parses the k8s manifests.

## 🗺️ Roadmap

- [ ] Real YOLO/Triton detector + video-stream ingestion
- [ ] Kafka-backed event sourcing with a replayable log
- [ ] pgvector-backed embedding store for drift history
- [ ] Grafana/Prometheus dashboards + OpenTelemetry tracing
- [ ] Policy-as-code (OPA) for compliance rules

## 📄 License

MIT © Akhil Vase — see [LICENSE](LICENSE).
