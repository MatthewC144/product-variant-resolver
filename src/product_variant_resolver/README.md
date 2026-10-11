# Package Map

This package contains both the active resolver and reproducible experiment/governance tooling. A
module being present here does not mean it runs in the default API.

## Active runtime path

| Module | Responsibility |
|---|---|
| `api.py` | FastAPI startup, `/resolve`, and `/health` |
| `service.py` | Dependency composition and response construction |
| `signals.py` | Noisy-title normalization and evidence extraction |
| `retrieval.py` | Sparse, hashing similarity, structured retrieval, and RRF |
| `rerank.py` | Reranker contracts and optional Pointwise adapters |
| `calibration.py` | Ranking features and calibrated probability |
| `policy.py` | `matched` / `ambiguous` / `no_match` decisions |
| `schemas.py`, `catalog.py`, `identity.py`, `config.py` | Core contracts and configuration |

Start with the human-readable [Code Tour](../../docs/CODE-TOUR.md).

## Optional integrations

- `postgres_*`: optional PostgreSQL/pgvector persistence and retrieval.
- `human_knowledge_*`: supporting review/explanation retrieval with no canonical identity authority.
- `observability.py`: optional tracing support.
- `neural_reranking.py`: local neural scorer loading; not enabled by default.

## Offline experiment and governance modules

Modules named `domain_ranker_*`, `image_search_*`, `pointwise_*`,
`serper_dual_source_*`, `representative_benchmark_*`, `canonical_authority_*`, and
`release_casting_review_*` reconstruct frozen experiments or owner-gated workflows. They are not a
second production application and should be read through [Results](../../docs/RESULTS.md) or the
[historical archive](../../docs/archive/README.md) before reading orchestration code.

## Default boundary

The default `Settings` keep the offline in-memory backend and do not activate a neural checkpoint.
Presence of PostgreSQL, ONNX, pairwise checkpoints, or experimental CLIs is evidence of implemented
and tested options—not a deployment claim.

