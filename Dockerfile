# syntax=docker/dockerfile:1

FROM python:3.13-slim-trixie

LABEL org.opencontainers.image.title="Reikun" \
      org.opencontainers.image.description="Reikun (例訓) — Semantic Japanese Dictionary" \
      org.opencontainers.image.source="https://github.com/AnkS4/Reikun" \
      org.opencontainers.image.authors="Aniket Satbhai" \
      org.opencontainers.image.licenses="Apache-2.0"

# INGEST_VIA_DOCKER=1 → self-provisioning image (rsync + ingest group; pipeline runs at boot)
ARG INGEST_VIA_DOCKER=0
ENV INGEST_VIA_DOCKER=$INGEST_VIA_DOCKER \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODELS_DIR=/app/models/fastembed \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/home/app/.cache/uv

RUN useradd --create-home --uid 1000 app \
    && mkdir /app && chown app:app /app \
    && if [ "$INGEST_VIA_DOCKER" = "1" ]; then \
         apt-get update \
         && apt-get install -y --no-install-recommends rsync \
         && rm -rf /var/lib/apt/lists/*; \
       fi
USER app
WORKDIR /app

# deps layer — cached until uv.lock changes
COPY --chown=app:app pyproject.toml uv.lock ./
RUN /usr/local/bin/python -m pip install --no-cache-dir --target=/tmp/uvpkg uv==0.12.17 \
    && if [ "$INGEST_VIA_DOCKER" = "1" ]; then \
      /tmp/uvpkg/bin/uv sync --frozen --no-default-groups --group ingest --no-install-project; \
    else \
      /tmp/uvpkg/bin/uv sync --frozen --no-default-groups --no-install-project; \
    fi \
    && rm -rf /tmp/uvpkg /home/app/.cache/uv
ENV PATH="/app/.venv/bin:$PATH"

# model warm layer — ~90 MB of downloads; depends only on the three modules
# embedder imports, so code edits don't invalidate it
COPY --chown=app:app app/__init__.py app/config.py app/embedder.py app/
RUN python -c "from app.embedder import warm_models; warm_models()"

# project layer — editable install provides the `reikun` script
COPY --chown=app:app app/ app/
COPY --chown=app:app scripts/ scripts/
RUN /usr/local/bin/python -m pip install --no-cache-dir --target=/tmp/uvpkg uv==0.12.17 \
    && if [ "$INGEST_VIA_DOCKER" = "1" ]; then \
      /tmp/uvpkg/bin/uv sync --frozen --no-default-groups --group ingest; \
    else \
      /tmp/uvpkg/bin/uv sync --frozen --no-default-groups; \
    fi \
    && rm -rf /tmp/uvpkg /home/app/.cache/uv

COPY --chown=app:app \
    data/processed/kanji_table.json \
    data/processed/headword_index.marisa \
    data/processed/strokes.json \
    data/processed/

RUN python -m compileall -q app scripts

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=10m --retries=3 \
    CMD python -c "import httpx,sys,os; r=httpx.get(f\"http://localhost:{os.getenv('PORT','8000')}/health\", timeout=3); sys.exit(0 if r.status_code==200 else 1)"

CMD ["reikun"]
