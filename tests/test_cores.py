"""Offline tests for every service core (no network, no third-party deps)."""

import asyncio

from aetheris.agents.remediation import SelfHealingAgent
from aetheris.common.embeddings import embed
from aetheris.common.eventbus import InMemoryBus
from aetheris.common.models import Event, Frame, Incident
from aetheris.mlops.drift import DriftMonitor, population_stability_index
from aetheris.privacy.redactor import Redactor
from aetheris.privacy.proxy import PrivacyProxy
from aetheris.vision.compliance import ComplianceEngine
from aetheris.vision.detector import MockDetector
from aetheris.vision.pipeline import VisionPipeline


# -- event bus ---------------------------------------------------------------
def test_bus_wildcard_pubsub():
    bus = InMemoryBus()
    seen = []
    bus.subscribe("vision.*", lambda e: seen.append(e.topic))
    asyncio.run(bus.publish(Event(topic="vision.alert", payload={})))
    asyncio.run(bus.publish(Event(topic="mlops.retrain", payload={})))
    assert seen == ["vision.alert"]
    assert len(bus.recent("vision.*")) == 1


# -- vision ------------------------------------------------------------------
def test_detector_is_deterministic():
    d = MockDetector()
    f = Frame(camera_id="c1", zone="z", signature=[0.9, 0.1, 0, 0, 0, 0, 0, 0])
    assert [x.label for x in d.detect(f)] == [x.label for x in d.detect(f)]
    assert any(x.label == "person_no_hardhat" for x in d.detect(f))


def test_pipeline_flags_ppe_and_restricted_zone():
    pipe = VisionPipeline(MockDetector(), ComplianceEngine())
    frame = Frame(camera_id="cam-1", zone="substation", signature=[0.92, 0.1, 0, 0, 0, 0, 0, 0])
    alert = asyncio.run(pipe.process(frame))
    assert alert is not None and alert.severity == "critical"
    rules = {v.rule for v in alert.violations}
    assert "PPE_HARD_HAT" in rules and "RESTRICTED_ZONE" in rules


def test_pipeline_clears_when_compliant():
    pipe = VisionPipeline(MockDetector(), ComplianceEngine())
    frame = Frame(camera_id="cam-2", zone="lobby", signature=[0.9, 0.9, 0, 0, 0, 0, 0, 0])  # person WITH hard hat
    assert asyncio.run(pipe.process(frame)) is None


# -- agents ------------------------------------------------------------------
def test_self_healing_runs_playbook():
    agent = SelfHealingAgent()
    res = asyncio.run(agent.heal(Incident(service="vision-edge", kind="high_cpu", detail="cpu>90")))
    assert res.resolved is True
    assert [s.action for s in res.steps] == ["scale_out_replicas", "restart_unhealthy_pod"]


def test_self_healing_unknown_kind_uses_default():
    agent = SelfHealingAgent()
    res = asyncio.run(agent.heal(Incident(service="x", kind="mystery", detail="")))
    assert res.steps[0].action == "page_oncall_engineer"


# -- privacy -----------------------------------------------------------------
def test_redactor_masks_pii_and_rehydrates():
    r = Redactor()
    text = "Email jane@corp.com, SSN 123-45-6789, card 4111 1111 1111 1111, call 415-555-0172"
    result, reverse = r.redact(text)
    kinds = {e["type"] for e in result.entities}
    assert {"EMAIL", "SSN", "CREDIT_CARD", "PHONE"} <= kinds
    assert "jane@corp.com" not in result.redacted_text
    assert Redactor.rehydrate(result.redacted_text, reverse) == text


def test_invalid_credit_card_not_masked():
    r = Redactor()
    result, _ = r.redact("card 1234 5678 9012 3456")  # fails Luhn
    assert not any(e["type"] == "CREDIT_CARD" for e in result.entities)


def test_privacy_proxy_never_leaks_raw_pii():
    out = asyncio.run(PrivacyProxy().complete("reach me at bob@acme.io"))
    assert out["pii_masked"] == 1
    assert "bob@acme.io" not in out["sent_to_llm"]
    assert "bob@acme.io" in out["response"]  # rehydrated locally


# -- mlops -------------------------------------------------------------------
def test_psi_zero_for_identical_distributions():
    xs = [i / 10 for i in range(100)]
    assert population_stability_index(xs, list(xs)) < 1e-9


def test_drift_monitor_detects_shift():
    mon = DriftMonitor()
    ref = [embed(f"nominal temperature reading {i}", 128) for i in range(50)]
    same = [embed(f"nominal temperature reading {i + 1}", 128) for i in range(50)]
    diff = [embed(f"critical anomaly alarm spike {i}", 128) for i in range(50)]
    assert mon.compute("m", ref, same).drifted is False
    hot = mon.compute("m", ref, diff)
    assert hot.drifted is True and hot.should_retrain is True
