# Product Variant Resolver — Lite MVP Evidence

> QA verdict: **PASS WITH RISKS** for the dependency-light offline fixture path (2026-09-01).
> PostgreSQL/pgvector, external neural models, Docker runtime, and Python 3.12 runtime remain
> unverified.

## Evidence index

| Area | Evidence | Result |
|---|---|---|
| Requirements | [`specs/product-variant-resolver/review.md`](../../specs/product-variant-resolver/review.md) | R1–R14 passed within fixture scope; R15 passed with risk; R16 passed for available suites. |
| Focused re-verification | Final QA review | Catalog-derived series soft conflicts, the RRF default decision, and the in-process HTTP disclosure were re-verified after correction. No separate agent-verification artifact was checked in. |
| Test suite | QA review command transcript | 38/38 unittest-compatible unit, integration, API, UI, fixture, training, evaluation, and reporting tests passed on macOS arm64 / Python 3.14.6. |
| Compilation | QA review command transcript | `compileall` exited 0. An offline wheel build was not possible because the host lacked the required setuptools artifact. |
| Fixture integrity | [`data/manifest.json`](../../data/manifest.json) | `fixture-v1`: 120 products; 100 cases; train/dev/test = 58/21/21; frozen catalog and benchmark SHA-256 values. |
| Ranking/evaluation | [JSON](../../reports/fixture-v1/evaluation-fixture-v1-test.json) and [Markdown](../../reports/fixture-v1/evaluation-fixture-v1-test.md) | Report schema, raw derivations, disclosure, and generated SVG artifacts passed QA validation. |
| API/manual flow | QA review | `matched`, `ambiguous`, and `no_match`; default response omission; bounded debug output; structured 4xx; fail-closed 503 checks. |
| UI | QA review | Node DOM harness covered loading, match, abstention/empty, and error states; safe text rendering checks passed. No live browser run. |
| Compose | QA review | Default and PostgreSQL-profile static `docker compose config` passed. No image/container/database run. |

## Frozen fixture-v1 test result

The checked-in report evaluates exactly **21 synthetic fixture test cases**, including 12 matched
cases. This dataset is curated/generated for an MVP and is not a marketplace sample.

| Metric | Result | Gate / note |
|---|---:|---|
| Recall@25 | `1.0` | R9 gate `>=0.95` |
| Top-1 accuracy | `1.0` | R10 gate `>=0.80` |
| Hard-negative accuracy | `1.0` (4/4) | R10 gate `>=0.75` |
| Precision | `1.0` | R12 gate `>=0.90` |
| False-match rate | `0.0` | R12 gate `<=0.10` |
| Coverage | `0.8333` | R12 gate `>=0.50` |
| Reranker Top-1 gain over RRF | `0.0` | R11 alternative: RRF remains default; heuristic is opt-in |
| Warmed in-process ASGI p95 | `7.9523 ms` | 21 samples, K=25; limited R13 fixture smoke only |

The JSON report retains raw counts and latency samples. A separate QA regeneration reported
an in-process HTTP p95 of `2.45 ms`; both results passed the 1500 ms fixture budget, and neither
measured Docker/container, TCP, reverse proxy, database, or concurrent load.

## Configuration captured by the report

- Dataset/catalog: `fixture-v1`; split by casting family; split seed `240901`.
- Catalog SHA-256: `0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`.
- Benchmark SHA-256: `e46c5b4a405a5b3e9fbac35c9613d8e5945e2d4494ad8df9f3d8be1e352fc323`.
- Candidate K: 25; sparse: token baseline; dense: `hashing-v1`; default ranker: RRF.
- Reranker: `heuristic-v1`, disabled by default and evaluated only as an ablation.
- Calibration: `fixture-v1-rrf-logistic-v2`; policy: `fixture-v1-rrf-trained-v2`.
- Report runtime: macOS arm64, Python 3.14.6.

## Known limitations and deferred evidence

- PostgreSQL/pgvector: schema and bound SQL exist; migration upgrade/downgrade, ingestion, FTS,
  exact pgvector search, and database E2E have not been run.
- External models: no pinned embedding model or cross-encoder has been integrated or evaluated;
  `hashing-v1` is not neural.
- Runtime: Docker build/start/health, read-only filesystem behavior, Python 3.12, and real network
  latency have not been verified.
- UI: no live-browser smoke test.
- Reviews: there was no formal architect, security, or performance-agent review. QA's secret scan
  is evidence of that check only and is not a security sign-off.
- Scope: do not describe these figures as production accuracy, broad Hot Wheels coverage, or
  production readiness.
