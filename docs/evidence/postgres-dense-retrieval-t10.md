# T10 PostgreSQL Exact Dense Retrieval Evidence

> Date: 2026-09-07
> Mode: Lite / isolated local Docker verification
> Catalog: `fixture-v1`

The final verification used Compose project `pvr-t10`, host PostgreSQL port `55435`, the rebuilt
Python 3.12 image, and PostgreSQL `16.14` with pgvector. Migration `0001` and catalog ingestion ran
before the new materialization command generated 120 deterministic 192-dimensional vectors.

The production materializer, startup verifier, and exact dense retriever proved:

- all 120 catalog identities received versioned embedding rows;
- the artifact version was `hashing-v1-d192-catalog-searchable-text-v1`;
- repeating materialization produced the same rows and index checksum;
- a catalog alias recovered its expected product within Top-25;
- all 12 matched frozen-test targets appeared within Top-25, giving Recall@25 `1.0`;
- deleting one embedding row made a new API instance fail readiness with 503;
- restoring the complete artifact recovered readiness;
- the query used pgvector cosine distance operator `<=>` with bound vector, version, and limit;
- PostgreSQL-backed API examples preserved `matched`, `ambiguous`, and `no_match` decisions;
- a real Uvicorn request resolved `2022 Chevy Nomad Red #101` to the expected canonical ID, with
  both sparse and dense candidates coming from PostgreSQL.

The real health response identified dense version
`postgres-exact-hashing-v1-d192-catalog-searchable-text-v1` and database PostgreSQL 16.14. The
resolved target ranked first in sparse, dense, structured, and fused candidate sources. The host
suite passed 77/77 after the feature, fail-closed, and schema-dimension tests were added.

This evidence validates the vector storage and exact-query pipeline, not neural semantic quality.
`hashing-v1` is deterministic and offline but remains a lexical hashing baseline. The run covers
120 synthetic/curated products and sequential smoke traffic; it does not measure 3,000-row latency,
concurrency, external models, or whether an approximate vector index would become useful. All T10
containers, network, and database volume were removed after verification.
