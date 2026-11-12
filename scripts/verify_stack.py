"""Verify actual deployed services, protocol, persisted results and MLflow correspondence."""

import asyncio
import json
from pathlib import Path
from time import perf_counter

import httpx
from agentbench.config import settings
from agentbench.database import Session
from agentbench.mcp.client import Sandbox
from jsonschema import ValidationError
from sqlalchemy import text


async def main():
    cfg = settings()
    proof = {"checks": {}, "live_model_evaluated": False}
    async with httpx.AsyncClient(timeout=30) as client:
        for name, url in [
            ("backend", "http://backend:8000/health/ready"),
            ("frontend", "http://frontend:8080"),
            ("mlflow", "http://mlflow:5000/health"),
            ("prometheus", "http://prometheus:9090/-/ready"),
        ]:
            start = perf_counter()
            response = await client.get(url)
            response.raise_for_status()
            proof["checks"][name] = {
                "http_status": response.status_code,
                "latency_ms": (perf_counter() - start) * 1000,
            }
        async with Sandbox("streamable-http") as sandbox:
            assert len(sandbox.schemas) == 21
            company = await sandbox.raw("get_company_profile", {"company": "ACME", "scenario": {}})
            assert company["company"] == "ACME"
            invalid = False
            try:
                await sandbox.raw("get_company_profile", {"company": 123, "scenario": {}})
            except ValidationError:
                invalid = True
            assert invalid
            proof["checks"]["mcp"] = {
                "transport": "streamable-http",
                "discovered_tools": len(sandbox.schemas),
                "profile": company,
                "invalid_arguments_rejected": invalid,
            }
        unauthorized = await client.post("http://mcp-financial:8000/mcp", json={})
        assert unauthorized.status_code == 401
        proof["checks"]["mcp"]["unauthenticated_status"] = 401
        response = await client.post(
            "http://backend:8000/api/auth/login",
            json={"email": "demo@agentbench.local", "password": cfg.demo_password},
        )
        response.raise_for_status()
        headers = {"Authorization": "Bearer " + response.json()["access_token"]}
        projects = (await client.get("http://backend:8000/api/projects", headers=headers)).json()["items"]
        project = next(p for p in projects if p["name"] == "Agent Reliability Lab")
        root = f"http://backend:8000/api/projects/{project['id']}"
        runs = (await client.get(root + "/runs?limit=100", headers=headers)).json()["items"]
        baseline = next(
            r
            for r in runs
            if r["dataset"] == "financial-research"
            and r["version"] == "v1"
            and r["summary"].get("gate", {}).get("status") == "PASS"
        )
        detail = (await client.get(root + "/runs/" + baseline["id"], headers=headers)).json()
        results = (await client.get(root + "/runs/" + baseline["id"] + "/results", headers=headers)).json()[
            "items"
        ]
        trace_parent = detail["snapshot"].get("trace_context", {}).get("traceparent", "").split("-")
        assert len(trace_parent) == 4, "API must capture a W3C parent span"
        assert results[0]["body"]["execution"]["trace"][0]["trace_id"] == trace_parent[1], (
            "Worker trace must preserve API parent trace"
        )
        proof["checks"]["otel_propagation"] = {
            "run_id": baseline["id"],
            "api_trace_id": trace_parent[1],
            "worker_trace_id": results[0]["body"]["execution"]["trace"][0]["trace_id"],
        }
        assert detail["snapshot"]["source_snapshot"]["tree_checksum"]
        proof["checks"]["source_snapshot"] = {
            "tree_checksum": detail["snapshot"]["source_snapshot"]["tree_checksum"],
            "source_files": len(detail["snapshot"]["source_snapshot"]["files"]),
        }
        events = await client.get(root + "/runs/" + baseline["id"] + "/events", headers=headers)
        assert "event: RunCompleted" in events.text
        proof["checks"]["durable_progress"] = {"completion_event": True}
        metrics = (await client.get("http://backend:8000/metrics")).text
        assert "agentbench_persisted_cases" in metrics
        targets = (await client.get("http://prometheus:9090/api/v1/targets")).json()
        assert any(t["health"] == "up" for t in targets["data"]["activeTargets"])
        proof["checks"]["prometheus"] = {"persisted_case_metrics": True, "scrape_target_up": True}
        from mlflow import MlflowClient

        tracker = MlflowClient(tracking_uri=cfg.mlflow_tracking_uri)
        tracking = detail["summary"]["tracking"]
        actual = await asyncio.to_thread(tracker.get_run, tracking["run_id"])
        assert actual.data.params["agentbench_run_id"] == baseline["id"]
        assert actual.data.metrics["success_rate"] == detail["summary"]["success_rate"]
        traces = await asyncio.to_thread(
            tracker.search_traces, experiment_ids=[tracking["experiment_id"]], max_results=2
        )
        assert traces, "The real MLflow experiment must contain supported traces"
        proof["checks"]["mlflow_correspondence"] = {
            "run_id": actual.info.run_id,
            "agentbench_run_id": baseline["id"],
            "success_rate": actual.data.metrics["success_rate"],
            "traces_found": len(traces),
            "genai_run_id": tracking["genai_evaluation_run_id"],
        }
    async with Session() as db:
        revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
        assert revision == "0002"
        proof["checks"]["postgres_migration"] = {"revision": revision}
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/stack-verification.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
