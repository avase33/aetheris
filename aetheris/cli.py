"""Command-line interface for AETHERIS.

    aetheris serve gateway            # run a service (gateway|vision|agents|privacy|mlops)
    aetheris demo                     # offline end-to-end walkthrough across all services
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from . import __version__

SERVICE_APPS = {
    "gateway": "aetheris.gateway.api:app",
    "vision": "aetheris.vision.api:app",
    "agents": "aetheris.agents.api:app",
    "privacy": "aetheris.privacy.api:app",
    "mlops": "aetheris.mlops.api:app",
}


def cmd_serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Install server extras: pip install 'aetheris[server]'", file=sys.stderr)
        return 1
    target = SERVICE_APPS[args.service]
    uvicorn.run(target, host=args.host, port=args.port, reload=args.reload)
    return 0


async def _demo() -> None:
    from .agents.remediation import SelfHealingAgent
    from .common.embeddings import embed
    from .common.models import Frame, Incident
    from .mlops.drift import DriftMonitor
    from .privacy.proxy import PrivacyProxy
    from .vision.compliance import ComplianceEngine
    from .vision.detector import MockDetector
    from .vision.pipeline import VisionPipeline

    print("== AETHERIS end-to-end demo (offline) ==\n")

    print("[1] vision-edge — compliance monitoring")
    pipe = VisionPipeline(MockDetector(), ComplianceEngine())
    frame = Frame(camera_id="cam-01", zone="substation",
                  signature=[0.92, 0.10, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])  # person, no hard hat, restricted zone
    alert = await pipe.process(frame)
    if alert:
        print(f"    ALERT [{alert.severity}] {alert.message}")
        for v in alert.violations:
            print(f"      - {v.rule}: {v.detail}")

    print("\n[2] agent-orchestrator — self-healing")
    agent = SelfHealingAgent()
    result = await agent.heal(Incident(service="vision-edge", kind="high_cpu", detail="pod CPU > 90%"))
    for s in result.steps:
        print(f"    {'OK ' if s.ok else 'ESC'} {s.action}: {s.result}")
    print(f"    resolved = {result.resolved}")

    print("\n[3] data-privacy-proxy — PII firewall")
    proxy = PrivacyProxy()
    out = await proxy.complete("Contact jane@corp.com or 415-555-0172, SSN 123-45-6789, card 4111 1111 1111 1111")
    print(f"    masked {out['pii_masked']} entities before egress")
    print(f"    sent to LLM: {out['sent_to_llm'][:90]}")

    print("\n[4] mlops-drift-watcher — embeddings drift")
    mon = DriftMonitor()
    ref = [embed(f"routine substation temperature reading {i} nominal", 256) for i in range(60)]
    cur = [embed(f"unexpected anomaly spike alarm event {i} critical", 256) for i in range(60)]
    report = mon.compute("thermal-detector-v1", ref, cur)
    print(f"    PSI={report.psi:.3f} centroid_drift={report.centroid_cosine_drift:.3f} "
          f"drifted={report.drifted} retrain={report.should_retrain}")
    print("\nDemo complete.")


def cmd_demo(args) -> int:
    asyncio.run(_demo())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aetheris", description="AETHERIS enterprise infrastructure platform.")
    p.add_argument("--version", action="version", version=f"AETHERIS {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("serve", help="run a service")
    s.add_argument("service", choices=list(SERVICE_APPS))
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")
    s.set_defaults(func=cmd_serve)

    d = sub.add_parser("demo", help="run the offline end-to-end demo")
    d.set_defaults(func=cmd_demo)
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
