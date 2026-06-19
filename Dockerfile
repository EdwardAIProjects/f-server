FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY f_server ./f_server
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

FROM python:3.12-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git openjdk-17-jdk-headless apksigner \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 fserver
COPY --from=builder /app /app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && chown -R fserver:fserver /app
USER fserver
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "f_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
