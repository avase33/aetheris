"""Privacy proxy: redact PII, forward only the sanitized text to an LLM, then
rehydrate placeholders locally so raw PII never leaves the network.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..logging_setup import get_logger
from .redactor import Redactor

log = get_logger("privacy")


class LLMEgress(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> str: ...


class MockLLM(LLMEgress):
    async def complete(self, prompt: str) -> str:
        # Echoes the (already-redacted) prompt to prove only sanitized text was sent.
        return f"[mock-llm] Received your request. Summary: {prompt[:240]}"


class OllamaLLM(LLMEgress):  # pragma: no cover - network
    def __init__(self, url: str, model: str = "llama3"):
        self.url, self.model = url, model

    async def complete(self, prompt: str) -> str:
        import json
        import urllib.request
        req = urllib.request.Request(
            f"{self.url}/api/generate",
            data=json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode(),
            headers={"content-type": "application/json"})
        import asyncio
        def _call():
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()).get("response", "")
        return await asyncio.to_thread(_call)


def get_llm(backend: str = "mock", **kwargs) -> LLMEgress:
    if backend == "ollama":
        return OllamaLLM(kwargs.get("url", "http://localhost:11434"))
    return MockLLM()


class PrivacyProxy:
    def __init__(self, llm: LLMEgress | None = None, redactor: Redactor | None = None):
        self.llm = llm or MockLLM()
        self.redactor = redactor or Redactor()
        self.requests = 0
        self.entities_masked = 0

    async def complete(self, prompt: str) -> dict:
        self.requests += 1
        result, reverse = self.redactor.redact(prompt)
        self.entities_masked += result.count
        if result.count:
            log.info("Masked %d PII entities before egress", result.count)
        llm_out = await self.llm.complete(result.redacted_text)   # only sanitized text leaves
        rehydrated = self.redactor.rehydrate(llm_out, reverse)
        return {
            "pii_masked": result.count,
            "entities": result.entities,
            "sent_to_llm": result.redacted_text,   # what actually left the network
            "llm_response": llm_out,
            "response": rehydrated,                 # placeholders restored locally
        }

    def stats(self) -> dict:
        return {"requests": self.requests, "entities_masked": self.entities_masked}
