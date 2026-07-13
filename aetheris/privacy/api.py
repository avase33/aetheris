"""FastAPI app for the aetheris-data-privacy-proxy service."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from ..config import Settings
from .proxy import PrivacyProxy, get_llm
from .redactor import Redactor

settings = Settings.from_env()
proxy = PrivacyProxy(llm=get_llm(settings.llm_backend, url=settings.ollama_url), redactor=Redactor())

app = FastAPI(title="AETHERIS · data-privacy-proxy", version="0.1.0",
              description="PII-masking firewall for LLM egress.")


class RedactIn(BaseModel):
    text: str = Field(..., examples=["Email me at john.doe@acme.com or call 415-555-0172"])


class CompleteIn(BaseModel):
    prompt: str = Field(..., examples=["Summarize account for jane@corp.com, SSN 123-45-6789"])


@app.get("/health")
def health() -> dict:
    return {"service": "data-privacy-proxy", "status": "ok", "llm": settings.llm_backend}


@app.post("/redact")
def redact(body: RedactIn) -> dict:
    result, _ = proxy.redactor.redact(body.text)
    return {"redacted": result.redacted_text, "entities": result.entities, "count": result.count}


@app.post("/complete")
async def complete(body: CompleteIn) -> dict:
    return await proxy.complete(body.prompt)


@app.get("/stats")
def stats() -> dict:
    return proxy.stats()
