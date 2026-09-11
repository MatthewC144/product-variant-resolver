# syntax=docker/dockerfile:1
FROM python:3.12.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PVR_CATALOG_PATH=/app/data/catalog.json \
    PVR_HUMAN_CATALOG_PATH=/app/data/human_backed_catalog.json \
    PVR_REVIEW_FAMILY_KNOWLEDGE_PATH=/app/data/review_family_knowledge.json \
    PVR_REVIEW_FAMILY_KNOWLEDGE_MANIFEST_PATH=/app/data/review_family_knowledge_manifest.json \
    PVR_BENCHMARK_PATH=/app/data/benchmark.json \
    PVR_BACKEND=offline \
    PVR_DENSE_PROVIDER=hashing-v1 \
    PVR_RERANKER_PROVIDER=heuristic-v1 \
    PVR_RERANKER_ENABLED=false \
    PVR_POLICY_VERSION=fixture-v1-rrf-trained-v2

WORKDIR /app

RUN addgroup --system pvr && adduser --system --ingroup pvr --home /nonexistent pvr

COPY pyproject.toml README.md ./
COPY constraints/ ./constraints/
COPY src/ ./src/
RUN python -m pip install --no-cache-dir -c constraints/python312.txt '.[postgres]'

COPY data/ ./data/
COPY config/ ./config/
COPY ui/ ./ui/
COPY migrations/ ./migrations/
COPY alembic.ini ./alembic.ini
COPY scripts/verify_postgres_migration.py ./scripts/verify_postgres_migration.py
COPY scripts/verify_postgres_ingestion.py ./scripts/verify_postgres_ingestion.py
COPY scripts/verify_postgres_sparse_retrieval.py ./scripts/verify_postgres_sparse_retrieval.py
COPY scripts/verify_postgres_dense_retrieval.py ./scripts/verify_postgres_dense_retrieval.py

USER pvr
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["uvicorn", "product_variant_resolver.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
