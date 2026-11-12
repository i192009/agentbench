"""Run tests in an isolated, disposable PostgreSQL database, never the demo database."""

import os
import re
import subprocess
import sys
from uuid import uuid4

import psycopg
from agentbench.config import settings
from psycopg import sql

name = "agentbench_test_" + uuid4().hex
assert re.fullmatch(r"agentbench_test_[a-f0-9]{32}", name)
url = settings().database_url.replace("postgresql+asyncpg", "postgresql")
test_url = url.rsplit("/", 1)[0] + "/" + name
with psycopg.connect(url, autocommit=True) as connection:
    connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        env = {
            **os.environ,
            "AB_TEST_DATABASE_URL": test_url.replace("postgresql://", "postgresql+asyncpg://"),
            "AB_TEST_REDIS_URL": settings().redis_url.rsplit("/", 1)[0] + "/2",
        }
        result = subprocess.run([sys.executable, "-m", "pytest", *sys.argv[1:]], env=env)
    finally:
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
raise SystemExit(result.returncode)
