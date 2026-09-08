# Product Variant Resolver — Lite MVP Evidence

> QA verdict: **PASS WITH RISKS** for the dependency-light offline fixture path (2026-09-01).
> The default offline Docker/Python 3.12 runtime is verified on one local arm64 machine.
> PostgreSQL migration, ingestion, sparse FTS, and exact pgvector API retrieval are locally
> verified; external neural models, TLS/proxy/remote networking, concurrent load, and 3,000-row
> database performance remain unverified.
> The 100-row Hot Wheels Wiki pilot is attributed, frozen, and validated as review-only staging;
> its deterministic cross-catalog review also remains outside the canonical catalog and AI
> evaluation set. Four attributable casting-family links are now accepted; all related variants
> remain held and supply no canonical or evaluation labels.

## Evidence index

| Area | Evidence | Result |
|---|---|---|
| Requirements | [`specs/product-variant-resolver/review.md`](../../specs/product-variant-resolver/review.md) | R1–R14 and R16–R20 passed within their Lite scopes; R15 and R21–R25 passed with documented risks. |
| Focused re-verification | Final QA review | Catalog-derived series soft conflicts, the RRF default decision, and the in-process HTTP disclosure were re-verified after correction. No separate agent-verification artifact was checked in. |
| Test suite | QA review command transcript | Original 38/38 suite passed; the current host suite passes 99/99. The earlier constrained runtime image passed 39/39 non-Node tests; its UI controller test remains host-only because Node is not installed in the runtime image. |
| Compilation | QA review command transcript | `compileall` exited 0. An offline wheel build was not possible because the host lacked the required setuptools artifact. |
| Fixture integrity | [`data/manifest.json`](../../data/manifest.json) | `fixture-v1`: 120 products; 100 cases; train/dev/test = 58/21/21; frozen catalog and benchmark SHA-256 values. |
| Ranking/evaluation | [JSON](../../reports/fixture-v1/evaluation-fixture-v1-test.json) and [Markdown](../../reports/fixture-v1/evaluation-fixture-v1-test.md) | Report schema, raw derivations, disclosure, and generated SVG artifacts passed QA validation. |
| API/manual flow | QA review | `matched`, `ambiguous`, and `no_match`; default response omission; bounded debug output; structured 4xx; fail-closed 503 checks. |
| UI | QA review | Node DOM harness covered loading, match, abstention/empty, and error states; safe text rendering checks passed. No live browser run. |
| Docker/Python 3.12 | QA review | No-cache constrained image `sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75` was healthy on Docker Desktop 29.5.3/aarch64 with Python 3.12.14, user `pvr` (UID 100/GID 101), and a read-only root filesystem. Live health and all three API outcomes matched expectations; abstentions returned no identity. |
| Container reporting | QA review | `pvr-report` generated one JSON, one Markdown, and four SVGs in the constrained read-only image; all 39 mounted tests not requiring Node passed. |
| Host→container latency | [`reports/runtime-validation/docker-python312-http-latency.json`](../../reports/runtime-validation/docker-python312-http-latency.json) | 50 sequential samples after 10 warm-ups reproduce nearest-rank p95 `4.721208 ms`; one arm64 machine, loopback, concurrency 1, offline-memory backend. |
| Compose/PostgreSQL | [T07](postgres-ingestion-t07.md), [T09](postgres-sparse-retrieval-t09.md), [T10](postgres-dense-retrieval-t10.md), and QA review | Migration, transactional ingestion, FTS, exact pgvector, artifact-readiness validation, and real HTTP resolution passed in isolated Compose runs. |
| External catalog pilot | [T30 evidence](fandom-catalog-pilot-t30.md), [attribution](../../data/external/hot-wheels-wiki/README.md), and [manifest](../../data/external/hot-wheels-wiki/pilot-2025/manifest.json) | 100 revision-frozen, text-only rows passed staging validation; 45 variant notes, 100 null colors, and zero canonical promotions. |
| External catalog review | [T31 evidence](fandom-catalog-review-t31.md) and [review manifest](../../data/external/hot-wheels-wiki/pilot-2025/review-manifest.json) | 100 rows / 53 families reviewed deterministically: 4 exact human-family candidates, 49 possible-new-family groups, and zero promotions. |
| Human adjudication queue | [T32 evidence](fandom-adjudication-queue-t32.md) and [worksheet](../../data/external/hot-wheels-wiki/pilot-2025/adjudication-queue.md) | All 100 rows occur once across 53 pending family decisions; actor/time/reason/evidence are required and promotion eligibility is zero. |
| Priority-1 evidence | [T33 evidence](fandom-priority-one-evidence-t33.md) and [review packet](../../data/external/hot-wheels-wiki/pilot-2025/priority-1-evidence.md) | Four side-by-side packets cover nine Wiki rows; family merges are proposed, variants remain held, confirmations remain empty, and promotions remain zero. |
| Priority-1 decisions | [T34 evidence](fandom-priority-one-decisions-t34.md) and [result](../../data/external/hot-wheels-wiki/pilot-2025/adjudication-result.md) | Four exact-target casting-family links are accepted; 49 decisions and all release variants remain held/pending, promotion eligibility is zero, and invalid targets fail closed. |

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

The later dependency closure rebuilt the API image without cache as
`sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75` and verified the exact
selected stack: FastAPI 0.141.1, Starlette 1.6.0, `httpx2`/`httpcore2` 2.12.0, AnyIO 4.14.0,
Pydantic 2.13.5, and Uvicorn 0.52.4. `python -W error` imported TestClient without warnings;
legacy `httpx` was absent. The read-only/tmpfs-mounted run passed all 39 backend/API/evaluation/
reporting/integration/unit/fixture tests that do not require Node. The complete 41-test selection
is evidenced by the fresh constrained host environment, not the container: its UI controller test
requires Node, which is intentionally absent from the runtime image.

This boundary includes the host HTTP client, Docker Desktop port forwarding, Uvicorn/FastAPI, the
offline resolver, and JSON serialization/parsing. It excludes startup, TLS, proxying, remote
networking, concurrent load, and PostgreSQL. The raw artifact is
[`reports/runtime-validation/docker-python312-http-latency.json`](../../reports/runtime-validation/docker-python312-http-latency.json).

## Configuration captured by the report

- Dataset/catalog: `fixture-v1`; split by casting family; split seed `240901`.
- Catalog SHA-256: `0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`.
- Benchmark SHA-256: `e46c5b4a405a5b3e9fbac35c9613d8e5945e2d4494ad8df9f3d8be1e352fc323`.
- Candidate K: 25; offline sparse: token baseline; dense model: deterministic `hashing-v1`;
  PostgreSQL dense execution: exact cosine pgvector; default ranker: RRF.
- Reranker: `heuristic-v1`, disabled by default and evaluated only as an ablation.
- Calibration: `fixture-v1-rrf-logistic-v2`; policy: `fixture-v1-rrf-trained-v2`.
- Report runtime: macOS arm64, Python 3.14.6.
- Verified container runtime: Docker Desktop 29.5.3/aarch64; Python 3.12.14; non-root UID 100;
  read-only root filesystem with writable `/tmp`; `127.0.0.1:8000` only.
- Runtime reporting dependency: `httpx2>=2,<3`, because the installed `pvr-report` command directly
  uses FastAPI TestClient.

## Known limitations and deferred evidence

- External catalog: the 100 Hot Wheels Wiki rows are a review queue only. They have no verified
  color or canonical UUID, do not enter API retrieval, and do not support an accuracy or 3,000-row
  coverage claim. T31 provides exact family-level pre-review only; human adjudication, canonical
  promotion rules, and formal legal/security review remain deferred. T32 prepares an attributable
  queue, T33 prepares evidence, and T34 records four family-only owner decisions. These still do
  not create canonical or release-variant labels.
- PostgreSQL/pgvector: migration lifecycle, canonical fixture ingestion, FTS candidate retrieval,
  GIN-plan compatibility, 120 deterministic vector rows, exact cosine retrieval, and real API HTTP
  resolution are verified in isolated Docker runs. Neural embeddings, 3,000-row evaluation,
  concurrency, and database latency have not been run.
- External models: no pinned embedding model or cross-encoder has been integrated or evaluated;
  `hashing-v1` is not neural.
- Runtime boundary: one local arm64 Docker/Python 3.12 default offline run and a separate local
  PostgreSQL sparse HTTP smoke run are verified. TLS, proxying, remote networks, concurrent load,
  and PostgreSQL latency are not.
- Rebuild reproducibility: `constraints/python312.txt` fixes the compatibility-sensitive web stack
  and is verified by a no-cache container build, but it is selective rather than a complete
  transitive lock. PostgreSQL extras and unlisted transitive/build dependencies remain range-
  resolved.
- UI test boundary: the runtime image intentionally omits Node, so its mounted container evidence is
  39/39 non-Node tests; the Node UI controller test is covered by the fresh 41/41 host run.
- Static-analysis debt: targeted dependency-scope Ruff/mypy checks passed, but existing whole-
  repository Ruff/mypy findings remain unresolved; full Ruff currently reports 36 findings.
- UI: no live-browser smoke test.
- Reviews: there was no formal architect, security, or performance-agent review. QA's secret scan
  is evidence of that check only and is not a security sign-off.
- Scope: do not describe these figures as production accuracy, broad Hot Wheels coverage, or
  production readiness.
