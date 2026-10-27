FROM python:3.13-slim

# Same uv version as local development (uv.lock was produced by it).
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

WORKDIR /app
# Dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# Render sets PORT and terminates TLS at its edge. Forwarded headers are not trusted wholesale: the
# per-IP limit reads True-Client-IP in app.py, because the leftmost X-Forwarded-For is client-controlled.
CMD ["sh", "-c", "exec uv run --no-sync uvicorn oauth_guides_api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
