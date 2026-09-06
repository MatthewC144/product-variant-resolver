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
- **Deferred review:** Migration cycle, database integration/E2E, model license/checksum, and
  external-model cache behavior in Docker.

## D6 — Measure and name each runtime boundary separately

- **Choice:** Report direct pipeline, warmed in-process FastAPI/TestClient, and host→Docker loopback
  latency as separate artifacts.
- **Reason:** This keeps the fixture CPU smoke reproducible and prevents it from being mislabeled as
  container or network performance.
- **Alternatives:** Publish one blended number; extrapolate loopback results to remote production;
  omit latency until load testing.
- **Impact:** The dedicated runtime artifact measures 50 sequential host→Docker loopback requests
  after 10 warm-ups at concurrency 1 and records nearest-rank p95 `4.721208 ms`. It includes Docker
  Desktop port forwarding but excludes startup, TLS, proxying, remote networking, concurrent load,
  and PostgreSQL. The fixture report's in-process ASGI p95 remains a different boundary.
- **Deferred review:** Formal performance review and TLS/proxy/remote/concurrency/PostgreSQL
  benchmark on representative infrastructure.

## D7 — Keep the reporter's HTTP client in runtime dependencies

- **Choice:** Declare `httpx2>=2,<3` as a runtime dependency rather than relying on the dev extra.
- **Reason:** The installed `pvr-report` CLI directly invokes FastAPI TestClient to collect its
  in-process HTTP samples, so the HTTP client is required in the shipped image rather than only in
  test environments. A no-cache rebuild with FastAPI 0.141.1, Starlette 1.6.0, httpx2 2.12.0, and
  httpcore2 2.12.0 generated and validated all six report artifacts in the read-only container.
- **Alternatives:** Move `pvr-report` to a separate reporting extra/image; replace TestClient with a
  standard-library or live-socket measurement; keep the dependency dev-only and make the installed
  CLI incomplete.
- **Impact:** The default runtime image is self-contained for API service and report generation,
  but carries an additional runtime dependency. Version ranges remain broad, and the dev extra's
  legacy `httpx` still emits a host warning.
- **Deferred review:** Add a lockfile or constraints file, reconcile `httpx` versus `httpx2`, and
  define a controlled dependency-update/rebuild policy.

## D8 — Keep reviewed real names separate until catalog alignment

- **Choice:** Import the 101 confirmed real-noisy-scan labels as a repository-owned auxiliary
  name-pair corpus, while excluding it from canonical-resolution accuracy, calibration training,
  and threshold selection.
- **Reason:** The source provides valuable initial-output versus human-verified-name evidence, but
  it does not yet provide a trustworthy mapping to this repository's immutable catalog UUIDs and
  slugs. Treating a matching text label as canonical ground truth would overstate what was verified
  and could leak evaluation labels into policy selection.
- **Alternatives:** Merge the records directly into `benchmark.json`; discard the 10 scans where
  recognition returned no candidate; copy the entire source workbook and image collection.
- **Impact:** The repository gains 91 directly comparable name pairs and 10 preserved recognition
  failures without changing the existing fixture-v1 headline metrics. The portable JSON excludes
  machine-specific frame paths and does not require the original workbook at runtime.
- **Deferred review:** Map reviewed labels to catalog identities, decide a casting-family grouped
  split, and only then promote an eligible subset into canonical resolver evaluation.

## D9 — Prefer explicit non-matches over fuzzy catalog assignments

- **Choice:** Align casting families only through exact normalized brand and casting names, and
  assign a canonical UUID only when exact series plus a variant discriminator leave one candidate.
  Fuzzy matching is disabled for ground-truth creation.
- **Reason:** The 120-item fixture catalog is synthetic and covers only 10 casting families, while
  the human corpus contains 97 real casting names. A high string-similarity score could make names
  such as `Dodge Challenger` appear close to `Dodge Charger` or collapse a chassis-specific Nissan
  Skyline into a generic family, creating false labels rather than measuring the resolver.
- **Alternatives:** Select the nearest text match for every row; manually force mappings based on
  domain intuition; create new canonical products automatically from incomplete name fields.
- **Impact:** The first alignment truthfully reports 0 canonical variants, 2 `Toyota Supra`
  casting-family-only records, and 99 unmapped records. This does not improve headline metrics, but
  it establishes exactly how much catalog work is required before real-data evaluation is valid.
- **Deferred review:** Define human-backed catalog provenance, deduplicate repeated scans, resolve
  uncertain series/variant semantics, and introduce a reviewable mapping workflow before expanding
  canonical ground truth.

## D10 — Separate casting identity from provisional variant identity

- **Choice:** Build a human-backed catalog with stable casting entities and nested provisional
  variants. Exact normalized brand/casting creates a casting; exact normalized series/variant
  groups source records into a draft variant. All draft variants require canonical review.
- **Reason:** The 101 confirmed labels reliably name castings, but do not consistently provide
  release year, collector number, color, scale, or edition as separate validated fields. Minting
  production canonical variants from those incomplete labels would make stable IDs depend on
  assumptions that may later be corrected.
- **Alternatives:** Create 101 unrelated products; merge everything by casting and discard variant
  differences; treat the free-text pricing keyword as a final natural key; wait until every field is
  manually re-labeled before retaining any catalog structure.
- **Impact:** All source evidence is usable for retrieval and review now: 101 cases become 97 casting
  entities and 100 provisional variant groups. One exact Chevelle structured duplicate merges while
  retaining both human names and case IDs. No provisional UUID is exposed as canonical truth.
- **Deferred review:** Add an explicit review queue for year, color, scale, series, edition, and
  collector number, then promote reviewed variants into a versioned canonical catalog.

## D11 — Run human knowledge as a non-canonical second RAG source

- **Choice:** Search the canonical fixture catalog and human-backed draft independently on every
  resolution. Canonical candidates continue through calibration and policy; human candidates use a
  separate sparse+dense RRF path and appear only as bounded debug/review evidence.
- **Reason:** The second corpus contains valuable verified names but provisional identities. Keeping
  the paths separate lets the system retrieve real casting knowledge without allowing incomplete
  records to generate a false canonical UUID or contaminate the existing calibration artifact.
- **Alternatives:** Merge provisional variants into the canonical catalog; run human retrieval only
  in an offline script; let the strongest human hit override `no_match`; omit the second source
  until every record is fully reviewed.
- **Impact:** A query such as `Hot Wheels BMW M3 GT2 Neon Speeders` retrieves the matching reviewed
  variant first while the API still returns `no_match` and null canonical identity. Debug output and
  the UI distinguish canonical candidates from human-review candidates; health fails closed if the
  required human catalog cannot load.
- **Deferred review:** Measure retrieval on a non-tautological held-out set, define promotion from
  provisional to canonical identity, and decide whether reviewed evidence may later influence—but
  never bypass—the calibrated decision policy.
