FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/agentbench/__init__.py ./backend/agentbench/__init__.py
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen
COPY backend ./backend
ENV PATH="/opt/venv/bin:$PATH"
COPY alembic.ini ./
COPY datasets ./datasets
COPY scripts ./scripts
COPY examples ./examples
COPY evaluation ./evaluation
RUN mkdir -p examples .runtime && useradd -m -u 10001 agentbench && chown -R agentbench:agentbench /app
USER agentbench
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "agentbench.main:app", "--host", "0.0.0.0", "--port", "8000"]
