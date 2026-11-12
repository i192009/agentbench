import json
from pathlib import Path

import pytest
from agentbench.agents.adapters import execute
from agentbench.evaluation.scoring import score
from agentbench.schemas import AgentConfig, DatasetFile
from agentbench.tracing import redact


@pytest.mark.parametrize("adapter", ["finsight", "ledgerguard"])
async def test_native_repository_contract_fixture_and_faulty_variant(adapter, sandbox):
    root = Path("examples/repository-contracts")
    config = AgentConfig.model_validate_json((root / f"{adapter}-agent.json").read_text())
    dataset = DatasetFile.model_validate_json((root / f"{adapter}-dataset.json").read_text())
    case = dataset.cases[0]
    result = await execute(config, case, sandbox, "offline", "integration-test")
    assert score(case, result).passed
    assert result.provenance["original_application_executed"] is False
    assert result.provenance["inspected_commit"]
    config.variant = "wrong_calculation" if adapter == "finsight" else "approval_bypass"
    broken = await execute(config, case, sandbox, "offline", "integration-test")
    assert not score(case, broken).passed


def test_secret_redaction():
    payload = {
        "password": "private",
        "nested": {"api_key": "private", "message": "Bearer token123"},
        "driver_token": "private",
    }
    assert "private" not in json.dumps(redact(payload))
    assert "token123" not in json.dumps(redact(payload))
