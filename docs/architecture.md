# AETHERIS architecture

AETHERIS is a monorepo of four decoupled services behind a core gateway, sharing
one common library (models + event bus + embeddings). Every service is an
independent FastAPI app with its own core logic; they communicate through events.

```
                        ┌──────────────────────────┐
        clients ─────►  │   AETHERIS CORE GATEWAY   │  aggregates health, routes
                        └────────────┬─────────────┘
             ┌──────────────┬────────┼────────┬──────────────┐
             ▼              ▼                  ▼              ▼
    ┌────────────────┐ ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
    │ vision-edge    │ │ agent-         │ │ data-privacy │ │ mlops-drift-   │
    │ CV compliance  │ │ orchestrator   │ │ -proxy       │ │ watcher        │
    │ + alerts       │ │ self-healing   │ │ PII firewall │ │ drift + retrain│
    └───────┬────────┘ └───────┬────────┘ └──────┬───────┘ └───────┬────────┘
            │  events          │                 │                 │
            └──────────────────┴───── Event Bus ──┴─────────────────┘
                       (in-memory · Redis · Kafka)

  Shared: models, event bus, hashing embeddings
  Deploy: Docker image (SERVICE env) · docker-compose · Kubernetes (+HPA)
```

## Services

### vision-edge (`aetheris.vision`)
A `Detector` (deterministic `MockDetector`; `TritonDetector` for GPU) turns a
frame into detections; a `ComplianceEngine` applies PPE / fire / restricted-zone
/ spill rules; the `VisionPipeline` raises `Alert`s and publishes `vision.alert`.

### agent-orchestrator (`aetheris.agents`)
A `SelfHealingAgent` runs a **state graph** (diagnose → act → verify → retry /
escalate). Each incident kind maps to a playbook; actions execute one at a time
until resolved or the budget is spent. Publishes `agents.remediation`.

### data-privacy-proxy (`aetheris.privacy`)
A `Redactor` detects & masks PII (email, phone, SSN, Luhn-validated cards, IPs,
API keys) with reversible placeholders. The `PrivacyProxy` forwards **only the
sanitized text** to the LLM and rehydrates placeholders locally — raw PII never
leaves the network.

### mlops-drift-watcher (`aetheris.mlops`)
A `DriftMonitor` computes **PSI** over per-sample cosine-to-reference-centroid,
plus **centroid cosine drift**, between reference and current embedding windows.
Past threshold it flags drift; past the retrain threshold it emits
`mlops.retrain` and records the event in a SQLite model registry.

## Event bus

`EventBus` is the seam between services. `InMemoryBus` (offline, wildcard topics
like `vision.*`) powers dev/tests; `RedisBus`/`KafkaBus` back it in production —
swap by setting `AETHERIS_BUS`.

## Deploying

- **One image, many services** — the Docker `CMD` runs `aetheris serve $SERVICE`.
- **docker-compose** brings up the gateway, all four services, Redis and Postgres.
- **Kubernetes** — `deploy/k8s/aetheris.yaml` has Deployments/Services for each,
  readiness/liveness probes, resource limits, and an HPA on the CV workhorse.

## Offline-first

Deterministic mocks replace the GPU detector, the broker, and the LLM, so the
whole platform runs, demos (`aetheris demo`), and passes CI with **zero external
infrastructure** — real adapters wire in via environment variables.
