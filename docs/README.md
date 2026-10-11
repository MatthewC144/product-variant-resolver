# Technical Documentation

This index is the second layer of the repository reading path. Start with the root
[README](../README.md), use the pages below for the technical story, and enter `evidence/`, `specs/`,
or `reports/` only when exact lineage is needed.

## Start here

1. [System overview](architecture/system-overview.md) — pipeline, authority boundary, and component rationale.
2. [Results](RESULTS.md) — current headline, historical context, negative results, and conclusions.
3. [Code tour](CODE-TOUR.md) — the seven files that explain the active system fastest.
4. [Limitations](LIMITATIONS.md) — canonical human-readable scope and claim boundaries.
5. [Portfolio guide](PORTFOLIO-GUIDE.md) — resume wording and interview walkthrough.

## Architecture

| Topic | Document |
|---|---|
| End-to-end resolver | [System overview](architecture/system-overview.md) |
| MVP contracts and original architecture | [MVP evidence](evidence/product-variant-resolver-mvp.md) |
| Human Knowledge storage profile | [Storage profile guide](HUMAN-STORAGE-PROFILE-GUIDE.md) |

## AI / ML experiments

| Topic | Document |
|---|---|
| Consolidated result hierarchy | [Results](RESULTS.md) |
| Pointwise and Listwise comparison | [Neural comparison evidence](evidence/neural-reranker-comparison-v1.md) |
| Domain-adapted pairwise ranker | [Domain-ranker v2 selection](evidence/domain-ranker-v2-selection.md) |
| Dual-source final ranking | [Dual-source AI eval](evidence/ai-evals/serper-dual-source-raw-pointwise-final-test-v1.md) |

## Evaluation

| Topic | Document |
|---|---|
| Dual-source benchmark QA | [Evaluation review](../specs/serper-dual-source-evaluation-v1/review.md) |
| Calibration QA | [Calibration review](../specs/serper-dual-source-policy-calibration-v1/review.md) |
| Claim boundaries | [Limitations](LIMITATIONS.md) |
| Portfolio release verification | [Release evidence](evidence/portfolio-release-closure-v1.md) |

## Engineering

| Topic | Document |
|---|---|
| Active implementation path | [Code tour](CODE-TOUR.md) |
| PostgreSQL ingestion | [Ingestion evidence](evidence/postgres-ingestion-t07.md) |
| pgvector retrieval | [Dense retrieval evidence](evidence/postgres-dense-retrieval-t10.md) |
| Artifact retention | [Artifact policy](ARTIFACT-POLICY.md) |

## Historical evidence

The repository intentionally retains rejected models, blocked gates, frozen manifests, and earlier
benchmarks. They are evidence of experimental discipline, not the recommended first reading path.
Use the [historical archive entry](archive/README.md) to choose the relevant lineage.

