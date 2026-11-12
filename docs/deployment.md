# Deployment and local development

## Docker: verified path

```bash
python scripts/bootstrap.py
docker compose up --build -d
docker compose ps
docker compose logs --tail 50 backend worker
```

The bootstrap preserves existing `.env`. The migration service runs Alembic and seeds data.
Application data, Redis AOF, checkpoints/artifacts, MLflow artifacts and Prometheus data use
persistent volumes. `docker compose down` preserves them. No destructive volume removal is
part of normal setup or tests.

If reusing a PostgreSQL volume created before the MLflow init script was added, create its
separate database once: `docker compose exec postgres psql -U agentbench -d postgres -c
"CREATE DATABASE mlflow OWNER agentbench"`. A fresh setup does this automatically.

`docker-compose.dev.yml` adds source mounts for iterative development. The default Compose
file builds self-contained images and does not depend on host Python sources.

## Host development

Prerequisites: Python 3.12, uv 0.13.7, Node 24, Docker for PostgreSQL/Redis.

```bash
python scripts/bootstrap.py
docker compose up -d postgres redis
uv sync --frozen --python 3.12
uv run python scripts/local_config.py
uv run --env-file .env.local python -m alembic upgrade head
uv run --env-file .env.local python -m agentbench seed
uv run --env-file .env.local python -m uvicorn agentbench.main:app --port 8010
```

In additional terminals:

```bash
uv run --env-file .env.local python -m celery -A agentbench.workers:celery worker --concurrency=2
uv run --env-file .env.local python -m celery -A agentbench.workers:celery beat --schedule=.runtime/celerybeat
cd frontend
npm ci
npm run dev
```

Windows Celery development should use `--pool=solo --concurrency=1`. This machine's Windows
Application Control blocked a native dependency DLL, so the complete verification ran in
Linux containers; native host execution is not claimed as verified. Node/Git were also absent
from host PATH, so their containerized tools were used. The Docker engine was available.

`local_config.py` derives ignored `.env.local` with loopback database ports and stdio MCP.
The Vite development proxy defaults to http://localhost:8010. Make targets use `.env.local`;
`make install` generates it without overwriting an existing file.

## Live provider configuration

No credentials are required for offline mode. To explicitly enable real LangChain model planning,
set `AB_LIVE_ENABLED=true`, `OPENAI_API_KEY`, `AB_PROVIDER_MODEL`,
`AB_PROVIDER_INPUT_PER_MILLION`, and `AB_PROVIDER_OUTPUT_PER_MILLION`.
The model selects issuer/metric; financial values and calculations remain deterministic.
Freeze that configuration with `python -m agentbench register-live --version live-configured`,
then evaluate with `python -m agentbench eval run --version live-configured --dataset ci-smoke --mode live`.
Choose a new version name when changing provider model or pricing; historical versions cannot be overwritten.
Set `AB_JUDGE_ENABLED=true`, `AB_JUDGE_MODEL`, `AB_JUDGE_INPUT_PER_MILLION` and
`AB_JUDGE_OUTPUT_PER_MILLION` to enable the optional structured judge. Add `judge` to the
requested evaluators through the API. Missing settings produce ERROR, never offline fallback.

External adapters require `AB_EXTERNAL_AGENT_ORIGINS` and the appropriate fixed environment
token. See repository guides for native read-only contracts. No external live instance was tested.

## Reliability and observability

Default run timeout is 1,800 seconds; run/project leases last timeout + 90 seconds. A killed
worker cannot renew work until that lease expires. Celery redelivery and the 15-second durable
dispatcher then resume unfinished cases. Completed results remain immutable and unique.
This favors avoiding overlapping executions over fast failover. Tune only with an explicit
understanding of distributed fencing and idempotency requirements.
Workers reject a queued snapshot when their source tree or dependency lock differs from
the captured revision. Drain evaluation work before upgrading, or retain workers for the matching revision.

The local OTLP HTTP collector receives propagated API/worker/tool/scorer spans. Prometheus
scrapes the backend's process counters and authoritative persisted run/case/queue gauges.
Metrics avoid per-run labels. MLflow uses one server worker to bound the local footprint.

## Browser verification

After `scripts/demo.py` has generated baseline/candidate runs, install the Playwright browser
matching the pinned package (`npx playwright install chromium`) and run:

```bash
cd frontend
AB_DASHBOARD_URL=http://localhost:5173 npm run test:e2e
```

The provided `Dockerfile.e2e` uses an existing browser image; set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE=/ms-playwright/chromium-1208/chrome-linux/chrome`
when using that image. The executed browser test records screenshots and retains failure traces.
