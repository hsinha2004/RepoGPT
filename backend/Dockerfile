# ==============================================================================
# RepoGPT Backend Dockerfile (Multi-stage, unprivileged user, slim runtime)
# ==============================================================================

# Stage 1: Build virtual environment with uv
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python --no-cache -r pyproject.toml

# Stage 2: Minimal runtime image
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with UID 10001
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -s /bin/bash -m app

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY --chown=app:app app /app/app

# Shared data and models directories
RUN mkdir -p /data /models && chown -R app:app /data /models /app

USER app:app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health/live').getcode() == 200 else 1)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
