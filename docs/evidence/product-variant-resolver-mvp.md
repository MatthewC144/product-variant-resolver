# Product Variant Resolver — Lite MVP Evidence

> QA verdict: **PASS WITH RISKS** for the dependency-light offline fixture path (2026-09-01).
> The default offline Docker/Python 3.12 runtime is verified on one local arm64 machine.
> PostgreSQL/pgvector, external neural models, TLS/proxy/remote networking, and concurrent load
> remain unverified.

## Evidence index

| Area | Evidence | Result |
|---|---|---|
| Requirements | [`specs/product-variant-resolver/review.md`](../../specs/product-variant-resolver/review.md) | R1–R14 and R16 passed within the Lite fixture scope; R15 passed with risk. |
| Focused re-verification | Final QA review | Catalog-derived series soft conflicts, the RRF default decision, and the in-process HTTP disclosure were re-verified after correction. No separate agent-verification artifact was checked in. |
| Test suite | QA review command transcript | 38/38 unittest-compatible unit, integration, API, UI, fixture, training, evaluation, and reporting tests passed on macOS arm64 / Python 3.14.6. |
| Compilation | QA review command transcript | `compileall` exited 0. An offline wheel build was not possible because the host lacked the required setuptools artifact. |
| Fixture integrity | [`data/manifest.json`](../../data/manifest.json) | `fixture-v1`: 120 products; 100 cases; train/dev/test = 58/21/21; frozen catalog and benchmark SHA-256 values. |
| Ranking/evaluation | [JSON](../../reports/fixture-v1/evaluation-fixture-v1-test.json) and [Markdown](../../reports/fixture-v1/evaluation-fixture-v1-test.md) | Report schema, raw derivations, disclosure, and generated SVG artifacts passed QA validation. |
| API/manual flow | QA review | `matched`, `ambiguous`, and `no_match`; default response omission; bounded debug output; structured 4xx; fail-closed 503 checks. |
| UI | QA review | Node DOM harness covered loading, match, abstention/empty, and error states; safe text rendering checks passed. No live browser run. |
| Docker/Python 3.12 | QA review | Rebuilt default image was healthy on Docker 29.5.3/aarch64 with Python 3.12.14, non-root UID 100, read-only root filesystem, loopback port, UI/three-state API flow, and missing-catalog fail-closed behavior. |
| Container reporting | QA review | `pvr-report` generated and validated one JSON, one Markdown, and four SVGs in the rebuilt read-only image; container API tests passed 8/8 and reporting tests 2/2. |
| Host→container latency | [`reports/runtime-validation/docker-python312-http-latency.json`](../../reports/runtime-validation/docker-python312-http-latency.json) | 50 sequential samples after 10 warm-ups reproduce nearest-rank p95 `4.721208 ms`; one arm64 machine, loopback, concurrency 1, offline-memory backend. |
| Compose/PostgreSQL | QA review | Default and PostgreSQL-profile static configuration passed, but PostgreSQL ingestion, retrieval, and migration-cycle E2E were not run. |

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

The fixture JSON report retains its raw in-process counts and samples. A separate QA regeneration
reported an in-process HTTP p95 of `2.45 ms`; those results are distinct from the checked-in
host→Docker artifact. Both in-process figures pass the 1500 ms fixture budget within their stated
scope, exclude Docker/TCP/proxy/database/concurrent-load costs, and are not production latency
evidence. The separately scoped container measurement follows.

## Docker/Python 3.12 runtime evidence

The separately checked-in runtime artifact records 50 host→Docker loopback requests after 10
warm-ups. Nearest-rank p95 is `4.721208 ms` at concurrency 1. The verified image used Docker
Desktop 29.5.3/aarch64 and Python 3.12.14, ran as UID 100 with a read-only root filesystem, and
became healthy on a loopback-only published port. QA observed UI assets, all three resolution
states, default response minimization, request IDs, and missing-catalog fail-closed behavior.

This boundary includes the host HTTP client, Docker Desktop port forwarding, Uvicorn/FastAPI, the
offline resolver, and JSON serialization/parsing. It excludes startup, TLS, proxying, remote
networking, concurrent load, and PostgreSQL. The raw artifact is
[`reports/runtime-validation/docker-python312-http-latency.json`](../../reports/runtime-validation/docker-python312-http-latency.json).

## Configuration captured by the report

- Dataset/catalog: `fixture-v1`; split by casting family; split seed `240901`.
- Catalog SHA-256: `0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`.
- Benchmark SHA-256: `e46c5b4a405a5b3e9fbac35c9613d8e5945e2d4494ad8df9f3d8be1e352fc323`.
- Candidate K: 25; sparse: token baseline; dense: `hashing-v1`; default ranker: RRF.
- Reranker: `heuristic-v1`, disabled by default and evaluated only as an ablation.
- Calibration: `fixture-v1-rrf-logistic-v2`; policy: `fixture-v1-rrf-trained-v2`.
- Report runtime: macOS arm64, Python 3.14.6.
- Verified container runtime: Docker Desktop 29.5.3/aarch64; Python 3.12.14; non-root UID 100;
  read-only root filesystem with writable `/tmp`; `127.0.0.1:8000` only.
- Runtime reporting dependency: `httpx2>=2,<3`, because the installed `pvr-report` command directly
  uses FastAPI TestClient.

## Known limitations and deferred evidence

- PostgreSQL/pgvector: schema and bound SQL exist; migration upgrade/downgrade, ingestion, FTS,
  exact pgvector search, and database E2E have not been run.
- External models: no pinned embedding model or cross-encoder has been integrated or evaluated;
  `hashing-v1` is not neural.
- Runtime boundary: one local arm64 Docker/Python 3.12 default offline run is verified. TLS,
  proxying, remote networks, concurrent load, and PostgreSQL are not.
- Rebuild reproducibility: dependencies remain bounded ranges without a committed lockfile or
  constraints file; the dev extra still lists legacy `httpx` and produces a host-side warning even
  though the container runtime uses `httpx2`.
- UI: no live-browser smoke test.
- Reviews: there was no formal architect, security, or performance-agent review. QA's secret scan
  is evidence of that check only and is not a security sign-off.
- Scope: do not describe these figures as production accuracy, broad Hot Wheels coverage, or
  production readiness.
