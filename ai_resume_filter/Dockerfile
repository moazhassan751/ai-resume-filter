FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build-time tools are isolated in this stage so the runtime image stays small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a wheelhouse for reproducible, cache-friendly builds.
COPY ai_resume_filter/requirements.txt /build/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip wheel --wheel-dir /wheels -r /build/requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2 \
    GUNICORN_TIMEOUT=120

WORKDIR /app

# Run as an unprivileged user to reduce container risk.
RUN groupadd --system app && useradd --system --gid app --uid 10001 app

COPY --from=builder /wheels /wheels
COPY ai_resume_filter/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r /tmp/requirements.txt \
    && rm -rf /wheels /root/.cache

COPY ai_resume_filter /app/ai_resume_filter

# Create the writable runtime directories used by uploads, exports, caches, and vector storage.
RUN mkdir -p /app/data/uploads /app/data/exports /app/data/cache /app/data/data /app/data/vector_db/chroma /app/data/models \
    && chown -R app:app /app

USER app

WORKDIR /app/ai_resume_filter

EXPOSE 8000

# Gunicorn with Uvicorn workers is the production entrypoint; worker count is configurable at runtime.
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"]
