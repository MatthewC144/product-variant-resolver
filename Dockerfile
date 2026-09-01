# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PVR_CATALOG_PATH=/app/data/catalog.json \
    PVR_BENCHMARK_PATH=/app/data/benchmark.json \
    PVR_BACKEND=offline \
    PVR_DENSE_PROVIDER=hashing-v1 \
    PVR_RERANKER_PROVIDER=heuristic-v1 \
    PVR_RERANKER_ENABLED=false \
    PVR_POLICY_VERSION=fixture-v1-rrf-trained-v2

WORKDIR /app

RUN addgroup --system pvr && adduser --system --ingroup pvr --home /nonexistent pvr

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir '.[postgres]'

COPY data/ ./data/
COPY config/ ./config/
COPY ui/ ./ui/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini

USER pvr
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["uvicorn", "product_variant_resolver.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
