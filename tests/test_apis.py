"""Smoke tests for each service's FastAPI app (needs server extras)."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402


def test_vision_service():
    from aetheris.vision.api import app
    c = TestClient(app)
    assert c.get("/health").json()["service"] == "vision-edge"
    r = c.post("/process", json={"camera_id": "cam1", "zone": "substation",
                                 "signature": [0.95, 0.05, 0, 0, 0, 0, 0, 0]})
    assert r.json()["status"] == "violation"


def test_agents_service():
    from aetheris.agents.api import app
    c = TestClient(app)
    r = c.post("/heal", json={"service": "vision-edge", "kind": "disk_pressure"})
    body = r.json()
    assert body["resolved"] is True and len(body["steps"]) == 2


def test_privacy_service():
    from aetheris.privacy.api import app
    c = TestClient(app)
    r = c.post("/complete", json={"prompt": "email me at x@y.com"})
    body = r.json()
    assert body["pii_masked"] == 1 and "x@y.com" not in body["sent_to_llm"]


def test_mlops_service(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHERIS_MLOPS_DB", str(tmp_path / "m.db"))
    import importlib
    import aetheris.mlops.api as m
    importlib.reload(m)
    c = TestClient(m.app)
    c.post("/register", json={"name": "det", "version": "1", "accuracy": 0.9})
    r = c.post("/drift", json={"model": "det",
                               "reference_texts": [f"nominal {i}" for i in range(20)],
                               "current_texts": [f"anomaly spike critical {i}" for i in range(20)]})
    assert r.json()["drifted"] is True


def test_gateway_service():
    from aetheris.gateway.api import app
    c = TestClient(app)
    assert c.get("/health").json()["service"] == "core-gateway"
    assert "vision-edge" in c.get("/api/services").json()
