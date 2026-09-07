# T09 PostgreSQL Sparse Retrieval Evidence

> Date: 2026-09-07
> Mode: Lite / isolated local Docker verification
> Catalog: `fixture-v1`

The final verification used Compose project `pvr-t09`, host PostgreSQL port `55434`, the rebuilt
Python 3.12 project image, and PostgreSQL `16.14` with pgvector. Migration `0001` and the T07
ingestion command installed 120 product and 120 search-document rows before retrieval checks.

The production `SQLAlchemyPostgresRetrieverAdapter` and `PostgresSparseRetriever` then proved:

- a catalog identifier alone returned its canonical product at Top-1;
- all 12 matched frozen test cases contained the expected UUID within Top-25, for Recall@25 `1.0`;
- forcing sequential scans off produced a plan containing GIN index
  `ix_product_search_document`;
- injection-shaped input remained a bound `:query` value and the product table remained present;
- catalog version, checksum, product count, and search-document count matched at startup;
- changing the stored checksum made a new API instance return health 503; restoring it recovered
  readiness;
- a real Uvicorn/FastAPI container on loopback returned ready and resolved
  `2022 Chevy Nomad Red #101` to
  `hot-wheels-chevy-nomad-2022-mainline-red-101` with sparse version
  `postgres-fts-simple-v1`.

The structured verification result reported 12 matched cases, Recall@25 `1.0`, identifier Top-1,
GIN-plan verification, safe bound-input handling, API readiness, and checksum fail-closed behavior.
The isolated API, database, network, and named volume were removed afterward.

This evidence covers PostgreSQL sparse candidate generation on 120 synthetic/curated fixture
products. It does not establish performance or quality at 3,000 rows, production traffic, BM25,
neural embeddings, or pgvector retrieval. Dense canonical retrieval remains the deterministic
in-memory `hashing-v1` baseline, and final identity still passes through RRF, calibration, and the
three-state decision policy.
