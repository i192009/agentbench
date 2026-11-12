"""Terminate only the Celery child executing this probe's synthetic run.

Run inside the worker container. The probe explicitly shortens its abandoned lease
to two seconds to exercise expiry without waiting the normal run-timeout lease.
No other run, project slot, worker parent, or external service is terminated.
"""

import asyncio
import json
import os
import signal
from pathlib import Path
from time import perf_counter

import httpx
from agentbench.config import settings
from agentbench.schemas import uid
from agentbench.workers import celery
from redis.asyncio import Redis


async def main():
    cfg = settings()
    stamp = uid()[:8]
    async with httpx.AsyncClient(base_url="http://backend:8000", timeout=30) as client:
        response = await client.post(
            "/api/auth/login", json={"email": "demo@agentbench.local", "password": cfg.demo_password}
        )
        response.raise_for_status()
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        project = (await client.post("/api/projects", json={"name": "Worker recovery probe " + stamp})).json()
        root = "/api/projects/" + project["id"]
        av = (await client.post(root + "/agents", json={"name": "Recovery probe", "version": "v1"})).json()[
            "version"
        ]
        dataset = json.loads(Path("datasets/ci.json").read_text())
        dataset["name"] = "recovery-probe-" + stamp
        cases = []
        for index in range(24):
            case = json.loads(json.dumps(dataset["cases"][index % 12]))
            case["id"] = f"recovery-{index:03}"
            case["fixture"]["fault"] = {"tool": "get_financial_statements", "kind": "slow", "seconds": 1}
            cases.append(case)
        dataset["cases"] = cases
        response = await client.post(root + "/datasets", json=dataset)
        response.raise_for_status()
        dv = response.json()["version"]
        response = await client.post(
            root + "/runs", json={"agent_version_id": av["id"], "dataset_version_id": dv["id"]}
        )
        response.raise_for_status()
        run_id = response.json()["id"]
        await client.post(root + f"/runs/{run_id}/start")
        before = []
        for _ in range(300):
            detail = (await client.get(root + f"/runs/{run_id}")).json()
            if 4 <= detail["completed"] < 24:
                before = (await client.get(root + f"/runs/{run_id}/results")).json()["items"]
                break
            await asyncio.sleep(0.1)
        assert before, "Probe needs completed cases before termination"
        active = await asyncio.to_thread(celery.control.inspect(timeout=2).active)
        task = next(
            t
            for tasks in (active or {}).values()
            for t in tasks
            if t["name"] == "agentbench.evaluate" and t["args"] == [run_id]
        )
        pid = task["worker_pid"]
        assert isinstance(pid, int) and pid > 1 and pid != os.getpid()
        redis = Redis.from_url(cfg.redis_url)
        key = "ab:run:" + run_id
        lease = await redis.get(key)
        assert lease, "Probe must own an active run lease"
        started = perf_counter()
        os.kill(pid, signal.SIGKILL)
        await redis.expire(key, 2)
        for slot in range(cfg.project_concurrency):
            slot_key = f"ab:project:{project['id']}:slot:{slot}"
            if await redis.get(slot_key) == lease:
                await redis.expire(slot_key, 2)
        await redis.aclose()
        for _ in range(360):
            detail = (await client.get(root + f"/runs/{run_id}")).json()
            if detail["status"] in ["COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS"]:
                break
            await asyncio.sleep(0.5)
        assert detail["status"] == "COMPLETED", detail
        assert detail["summary"]["gate"]["status"] == "PASS", detail["summary"]
        after = (await client.get(root + f"/runs/{run_id}/results")).json()["items"]
        assert len(after) == 24 and len({r["case_id"] for r in after}) == 24
        originals = {r["case_id"]: r["body"]["attempt_id"] for r in before}
        assert all(
            r["body"]["attempt_id"] == originals[r["case_id"]] for r in after if r["case_id"] in originals
        )
        report = {
            "run_id": run_id,
            "project_id": project["id"],
            "terminated_child_pid": pid,
            "completed_before_termination": len(before),
            "completed_after_recovery": len(after),
            "preserved_attempt_ids": True,
            "gate": detail["summary"]["gate"]["status"],
            "recovery_seconds": perf_counter() - started,
            "probe_lease_seconds": 2,
            "normal_lease_seconds": cfg.run_timeout_seconds + 90,
            "note": "Only the probe lease was shortened; normal crash recovery waits for the configured run-timeout lease to expire.",
        }
        path = Path(".runtime/reliability.json")
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
