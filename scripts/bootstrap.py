"""Create ignored local-only secrets. Never overwrite existing configuration."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print(".env already exists; preserved")
else:
    password = secrets.token_urlsafe(24)
    body = (root / ".env.example").read_text()
    for old, new in [
        ("local-change-me", password),
        ("replace-with-a-random-secret-of-at-least-32-characters", secrets.token_urlsafe(48)),
        ("replace-with-a-local-sandbox-token", secrets.token_urlsafe(32)),
        ("change-this-local-demo-password", "demo-agentbench-local-2026!"),
    ]:
        body = body.replace(old, new)
    target.write_text(body, encoding="utf-8")
    print("Created ignored .env. Local demo: demo@agentbench.local / demo-agentbench-local-2026!")
