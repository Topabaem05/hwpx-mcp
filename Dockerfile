# syntax=docker/dockerfile:1

# ==============================================================================
# Stage 1: Builder - Install dependencies
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml pdm.lock* ./

RUN pdm config python.use_venv true && \
    pdm venv create --with-pip && \
    pdm install --prod --no-lock --no-editable

# ==============================================================================
# Stage 2: Runtime - Minimal production image
# ==============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

COPY --from=builder /app/.venv /app/.venv

COPY hwpx_mcp ./hwpx_mcp
COPY templates ./templates

RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
ENV MCP_STATELESS=false
ENV MCP_JSON_RESPONSE=false

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:${MCP_PORT}/health || exit 1

CMD ["python", "-m", "hwpx_mcp.server"]
