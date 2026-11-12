"""Derive ignored host settings from the local Compose configuration."""

from pathlib import Path

from agentbench.config import settings

path = Path(".env.local")
if path.exists():
    print(".env.local already exists; preserved")
else:
    cfg = settings()
    values = {
        "AB_DATABASE_URL": cfg.database_url.replace("@postgres:5432/", "@127.0.0.1:5440/"),
        "AB_REDIS_URL": cfg.redis_url.replace("redis:6379", "127.0.0.1:6390"),
        "AB_JWT_SECRET": cfg.jwt_secret,
        "AB_MCP_TOKEN": cfg.mcp_token,
        "AB_DEMO_PASSWORD": cfg.demo_password,
        "AB_MCP_TRANSPORT": "stdio",
        "AB_MLFLOW_TRACKING_URI": "",
        "AB_FRONTEND_ORIGIN": "http://localhost:5173",
    }
    path.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
    print("Created ignored .env.local for host API, CLI and worker development")
