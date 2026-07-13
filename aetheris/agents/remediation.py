"""Self-healing multi-agent remediation over a state graph.

Given an incident, the workflow diagnoses it, selects a playbook, and executes
remediation actions one at a time — re-checking after each — until the incident
is resolved or the attempt budget is spent (then it escalates). This models the
LangGraph/CrewAI-style self-healing operations the platform is meant to run.
"""

from __future__ import annotations

from typing import Any

from ..common.eventbus import EventBus
from ..common.models import Event, Incident, RemediationResult, RemediationStep
from ..logging_setup import get_logger
from .graph import END, StateGraph

log = get_logger("agents")

# Ordered playbooks; the LAST action is the one that resolves the incident.
PLAYBOOKS: dict[str, list[str]] = {
    "high_cpu": ["scale_out_replicas", "restart_unhealthy_pod"],
    "drift_detected": ["shadow_new_model", "trigger_retrain_pipeline"],
    "camera_offline": ["reconnect_rtsp_stream", "failover_to_standby_camera"],
    "disk_pressure": ["purge_temp_cache", "expand_persistent_volume"],
    "high_latency": ["warm_cache", "scale_out_replicas"],
    "cert_expiring": ["rotate_tls_certificate"],
}
DEFAULT_PLAYBOOK = ["page_oncall_engineer"]


class SelfHealingAgent:
    def __init__(self, bus: EventBus | None = None, max_attempts: int = 4):
        self.bus = bus
        self.max_attempts = max_attempts
        self.graph = self._build()

    def _build(self):
        g: StateGraph[dict] = StateGraph()

        async def diagnose(state: dict) -> dict:
            inc: Incident = state["incident"]
            state["plan"] = PLAYBOOKS.get(inc.kind, DEFAULT_PLAYBOOK)
            log.info("Diagnosed %s/%s -> playbook %s", inc.service, inc.kind, state["plan"])
            return state

        async def act(state: dict) -> dict:
            i = state["attempt"]
            action = state["plan"][i]
            state["steps"].append(RemediationStep(action=action, result=f"executed '{action}'", ok=True))
            state["resolved"] = (i == len(state["plan"]) - 1)  # last action is the fix
            return state

        async def escalate(state: dict) -> dict:
            state["steps"].append(RemediationStep(action="escalate", result="paged on-call; auto-heal failed", ok=False))
            state["resolved"] = False
            return state

        def route(state: dict) -> str:
            if state["resolved"]:
                return END
            nxt = state["attempt"] + 1
            if nxt < len(state["plan"]) and nxt < self.max_attempts:
                state["attempt"] = nxt
                return "act"
            return "escalate"

        g.add_node("diagnose", diagnose).add_node("act", act).add_node("escalate", escalate)
        g.set_entry_point("diagnose")
        g.add_edge("diagnose", "act")
        g.add_conditional_edges("act", route)
        g.add_edge("escalate", END)
        return g.compile()

    async def heal(self, incident: Incident) -> RemediationResult:
        state: dict[str, Any] = {"incident": incident, "plan": [], "attempt": 0, "steps": [], "resolved": False}
        state = await self.graph.invoke(state)
        result = RemediationResult(incident_id=incident.id, resolved=state["resolved"], steps=state["steps"])
        log.info("Incident %s resolved=%s in %d steps", incident.id, result.resolved, len(result.steps))
        if self.bus is not None:
            await self.bus.publish(Event(topic="agents.remediation",
                                         payload=result.to_dict(), source="agent-orchestrator"))
        return result
