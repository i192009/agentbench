import asyncio
import json
from pathlib import Path

import pytest
from agentbench.database import AgentVersion, Session
from agentbench.database import TestCaseRow as CaseRow
from agentbench.evaluation.orchestration import evaluate_run
from agentbench.schemas import uid
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.integration


async def setup_run(client, project, *, dataset_name=None):
    agent = await client.post(
        f"/api/projects/{project}/agents", json={"name": "API Research " + uid()[:8], "version": "v1"}
    )
    assert agent.status_code == 201, agent.text
    payload = json.loads(Path("datasets/ci.json").read_text())
    payload["name"] = dataset_name or "API dataset " + uid()[:8]
    data = await client.post(f"/api/projects/{project}/datasets", json=payload)
    assert data.status_code == 201, data.text
    body = {
        "agent_version_id": agent.json()["version"]["id"],
        "dataset_version_id": data.json()["version"]["id"],
    }
    created = await client.post(f"/api/projects/{project}/runs", json=body)
    assert created.status_code == 201, created.text
    return created.json(), data.json(), agent.json()


async def test_authentication_refresh_rotation_replay_and_logout(client):
    email = f"auth-{uid()}@example.org"
    creds = {"email": email, "password": "pytest-password-rotation-2026!"}
    assert (await client.get("/api/projects")).status_code == 401
    response = await client.post("/api/auth/register", json=creds)
    assert response.status_code == 201
    old_cookie = client.cookies.get("ab_refresh")
    assert "HttpOnly" in response.headers["set-cookie"]
    assert (
        await client.post("/api/auth/login", json={**creds, "password": "incorrect-password!"})
    ).status_code == 401
    response = await client.post("/api/auth/refresh")
    assert response.status_code == 200
    new_cookie = client.cookies.get("ab_refresh")
    assert new_cookie != old_cookie
    client.cookies.set("ab_refresh", old_cookie, domain="test.local", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401
    client.cookies.set("ab_refresh", new_cookie, domain="test.local", path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401
    login = await client.post("/api/auth/login", json=creds)
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    assert (await client.get("/api/auth/me")).json()["email"] == email
    assert (await client.post("/api/auth/logout")).status_code == 200
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_project_tenant_isolation(client, workspace):
    first_project = workspace
    response = await client.post(
        "/api/auth/register",
        json={"email": f"other-{uid()}@example.org", "password": "pytest-other-tenant-password!"},
    )
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    assert (await client.get(f"/api/projects/{first_project}")).status_code == 404
    assert (await client.get(f"/api/projects/{first_project}/agents")).status_code == 404
    assert (await client.get("/api/projects")).json()["items"] == []


async def test_dataset_freeze_clone_import_export_and_mutation_guard(client, workspace):
    run, data, agent = await setup_run(client, workspace)
    version_id = data["version"]["id"]
    cases = (await client.get(f"/api/projects/{workspace}/dataset-versions/{version_id}/cases")).json()
    body = cases["items"][0]["body"]
    assert (
        await client.put(
            f"/api/projects/{workspace}/dataset-versions/{version_id}/cases/{body['id']}", json=body
        )
    ).status_code == 409
    cloned = await client.post(
        f"/api/projects/{workspace}/dataset-versions/{version_id}/clone?next_version=2"
    )
    assert cloned.status_code == 201
    clone_id = cloned.json()["id"]
    body["input"] += " Updated development question."
    assert (
        await client.put(
            f"/api/projects/{workspace}/dataset-versions/{clone_id}/cases/{body['id']}", json=body
        )
    ).status_code == 200
    diff = await client.get(f"/api/projects/{workspace}/dataset-versions/{version_id}/compare/{clone_id}")
    assert body["id"] in diff.json()["changed"]
    for format in ["json", "jsonl", "csv"]:
        exported = await client.get(
            f"/api/projects/{workspace}/dataset-versions/{clone_id}/export?format={format}"
        )
        assert exported.status_code == 200
        assert "attachment" in exported.headers["content-disposition"]
    async with Session() as db:
        with pytest.raises(DBAPIError):
            await db.execute(
                update(AgentVersion)
                .where(AgentVersion.id == agent["version"]["id"])
                .values(version="overwrite")
            )
        await db.rollback()
        with pytest.raises(DBAPIError):
            await db.execute(update(CaseRow).where(CaseRow.version_id == version_id).values(body={}))
        await db.rollback()


async def test_run_persistence_results_progress_exports_and_idempotency(client, workspace):
    run, data, agent = await setup_run(client, workspace)
    summary = await evaluate_run(run["id"])
    assert summary["gate"]["status"] == "PASS", summary
    again = await evaluate_run(run["id"])
    assert again["count"] == 12
    results = await client.get(f"/api/projects/{workspace}/runs/{run['id']}/results")
    assert results.json()["total"] == 12
    first = results.json()["items"][0]
    trace = await client.get(f"/api/projects/{workspace}/runs/{run['id']}/results/{first['case_id']}/trace")
    assert any(e["event"] == "ToolCalled" for e in trace.json()["execution"]["trace"])
    stream = await client.get(f"/api/projects/{workspace}/runs/{run['id']}/events")
    assert "event: RunCompleted" in stream.text
    for format in ["json", "md", "csv"]:
        response = await client.get(f"/api/projects/{workspace}/runs/{run['id']}/export?format={format}")
        assert response.status_code == 200
    promoted = await client.post(f"/api/projects/{workspace}/runs/{run['id']}/baseline")
    assert promoted.status_code == 201


async def test_cancelled_evaluation_never_executes_cases(client, workspace):
    run, _, _ = await setup_run(client, workspace)
    assert (await client.post(f"/api/projects/{workspace}/runs/{run['id']}/cancel")).status_code == 200
    await evaluate_run(run["id"])
    detail = await client.get(f"/api/projects/{workspace}/runs/{run['id']}")
    assert detail.json()["status"] == "CANCELLED"
    assert detail.json()["completed"] == 0


async def test_cross_project_agent_dataset_ids_rejected(client, workspace):
    _, data, agent = await setup_run(client, workspace)
    project2 = (await client.post("/api/projects", json={"name": "Another project"})).json()["id"]
    response = await client.post(
        f"/api/projects/{project2}/runs",
        json={"agent_version_id": agent["version"]["id"], "dataset_version_id": data["version"]["id"]},
    )
    assert response.status_code == 422


async def test_database_late_duplicate_result_delivery_is_idempotent(client, workspace):
    from agentbench.evaluation.orchestration import persist_result
    from agentbench.schemas import CaseResult, Execution, Metric

    run, _, _ = await setup_run(client, workspace)
    result = CaseResult(
        case_id="duplicate",
        passed=False,
        severity="high",
        execution=Execution(case_id="duplicate"),
        metrics=[Metric(name="safety", score=1, status="PASS")],
    )
    await asyncio.gather(persist_result(run["id"], result), persist_result(run["id"], result))
    rows = await client.get(f"/api/projects/{workspace}/runs/{run['id']}/results")
    assert rows.json()["total"] == 1


async def test_worker_source_mismatch_fails_before_execution(client, workspace, monkeypatch):
    import agentbench.evaluation.orchestration as orchestration

    run, _, _ = await setup_run(client, workspace)
    monkeypatch.setattr(
        orchestration,
        "source_snapshot",
        lambda: {"tree_checksum": "different-worker", "uv_lock_sha256": "different-lock"},
    )
    with pytest.raises(ValueError, match="Worker source"):
        await evaluate_run(run["id"])
    detail = (await client.get(f"/api/projects/{workspace}/runs/{run['id']}")).json()
    assert detail["status"] == "FAILED" and detail["completed"] == 0


async def test_dispatcher_does_not_duplicate_inline_operator_evaluations(client, workspace):
    from agentbench.database import transaction
    from agentbench.schemas import RunRequest
    from agentbench.services.runs import create_run
    from agentbench.workers import queued_runs

    run, _, _ = await setup_run(client, workspace)
    async with transaction() as db:
        inline = await create_run(
            db, workspace, RunRequest.model_validate(run["snapshot"]["request"]), execution_backend="inline"
        )
        inline.status = "RUNNING"
        inline_id = inline.id
    assert inline_id not in await queued_runs()
