# Product Variant Resolver — MVP Decisions

> Status: accepted for the Lite/MVP fixture path on 2026-09-01. Architect, security, and
> performance reviews were not run and remain deferred.

## D1 — Ship an offline fixture baseline first

- **Choice:** Make the version-controlled catalog and dependency-light in-memory pipeline the
  executable default.
- **Reason:** It provides a deterministic demonstration and a reproducible evaluation loop without
  network, database, paid API, or GPU dependencies.
- **Alternatives:** Real marketplace catalog ingestion; PostgreSQL/pgvector as the only runtime;
  hosted retrieval/model APIs.
- **Impact:** The checked-in metrics describe only 21 synthetic fixture test cases. They do not
  establish production accuracy, marketplace coverage, or production readiness.
- **Deferred review:** Real-data provenance/coverage and production catalog design.

## D2 — Keep product knowledge in catalog data

- **Choice:** Application code parses generic syntax; color, series, aliases, identifiers, and
  variants come from catalog data.
- **Reason:** A catalog-only change can add knowledge without another product-specific branch.
- **Alternatives:** Hard-coded series/color dictionaries or variant rules in the resolver.
- **Impact:** Structured matches and conflicts remain explainable. Conflicts are ranking features,
  not destructive filters.
- **Deferred review:** Governance and validation for externally sourced catalog changes.

## D3 — Use RRF as the default ranker

- **Choice:** Default to reciprocal-rank fusion. Keep `heuristic-v1` available only through
  `PVR_RERANKER_ENABLED=true` and for offline ablation.
- **Reason:** On the same 12 matched frozen-test cases, RRF and `heuristic-v1` each produced Top-1
  `1.0`; the absolute reranker gain was `0.0`.
- **Alternatives:** Always run the heuristic; add raw sparse/dense scores; use a pinned local
  cross-encoder.
- **Impact:** The default path avoids an unproven stage while retaining its interface and debug
  fields. This decision says nothing about external cross-encoders because none was evaluated.
- **Deferred review:** Revisit with real hard negatives and a pinned neural model.

## D4 — Calibrate and abstain

- **Choice:** Fit calibration on grouped train data, select thresholds on grouped dev data, and
  freeze the policy before evaluating test labels.
- **Reason:** A resolver must be able to return `ambiguous` or `no_match`, not force a nearby
  identity.
- **Alternatives:** Always choose Top-1; use a fixed uncalibrated score cutoff.
- **Impact:** The API has three lowercase decision states. Current test evidence shows precision
  `1.0`, false-match rate `0.0`, and coverage `0.8333`, but only on the synthetic fixture test.
- **Deferred review:** Larger calibration sets, uncertainty intervals, and a full
  precision–coverage frontier.

## D5 — Treat PostgreSQL and external models as deferred adapters

- **Choice:** Preserve Alembic schema, parameterized SQL constants, Compose profile, and provider
  interfaces, but fail readiness when an unavailable provider is selected.
- **Reason:** Static scaffolding exists, but there is no runtime evidence for PostgreSQL ingestion,
  FTS, pgvector retrieval, or pinned external embedding/reranker artifacts.
- **Alternatives:** Remove all adapter scaffolding; delay the repository until every external
  dependency is integrated.
- **Impact:** `PVR_BACKEND=offline`, `hashing-v1`, and RRF are the only verified defaults. The
  PostgreSQL profile reserves/migrates a future database path but does not switch API resolution.
- **Deferred review:** Migration cycle, database integration/E2E, model license/checksum, offline
  cache behavior, and missing-artifact readiness on Python 3.12 in Docker.

## D6 — Measure only boundaries that were actually run

- **Choice:** Report direct pipeline and warmed in-process FastAPI/TestClient latency separately.
- **Reason:** This keeps the fixture CPU smoke reproducible and prevents it from being mislabeled as
  container or network performance.
- **Alternatives:** Extrapolate Docker/TCP latency or omit latency entirely.
- **Impact:** The latest checked-in HTTP p95 is `7.9523 ms` for 21 sequential samples after five warm-ups;
  a separate QA regeneration reported `2.45 ms`. Container, TCP, reverse proxy, database, and concurrent
  load were not measured.
- **Deferred review:** Formal performance review and Docker/TCP/concurrency benchmark.
