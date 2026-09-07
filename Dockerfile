FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODELS_DIR=/app/models/fastembed

# Install python dependencies
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ app/
COPY scripts/ scripts/
COPY monitoring/ monitoring/

# Create directories for models and processed/raw data (populated at runtime,
# or mounted as volumes by docker-compose)
RUN mkdir -p models/fastembed data/processed data/raw data/kanjivg data/monitoring

# Pre-download the embedding/sparse/reranker ONNX models into the image so the
# first request doesn't pay the download cost.
RUN python -c "from app.embedder import warm_models; warm_models()"

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import httpx,sys; sys.exit(0 if httpx.get('http://localhost:8501/healthz', timeout=3).status_code==200 else 1)"

CMD ["python", "scripts/startup.py"]
