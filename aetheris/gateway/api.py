"""AETHERIS Core Gateway.

The single entry point in front of the four services. It aggregates health,
exposes a service catalog, and serves a small landing page. Downstream URLs are
configured via environment (defaults match docker-compose).
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

SERVICES = {
    "vision-edge": os.environ.get("VISION_URL", "http://vision-edge:8000"),
    "agent-orchestrator": os.environ.get("AGENTS_URL", "http://agent-orchestrator:8000"),
    "data-privacy-proxy": os.environ.get("PRIVACY_URL", "http://data-privacy-proxy:8000"),
    "mlops-drift-watcher": os.environ.get("MLOPS_URL", "http://mlops-drift-watcher:8000"),
}

app = FastAPI(title="AETHERIS · core-gateway", version="0.1.0",
              description="Unified gateway for the AETHERIS infrastructure platform.")


@app.get("/health")
def health() -> dict:
    return {"service": "core-gateway", "status": "ok", "downstreams": list(SERVICES)}


@app.get("/api/services")
def services() -> dict:
    return SERVICES


@app.get("/api/status")
async def status() -> dict:
    """Best-effort aggregate health of every downstream service."""
    try:
        import httpx
    except ImportError:
        return {"gateway": "ok", "note": "install httpx for downstream status", "services": {}}

    results: dict[str, dict] = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health")
                results[name] = {"reachable": r.status_code == 200, **r.json()}
            except Exception as exc:  # noqa: BLE001
                results[name] = {"reachable": False, "error": str(exc)}
    healthy = sum(1 for r in results.values() if r.get("reachable"))
    return {"gateway": "ok", "healthy": f"{healthy}/{len(SERVICES)}", "services": results}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    rows = "".join(
        f'<tr><td><b>{name}</b></td><td><code>{url}</code></td>'
        f'<td><a href="{url}/docs">API docs</a></td></tr>'
        for name, url in SERVICES.items()
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>AETHERIS</title>
<style>body{{font-family:system-ui;background:#0b0e14;color:#e7edf5;max-width:820px;margin:40px auto;padding:0 20px}}
h1{{letter-spacing:.5px}} code{{color:#67e8c3}} table{{width:100%;border-collapse:collapse;margin-top:16px}}
td{{padding:10px;border-bottom:1px solid #232c40}} a{{color:#6b8afd}}</style></head>
<body><h1>🛰️ AETHERIS Core Gateway</h1>
<p>Autonomous Enterprise Thermal, Environmental &amp; Robotic Infrastructure System.</p>
<table><tr><th align=left>Service</th><th align=left>URL</th><th></th></tr>{rows}</table>
<p style="color:#8a97ab;margin-top:20px">GET <code>/api/status</code> for aggregate health.</p>
</body></html>"""
