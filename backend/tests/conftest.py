import asyncio
import os
import subprocess
import sys

import httpx
import pytest
import pytest_asyncio

os.environ["AB_DATABASE_URL"] = os.getenv(
    "AB_TEST_DATABASE_URL", "sqlite+aiosqlite:///./.runtime/unit-tests.db"
)
os.environ["AB_REDIS_URL"] = os.getenv("AB_TEST_REDIS_URL", "redis://redis:6379/2")
os.environ["AB_MCP_TRANSPORT"] = "stdio"
os.environ["AB_MLFLOW_TRACKING_URI"] = ""


@pytest.fixture(scope="session", autouse=True)
def migrate():
    from pathlib import Path

    Path(".runtime").mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest_asyncio.fixture
async def client():
    from agentbench.main import app
    from agentbench.schemas import uid

    transport = httpx.ASGITransport(app=app, client=("pytest-" + uid(), 12345))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as instance:
        yield instance


@pytest_asyncio.fixture(scope="session")
async def sandbox():
    from agentbench.mcp.client import Sandbox

    ready, stop = asyncio.Queue(), asyncio.Event()

    async def owner():
        async with Sandbox("stdio") as instance:
            await ready.put(instance)
            await stop.wait()

    task = asyncio.create_task(owner())
    instance = await asyncio.wait_for(ready.get(), 45)
    yield instance
    stop.set()
    await task


@pytest_asyncio.fixture
async def workspace(client):
    from agentbench.schemas import uid

    response = await client.post(
        "/api/auth/register",
        json={"email": f"test-{uid()}@example.org", "password": "pytest-local-password-2026!"},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = "Bearer " + token
    response = await client.post("/api/projects", json={"name": "Test project"})
    assert response.status_code == 201, response.text
    return response.json()["id"]
