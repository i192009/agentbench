"""Executable acceptance demonstration through authenticated API + Celery + HTTP MCP.

Requires a running Compose stack. Every artifact comes from persisted API results.
"""

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter

import httpx
from agentbench.config import settings


async def main(base_url: str, output: Path, quick: bool = False):
    output.mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        for _attempt in range(60):
            try:
                ready = await client.get("/health/ready")
                if ready.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            await asyncio.sleep(0.5)
        login = await client.post(
            "/api/auth/login", json={"email": "demo@agentbench.local", "password": settings().demo_password}
        )
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
        projects = (await client.get("/api/projects")).json()["items"]
        project = next(p for p in projects if p["name"] == "Agent Reliability Lab")
        root = f"/api/projects/{project['id']}"
        agents = (await client.get(root + "/agents")).json()["items"]
        datasets = (await client.get(root + "/datasets")).json()["items"]
        runs = {}

        async def run(
            name, agent_name, version, dataset, expected_gate="PASS", baseline=None, evaluators=None
        ):
            agent = next(a for a in agents if a["name"] == agent_name)
            avs = (await client.get(root + f"/agents/{agent['id']}/versions")).json()["items"]
            av = next(a for a in avs if a["version"] == version)
            ds = next(d for d in datasets if d["name"] == dataset)
            dv = (await client.get(root + f"/datasets/{ds['id']}/versions")).json()["items"][0]
            request = {
                "agent_version_id": av["id"],
                "dataset_version_id": dv["id"],
                "mode": "offline",
                "evaluators": evaluators or ["deterministic"],
            }
            if baseline:
                request["baseline_id"] = runs[baseline]["id"]
            response = await client.post(root + "/runs", json=request)
            response.raise_for_status()
            identifier = response.json()["id"]
            response = await client.post(root + f"/runs/{identifier}/start")
            response.raise_for_status()
            print(f"Started {name}: {identifier}", flush=True)
            for _ in range(600):
                response = await client.get(root + f"/runs/{identifier}")
                response.raise_for_status()
                detail = response.json()
                if detail["status"] in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"}:
                    break
                await asyncio.sleep(0.5)
            else:
                raise TimeoutError(f"Run {name} did not finish in 5 minutes")
            if detail["status"] == "FAILED":
                raise AssertionError(detail["error"])
            summary = detail["summary"]
            for format in ["json", "md"]:
                response = await client.get(root + f"/runs/{identifier}/export?format={format}")
                response.raise_for_status()
                (output / f"{name}.{format}").write_text(response.text, encoding="utf-8")
            assert summary["gate"]["status"] == expected_gate, (name, summary)
            assert summary["tracking"]["status"] == "RECORDED", summary["tracking"]
            runs[name] = {
                "id": identifier,
                "status": detail["status"],
                "gate": summary["gate"]["status"],
                "passed": summary["passed"],
                "count": summary["count"],
                "safety_failures": summary["safety_violations"],
                "tracking": summary["tracking"],
                "cases_per_second": summary["cases_per_second"],
            }
            print(
                f"{name}: {summary['passed']}/{summary['count']} passed; gate={summary['gate']['status']}; MLflow={summary['tracking']['status']}",
                flush=True,
            )
            return identifier

        baseline = await run("baseline", "Financial Research", "v1", "financial-research")
        promoted = await client.post(root + f"/runs/{baseline}/baseline")
        promoted.raise_for_status()
        await run("candidate", "Financial Research", "v2-faulty", "financial-research", "FAIL", "baseline")
        await run("operations", "Financial Operations", "v1", "financial-operations")
        await run(
            "approval-bypass",
            "Financial Operations",
            "v2-faulty",
            "financial-operations",
            "FAIL",
            "operations",
        )
        await run("adversarial", "Injection Defense", "v1", "adversarial")
        await run(
            "injection-vulnerable", "Injection Defense", "v2-faulty", "adversarial", "FAIL", "adversarial"
        )
        if not quick:
            await run(
                "rag", "Financial Research", "v1", "rag", evaluators=["deterministic", "ragas", "deepeval"]
            )
            await run("workflows", "Workflow Supervisor", "v1", "multi-step")
            await run("finsight", "FinSight AI contract", "v1", "finsight-contract")
            await run(
                "finsight-faulty",
                "FinSight AI contract",
                "v2-faulty",
                "finsight-contract",
                "FAIL",
                "finsight",
            )
            await run("ledgerguard", "LedgerGuard AI contract", "v1", "ledgerguard-contract")
            await run(
                "ledgerguard-faulty",
                "LedgerGuard AI contract",
                "v2-faulty",
                "ledgerguard-contract",
                "FAIL",
                "ledgerguard",
            )
        ci = await run(
            "ci-baseline",
            "Financial Research",
            "v1",
            "ci-smoke",
            evaluators=["deterministic", "ragas", "deepeval"],
        )
        response = await client.get(root + f"/runs/{ci}/export")
        pinned = Path("evaluation/baselines/ci-baseline.json")
        pinned.parent.mkdir(parents=True, exist_ok=True)
        pinned.write_text(response.text, encoding="utf-8")
        proof = {
            "project_id": project["id"],
            "runs": runs,
            "elapsed_seconds": perf_counter() - started,
            "mode": "offline",
            "live_model_reasoning_evaluated": False,
        }
        (output / "demonstration.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
        print(json.dumps(proof, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8010")
    parser.add_argument("--output", type=Path, default=Path("artifacts/demo"))
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.base_url, args.output, args.quick))
