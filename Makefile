SHELL := /bin/sh
DC := docker compose
PY := uv run --env-file .env.local python

.PHONY: install format lint typecheck test test-unit test-integration test-e2e test-adversarial test-regression build up down migrate seed eval-offline eval-live eval-finsight eval-ledgerguard benchmark ci-gate clean
install:
	uv sync --frozen
	python scripts/bootstrap.py
	uv run python scripts/local_config.py
	cd frontend && npm ci
format:
	$(PY) -m ruff format backend scripts
lint:
	$(PY) -m ruff check backend scripts
typecheck:
	$(PY) -m mypy backend/agentbench
	cd frontend && npx tsc --noEmit
test:
	$(PY) scripts/test_postgres.py -q
	cd frontend && npm test
test-unit:
	$(PY) -m pytest -q -m 'not integration and not adversarial and not e2e'
test-integration:
	$(PY) scripts/test_postgres.py -q -m integration
test-e2e:
	cd frontend && npm run test:e2e
test-adversarial:
	$(PY) -m pytest -q -m adversarial
test-regression:
	$(PY) -m pytest -q -m regression
	$(PY) scripts/verify_ci.py
build:
	$(DC) build
up:
	python scripts/bootstrap.py
	$(DC) up --build -d
down:
	$(DC) down
migrate:
	$(PY) -m alembic upgrade head
seed:
	$(PY) -m agentbench seed
eval-offline:
	$(PY) -m agentbench eval run --agent 'Financial Research' --dataset financial-research --mode offline
eval-live:
	$(PY) -m agentbench register-live --version live-configured
	$(PY) -m agentbench eval run --agent 'Financial Research' --version live-configured --dataset ci-smoke --mode live
eval-finsight:
	$(PY) -m agentbench eval run --agent 'FinSight AI contract' --dataset finsight-contract --mode offline
eval-ledgerguard:
	$(PY) -m agentbench eval run --agent 'LedgerGuard AI contract' --dataset ledgerguard-contract --mode offline
benchmark:
	$(PY) scripts/benchmark.py
VERSION ?= v1
ci-gate:
	$(PY) scripts/ci_gate.py --version $(VERSION)
clean:
	$(PY) scripts/clean.py
