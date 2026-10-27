FROM python:3.13-slim

# Same uv version as local development (uv.lock was produced by it).
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

WORKDIR /app
# Dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# Railway sets PORT and terminates TLS at its proxy; --proxy-headers makes request.client.host the
# real client IP, which the per-IP generation limit depends on.
CMD ["sh", "-c", "exec uv run --no-sync uvicorn oauth_guides_api.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
