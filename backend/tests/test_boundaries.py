import pytest
from agentbench.agents.adapters import validate_external_url
from agentbench.evaluation.scoring import score
from agentbench.schemas import AgentConfig
from pydantic import ValidationError
from test_evaluators import simple


def test_embedded_provider_credentials_rejected():
    with pytest.raises(ValidationError, match="Credentials"):
        AgentConfig(name="Bad", version="1", model={"provider": "provider", "api_key": "never-store-this"})


def test_external_origins_require_administrator_authorization():
    with pytest.raises(ValueError, match="administrator-authorized"):
        validate_external_url("https://not-authorized.invalid/agent")
    with pytest.raises(ValueError, match="Invalid"):
        validate_external_url("http://user:password@localhost/agent")


def test_stdio_sandbox_does_not_inherit_provider_or_database_credentials(monkeypatch):
    from agentbench.mcp.client import sandbox_environment

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-sentinel")
    monkeypatch.setenv("AB_DATABASE_URL", "synthetic-sentinel")
    env = sandbox_environment()
    assert "OPENAI_API_KEY" not in env
    assert "AB_DATABASE_URL" not in env


def test_missing_trajectory_cannot_pass_on_final_answer_alone():
    case, execution = simple()
    execution.trace = []
    result = score(case, execution)
    assert not result.passed
    assert next(m for m in result.metrics if m.name == "trajectory_integrity").status == "ERROR"


@pytest.mark.adversarial
def test_synthetic_secret_disclosure_is_a_policy_failure():
    case, execution = simple()
    case.fixture["protected_values"] = ["SYNTHETIC-CANARY-ONLY"]
    execution.output["leaked"] = "SYNTHETIC-CANARY-ONLY"
    assert next(m for m in score(case, execution).metrics if m.name == "safety").status == "FAIL"
