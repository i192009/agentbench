from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AB_", env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./agentbench.db"
    redis_url: str = "redis://localhost:6390/0"
    jwt_secret: str = Field(min_length=32, default="local-development-only-change-before-hosting-001")
    access_minutes: int = 15
    refresh_days: int = 7
    secure_cookies: bool = False
    frontend_origin: str = "http://localhost:5173"
    mcp_transport: str = "stdio"
    mcp_base_url: str = "http://localhost"
    mcp_token: str = "local-synthetic-sandbox"
    mlflow_tracking_uri: str = ""
    project_concurrency: int = Field(default=2, ge=1, le=8)
    case_concurrency: int = Field(default=4, ge=1, le=16)
    external_agent_origins: str = ""
    provider_model: str = ""
    provider_input_per_million: float | None = Field(default=None, ge=0)
    provider_output_per_million: float | None = Field(default=None, ge=0)
    live_enabled: bool = False
    judge_enabled: bool = False
    judge_model: str = ""
    judge_input_per_million: float | None = Field(default=None, ge=0)
    judge_output_per_million: float | None = Field(default=None, ge=0)
    demo_password: str = ""
    checkpoint_dir: str = ".runtime/checkpoints"
    run_timeout_seconds: int = 1800


@lru_cache
def settings() -> Settings:
    return Settings()
