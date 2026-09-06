# Product Variant Resolver — MVP Brief

> Mode: Lite / MVP Mode  
> Status: Confirmed for Lite MVP execution on 2026-09-01  
> Source of truth: `../../../Product Variant Resolver.md` at the parent workspace level  
> Product repository root: `Product Variant Resolver/`

## 1. Product goal

Build an offline-first entity-resolution service that maps a noisy marketplace title to exactly one canonical product variant when evidence is sufficient, and otherwise returns `ambiguous` or `no_match`. The result is a catalog-backed identity, not another search keyword.

The first executable MVP proves the architecture and evaluation loop on a small, version-controlled fixture catalog. It must demonstrate:

- deterministic extraction of high-value syntax signals;
- hybrid sparse, dense, and structured candidate generation;
- reciprocal-rank fusion (RRF) and a CPU-capable pointwise reranker;
- calibrated confidence and abstention;
- explainable retrieval/ranking output in debug mode;
- a reproducible, leakage-aware benchmark with hard negatives.

This MVP is a portfolio-quality engineering validation, not evidence of production accuracy or coverage.

## 2. MVP scope

### 2.1 Included capabilities

- One domain: Hot Wheels product variants represented by a curated fixture catalog.
- A version-controlled fixture catalog containing at least 120 canonical variants across at least 8 casting families and at least 20 near-duplicate variant groups.
- A version-controlled synthetic/curated benchmark containing at least 90 noisy titles: at least 50 `matched`, 20 `ambiguous`, and 20 `no_match` cases.
- Canonical identity represented by both an immutable UUID and an immutable, unique human-readable `canonical_id` slug.
- Syntax-only signal extraction for year, collector number, series position, quantity/multipack hints, and normalized title tokens. Product aliases, color vocabulary, series knowledge, and variant knowledge live in catalog data rather than application conditionals.
- PostgreSQL full-text search as the sparse baseline, exact pgvector search for dense retrieval, and structured soft boosts without aggressive hard filtering.
- RRF candidate fusion.
- One local, CPU-capable pointwise reranker.
- Logistic-regression confidence calibration trained on the grouped training split, threshold selection on the grouped development split, and one final report on the untouched grouped test split.
- `matched`, `ambiguous`, and `no_match` decisions with lowercase API status values.
- FastAPI `POST /resolve` and `GET /health` contracts.
- A minimal HTML/CSS/Vanilla JavaScript debug UI that uses `/resolve` with `debug=true`.
- Reproducible evaluation for Recall@10/25/50, Top-1 accuracy, MRR@10, hard-negative accuracy, precision, coverage, false-match rate, abstention rate, and p50/p95 latency.
- Docker Compose for the API and PostgreSQL/pgvector dependency.
- Unit, integration, API/E2E, and benchmark-gate tests.

### 2.2 EARS acceptance requirements

- **R1 — Canonical resolution:** WHEN a valid title has sufficient evidence for one fixture entity, THE SYSTEM SHALL return `status="matched"`, its immutable UUID, its unique `canonical_id`, product attributes, and a confidence in `[0,1]`.
- **R2 — Ambiguity:** WHEN two or more plausible variants remain within the configured decision margin, THE SYSTEM SHALL return `status="ambiguous"`, no asserted canonical identity, and a machine-readable reason.
- **R3 — Unknown entity:** WHEN no candidate satisfies the configured evidence threshold, THE SYSTEM SHALL return `status="no_match"`, no asserted canonical identity, and a machine-readable reason.
- **R4 — Default response minimization:** WHEN `/resolve` is called without `debug=true`, THE SYSTEM SHALL omit candidate lists, internal ranks/scores, and component timings.
- **R5 — Explainability:** WHEN `/resolve` is called with `debug=true`, THE SYSTEM SHALL include extracted signals, bounded candidate explanations, sparse/dense/RRF/reranker ranks and scores, structured matches/conflicts, and component timings.
- **R6 — Syntax/knowledge boundary:** WHEN a new catalog variant, alias, series, color, or edition is added, THE SYSTEM SHALL make that knowledge searchable through data ingestion without requiring a product-specific application-code branch.
- **R7 — Soft conflict handling:** WHEN an extracted year, color, series, or collector number conflicts with a candidate, THE SYSTEM SHALL retain the candidate until ranking unless a generic syntax/validation rule proves it invalid.
- **R8 — Reproducible split:** WHEN benchmark data is built, THE SYSTEM SHALL assign query cases to train/dev/test by casting family, keep the test labels untouched during calibration and threshold selection, and record the split seed/version.
- **R9 — Retrieval gate:** WHEN the frozen fixture test split is evaluated, THE SYSTEM SHALL achieve Recall@25 at or above 0.95 for cases whose expected status is `matched`.
- **R10 — Ranking gate:** WHEN the frozen fixture test split is evaluated, THE SYSTEM SHALL achieve Top-1 accuracy at or above 0.80 and hard-negative accuracy at or above 0.75 on applicable matched cases.
- **R11 — Reranker value gate:** WHEN pointwise reranking is compared with fused retrieval on the same frozen test cases, THE SYSTEM SHALL improve Top-1 accuracy by at least 0.05 absolute or document a data-backed decision to omit the reranker from the default path.
- **R12 — Reliability gate:** WHEN the threshold frozen on the development split is applied to the test split, THE SYSTEM SHALL achieve matched-decision precision at or above 0.90, false-match rate at or below 0.10 across `ambiguous` and `no_match` cases, and coverage at or above 0.50.
- **R13 — CPU smoke budget:** WHEN the warmed service evaluates the fixture test split on a documented reference CPU with index build and model startup excluded, THE SYSTEM SHALL report p95 `/resolve` latency at or below 1.5 seconds with candidate depth at most 25.
- **R14 — API validation:** WHEN a request has a blank title, a title longer than 500 Unicode code points, an unsupported field, or an out-of-range debug limit, THE SYSTEM SHALL reject it with a structured 4xx response and no stack trace.
- **R15 — Health/readiness:** WHEN catalog, sparse index, dense index, or required local model artifacts are unavailable, THE SYSTEM SHALL expose a non-ready health state and SHALL NOT return a fabricated match.
- **R16 — Quality gate:** WHEN the MVP is proposed complete, THE SYSTEM SHALL have green unit, integration, API/E2E, and benchmark-gate suites plus a generated machine-readable and Markdown evaluation report.
- **R17 — Human-label provenance:** WHEN a reviewed external name dataset is added, THE SYSTEM SHALL preserve the initial system name (including an explicit no-candidate outcome), the human-verified name fields, label confidence, source checksum, and usage limits without treating unmapped names as canonical catalog ground truth.
- **R18 — Conservative catalog alignment:** WHEN human-labeled names are compared with the catalog, THE SYSTEM SHALL assign a canonical UUID only after a unique exact structured match, retain family-only and unmapped outcomes without asserted identities, and freeze the input/output checksums and alignment policy.

The numeric gates above are deliberately modest fixture-MVP gates. Reports and README text must state dataset size, construction method, split strategy, hardware, model versions, and that the figures do not establish production accuracy.

## 3. Out-of-scope / deferred scope

- Ingestion, crawling, or synchronization of the proposed 8,000–30,000 real-world catalog.
- Claims of production readiness, broad marketplace coverage, or externally valid accuracy.
- Multiple product categories or real-time catalog synchronization.
- OpenSearch or another distributed search cluster.
- ANN/HNSW as the default; exact vector search remains the MVP path.
- PostgreSQL-specific BM25 extensions beyond the built-in full-text-search baseline.
- Weighted-score fusion beyond an optional offline comparison; RRF is the MVP default.
- Listwise reranking, model fine-tuning, a model-zoo benchmark, GPU-only models, or paid inference APIs.
- Conditional reranking, batch optimization, comprehensive concurrency/load testing, and a full accuracy/latency frontier.
- Mandatory image input or multimodal fallback.
- Public production deployment, authentication/authorization, tenant isolation, and a complete security audit.
- A large frontend or React application.
- A formal `POST /search` product API. Raw search remains a deferred debug capability.
- FlipRadar runtime integration; the MVP freezes `/resolve` as the future consumer boundary and demonstrates it locally.
- Automated catalog correction, human-review workflows, and real-time observability backends.

## 4. Core user flows

### 4.1 Resolve a clear match

1. A caller submits a noisy title to `POST /resolve`.
2. The backend validates and normalizes the request.
3. The signal extractor emits syntax signals without choosing identity.
4. Sparse, dense, and structured retrievers produce broad candidate sets.
5. RRF fuses candidates; the pointwise reranker orders the top candidates.
6. The calibrator and decision policy return one `matched` identity when score, margin, and conflict evidence satisfy the frozen policy.

### 4.2 Refuse an ambiguous match

1. Two or more near-duplicate variants remain plausible.
2. The calibrated score or top-1/top-2 margin fails the match policy.
3. The API returns `ambiguous` with a reason and no asserted canonical identity.

### 4.3 Refuse an unknown product

1. Retrieval returns only weak or conflicting candidates for an entity absent from the catalog.
2. No candidate reaches the no-match threshold.
3. The API returns `no_match` and does not substitute a nearby known variant.

### 4.4 Inspect a decision

1. A local developer opens the debug UI or sends `debug=true`.
2. The UI displays extracted signals, retrieval order, fused order, reranked order, confidence, conflicts, reason, and timings.
3. Debug output is bounded and excluded by default from the consumer response.

### 4.5 Reproduce evaluation

1. A developer starts the pinned Docker Compose stack and loads the fixture catalog.
2. A deterministic command builds/validates grouped splits, materializes embeddings, and runs evaluation.
3. The run emits versioned JSON and Markdown results containing dataset/model/config/hardware metadata.

## 5. System architecture

```text
Debug UI / future FlipRadar consumer
                 |
          FastAPI boundary
     POST /resolve | GET /health
                 |
           ResolverService
                 |
   +-------------+-------------------+
   |                                 |
SignalExtractor              CandidateRetriever
                           /        |           \
                    Postgres FTS  pgvector   structured
                           \        |           /
                              RRF fusion
                                  |
                     local pointwise reranker
                                  |
                 logistic calibrator + policy
                                  |
               matched / ambiguous / no_match
```

Architectural rules:

- Pipeline components implement narrow interfaces and can be tested independently.
- The catalog is the source of product knowledge; the application owns only generic parsing, retrieval, ranking, and decision algorithms.
- Dense search is exact for the fixture MVP. Sparse and dense raw scores are never directly added; RRF combines ranks.
- Structured attributes affect ranking through explicit boosts/conflict features, not destructive filtering.
- The calibration artifact contains feature schema, training dataset version, model version, and threshold-policy version.
- OpenTelemetry-compatible spans may be emitted locally, but a collector/backend is optional. The API always records component timings for internal metrics.
- The retrieval index includes all known canonical catalog entities, including entities targeted by test queries. Group splitting applies to query examples and any learned/tuned components; test-family queries and labels are not used to fit the reranker/calibrator or select thresholds.

## 6. Frontend/backend boundaries

### Frontend owns

- One local debug page with title input, submit/reset controls, loading/error/empty states, and sections for final decision, signals, candidates, confidence, and timings.
- Calling only documented backend contracts through `fetch`.
- Rendering backend values safely with text APIs; no product-resolution or confidence logic in JavaScript.
- Hiding debug sections when the response does not contain debug data.

### Backend owns

- Validation, normalization, signal extraction, catalog ingestion, retrieval, fusion, ranking, calibration, abstention, metrics, tracing, and error mapping.
- All canonical identity and decision logic.
- The `debug` authorization/configuration hook, even though local MVP access is unrestricted.
- Stable response schemas and bounded debug payloads.

### Shared boundary

- Pydantic-generated OpenAPI is the contract source.
- Lowercase status values are fixed: `matched`, `ambiguous`, `no_match`.
- The frontend must not depend on database schemas, model classes, or undocumented internal scores.

## 7. Tech stack assumptions

- Python 3.12.
- FastAPI, Pydantic v2, Uvicorn.
- PostgreSQL 16 with pgvector; built-in PostgreSQL full-text search is the sparse baseline.
- SQLAlchemy 2 and Alembic for persistence/migrations.
- A pinned, permissively licensed, compact open-source embedding model and pointwise cross-encoder that run on CPU. Exact model IDs, revisions, licenses, and checksums are recorded before implementation is accepted.
- scikit-learn logistic regression for confidence calibration.
- pandas, NumPy, scikit-learn metrics, and Matplotlib for evaluation/report generation.
- pytest, pytest-asyncio, HTTPX, and testcontainers or Docker Compose for tests.
- HTML, CSS, Vanilla JavaScript, and Fetch API for the debug UI.
- Docker and Docker Compose for repeatable local execution.
- OpenTelemetry API/SDK for local spans; an external collector is not required.
- No paid API, cloud dependency, GPU, or network call in the runtime request path. Initial model acquisition may be an explicit setup step; afterward artifacts must be addressable from a pinned local cache/path and missing artifacts must fail readiness.
- Fixture catalog and benchmark live in version control. Generated embeddings, model caches, database volumes, and evaluation output artifacts follow explicit repository/ignore rules.
- The working repository root is this `Product Variant Resolver/` directory; it remains separate from FlipRadar.

## 8. Data model

### 8.1 `ProductVariant`

| Field | Type | Rule |
|---|---|---|
| `canonical_uuid` | UUID | Primary, immutable identity assigned once at ingestion |
| `canonical_id` | string | Unique, immutable slug minted once; contains normalized brand, casting, year, series/edition, color, collector number when present, plus a deterministic collision suffix when required |
| `brand` | string | Required |
| `casting` | string | Required |
| `release_year` | integer/null | Validated plausible range |
| `series` | string/null | Catalog knowledge |
| `color` | string/null | Catalog knowledge |
| `collector_number` | string/null | Stored as normalized string, not numeric |
| `series_position` | string/null | Preserves values such as `3/10` |
| `rarity_tier` | string/null | Catalog knowledge |
| `edition` | string/null | Required in identity key when it distinguishes a variant |
| `created_at` / `updated_at` | timestamp | Audit timestamps; identity fields do not silently remint IDs |

The natural-key fingerprint used to detect duplicates includes every available variant-defining field. Correction of descriptive fields does not mutate UUID or slug. A collision during ingestion is rejected unless a deterministic, documented suffix disambiguates two genuinely distinct variants.

### 8.2 `ProductAlias`

- `id`, `canonical_uuid`, `alias_text`, `normalized_alias`, `alias_type`, `source_id`.
- Unique constraint prevents duplicate normalized aliases per product.
- Aliases are indexed as data and never converted into product-specific code branches.

### 8.3 `Identifier`

- `id`, `canonical_uuid`, `identifier_type`, `identifier_value`, `normalized_value`, `source_id`.
- Supports collector number and future external identifiers without schema-specific columns for every provider.

### 8.4 `ProvenanceRecord`

- `id`, `canonical_uuid`, optional `field_name`, `value_snapshot`, `source_name`, `source_reference`, `retrieved_at`, `license_note`, `confidence_note`.
- The fixture source is explicit (`curated_fixture` or `synthetic_fixture`); synthetic data is never presented as scraped truth.

### 8.5 `BenchmarkCase`

- `case_id`, `query`, `expected_status`, nullable `expected_canonical_uuid`, nullable `expected_canonical_id`, `failure_category`, `casting_family`, `split`, `source_type`, `label_notes`, `dataset_version`.
- `expected_canonical_*` is required only for `matched` cases.
- Split assignment is deterministic by casting family; catalog entities remain searchable in every split.

### 8.6 Runtime value objects

- `ExtractedSignals`: normalized title, year, collector number, series position, quantity/multipack hint, token/color/series hints and parse warnings.
- `CandidateScore`: UUID, per-retriever rank/score, RRF score/rank, structured matches/conflicts, reranker score/rank.
- `CalibrationFeatures`: top-1 score, top-1/top-2 margin, source ranks, identifier/attribute matches, conflicts, and candidate count.
- `Decision`: status, nullable identity, confidence, reason, policy version.

Runtime resolution traces are not persisted by default in the fixture MVP.

### 8.7 `HumanLabeledNamePair`

- `case_id`, `initial_output_status`, nullable `initial_name`, nullable `initial_confidence`.
- Human-confirmed `human_label_name`, `human_label_casting`, brand, series, variant, and pricing keyword.
- Stored pipeline keyword outputs and failure categories support later comparison without rewriting the original human answer.
- These records are an auxiliary evaluation corpus. Until a record is mapped to an immutable catalog UUID/slug, it is excluded from canonical-resolution accuracy, calibration training, and threshold selection.

### 8.8 `HumanCatalogAlignment`

- `case_id`, `status` (`mapped`, `casting_family_only`, or `unmapped`), and a machine-readable reason.
- Nullable canonical UUID/slug, matched casting family, and bounded candidate canonical IDs.
- Family alignment requires exact normalized brand and casting. Canonical alignment additionally requires one unique candidate after exact series and variant-discriminator comparison; fuzzy similarity alone never asserts identity.

## 9. API contracts

### 9.1 `POST /resolve`

Request:

```json
{
  "title": "Hot Wheels 2000 Chevy Nomad Orange #196 NIB lot of 3",
  "debug": false,
  "debug_candidate_limit": 10
}
```

Rules:

- `title`: required, trimmed, 1–500 Unicode code points.
- `debug`: optional, default `false`.
- `debug_candidate_limit`: optional, default 10, allowed 1–25, ignored when `debug=false`.
- Unknown request fields are rejected.

Default matched response:

```json
{
  "status": "matched",
  "canonical_uuid": "7ce6ecde-28b8-4d51-9db3-25c6d67b4b63",
  "canonical_id": "hot-wheels-chevy-nomad-2000-mainline-orange-196",
  "confidence": 0.94,
  "reason": "score_and_margin_above_threshold",
  "product": {
    "brand": "Hot Wheels",
    "casting": "Chevy Nomad",
    "release_year": 2000,
    "series": "Mainline",
    "color": "Orange",
    "collector_number": "196",
    "rarity_tier": "mainline",
    "edition": null
  },
  "policy_version": "fixture-v1"
}
```

Default abstention response:

```json
{
  "status": "ambiguous",
  "canonical_uuid": null,
  "canonical_id": null,
  "confidence": 0.61,
  "reason": "top1_top2_margin_too_small",
  "product": null,
  "policy_version": "fixture-v1"
}
```

`no_match` uses the same nullable identity shape with a reason such as `no_candidate_above_threshold`.

When `debug=true`, the response additionally contains:

```json
{
  "debug": {
    "signals": {},
    "candidates": [],
    "timings_ms": {
      "signal_extraction": 0,
      "sparse": 0,
      "dense": 0,
      "structured": 0,
      "fusion": 0,
      "rerank": 0,
      "calibration": 0,
      "total": 0
    },
    "catalog_version": "fixture-v1",
    "model_versions": {}
  }
}
```

Candidate debug entries are bounded and expose sparse/dense/RRF/reranker ranks and scores plus structured matches/conflicts. They never include embedding vectors or internal stack traces.

### 9.2 `GET /health`

- Returns liveness plus readiness of database, catalog version, sparse index, dense index, reranker artifact, and calibration artifact.
- HTTP 200 when ready; HTTP 503 when alive but unable to resolve safely.

### 9.3 Deferred API

- `POST /search` is not part of the MVP public contract. If later added, it is explicitly debug-only and cannot be treated as canonical resolution.

## 10. Error handling

All errors use:

```json
{
  "error": {
    "code": "invalid_title",
    "message": "title must contain 1 to 500 characters",
    "request_id": "...",
    "details": []
  }
}
```

| Condition | HTTP | Behavior |
|---|---:|---|
| Invalid schema/title/limit | 422 | Stable code; no pipeline execution |
| Unsupported content type or malformed JSON | 400/415 | Stable code; no raw parser exception |
| Catalog/index/model/calibrator not ready | 503 | No guessed resolution; readiness identifies failed dependency |
| Database or local model timeout | 503 | Bounded failure; request ID logged |
| Unexpected internal failure | 500 | Generic client message; structured server log and trace ID |

Pipeline rules:

- Empty candidate sets become a valid `no_match`, not a 500.
- A single retriever failure does not silently degrade to `matched`; the MVP fails the request with 503 unless a later, explicitly versioned policy permits safe partial operation.
- Non-finite scores, missing candidate identity, calibration feature mismatch, and policy/artifact version mismatch fail closed.
- API logging records stage/error metadata but does not record full titles by default.

## 11. Basic security notes

- Treat marketplace titles, fixture imports, aliases, source references, and debug parameters as untrusted input.
- Validate length, type, Unicode normalization, enum/range constraints, and fixture schema before storage or retrieval.
- Use parameterized SQL/SQLAlchemy expressions; never interpolate title or identifier strings into SQL or full-text-query syntax.
- Escape all UI output by assigning text content, not HTML.
- Bound candidate depth, debug output, request size, and component timeouts to reduce accidental resource exhaustion.
- Do not return stack traces, SQL fragments, model paths, environment variables, embeddings, or secrets.
- Keep `debug=false` by default. Local MVP may expose debug without auth only on loopback; any non-local deployment must disable it or add access control.
- Pin model revisions and dependencies; record model license and artifact checksum. Loading arbitrary model IDs or pickle/joblib paths from a request is forbidden.
- The fixture catalog contains no personal data. Full PII/privacy review is deferred unless later data sources introduce seller or user information.
- No authentication, payment, secrets, paid APIs, or user accounts are in the MVP. A targeted security review is required before public exposure or automated external ingestion.

## 12. Testing strategy

### 12.1 Dataset and reproducibility tests

- Validate catalog count, UUID/slug uniqueness, natural-key collisions, alias references, provenance, required failure categories, class counts, and benchmark target consistency.
- Snapshot deterministic fixture and split manifests with a dataset version and checksum.
- Assert that one casting family occurs in only one query split.
- Assert that calibration/threshold training code cannot read test labels before final evaluation.

### 12.2 Unit tests

- Signal parsing: year, collector number, series position, multipack, punctuation/Unicode/noise, false-positive boundaries.
- Slug minting/collision and immutable identity rules.
- Sparse/dense/structured adapter normalization and deterministic tie-breaking.
- RRF calculation, duplicate candidate merge, bounded K, and stable ordering.
- Reranker feature serialization and calibration feature schema.
- Decision policy for clear match, small margin, weak candidate, conflict, non-finite score, and artifact mismatch.
- Pydantic request/response schemas and debug-field omission.

### 12.3 Integration tests

- Apply migrations, ingest fixture data idempotently, build exact vector and full-text indexes, and resolve known fixture cases against PostgreSQL/pgvector.
- Verify that catalog-only changes add knowledge without product-specific code edits.
- Verify readiness transitions for missing catalog/index/model/calibrator.
- Verify local model loading from the pinned artifact/cache and failure when the configured revision is absent.

### 12.4 API/E2E tests

- Exercise one clear `matched`, one near-duplicate `ambiguous`, and one absent-entity `no_match` request.
- Assert default omission and debug inclusion/bounds.
- Assert 4xx validation, 503 fail-closed behavior, lowercase enums, stable error schema, and no stack-trace leakage.
- Smoke-test the debug UI against a live local API for loading, success, abstention, validation error, and safe text rendering.

### 12.5 Evaluation gates

- Run R9–R13 once on the frozen test split after configuration and threshold choices are frozen on train/dev.
- Compare sparse-only, dense-only, RRF, and RRF+pointwise using identical candidates/splits/config metadata.
- Generate JSON and Markdown reports with sample count, category support, uncertainty/raw counts, dataset version, split, model revisions, thresholds, candidate K, hardware, warm-up, and latency method.
- Record per-failure-category results; never hide unsupported categories or replace them with an overall score.
- Store the AI/ranking evaluation rubric and evidence under `docs/evidence/ai-evals/` during implementation handoff.

### 12.6 G1/G2/G3-lite release interpretation

- G1-lite: this brief is confirmed and has no unresolved blocking product, interface, data, or acceptance decision.
- G2: all implementation tasks are complete, their task-level verification passes, and changes remain inside the specified MVP scope.
- G3-lite: all required Lite-scope test layers are green, R9–R13 are reported honestly, QA review
  is PASS or PASS WITH RISKS with limitations preserved, AI-eval evidence is updated, and the
  project log records decisions and known limits.

## 13. Implementation tasks

Each task is intended to be independently committable and verifiable. `task_executor` coordinates; the recommended implementation specialist is shown in brackets.

> Checklist snapshot (2026-09-01): `[x]` means the final QA review contains evidence for the task's
> accepted Lite fixture path. Any task that did not meet its original PostgreSQL, external-model,
> or non-Lite acceptance remains unchecked with a partial/deferred note.

- [x] **T01 — Scaffold the Python service and pinned configuration** `[backend]` _(R13–R16)_  
  Create package, dependency, settings, lint/type/test, artifact-path, and repository-ignore configuration without implementing resolution.  
  **Verify:** application imports; config validation and empty test command pass.

- [x] **T02 — Define API and domain schemas** `[backend]` _(R1–R5, R14)_  
  Add Pydantic/domain value objects for requests, products, signals, candidates, decisions, debug payloads, health, and errors with lowercase statuses.  
  **Verify:** schema tests cover all three statuses, bounds, unknown fields, and default debug omission.

- [x] **T03 — Implement immutable canonical identity rules** `[backend]` _(R1, R6)_  
  Implement UUID/slug minting, natural-key fingerprinting, collision rejection/suffixing, and immutability checks.  
  **Verify:** unit tests prove uniqueness across color/year/series/edition differences and stable IDs across descriptive corrections.

- [x] **T04 — Add PostgreSQL/pgvector schema migrations** `[backend]` _(R1, R6, R15)_
  Create product, alias, identifier, provenance, and index metadata tables plus constraints/indexes.  
  **Verify:** migration upgrade from empty DB and downgrade/upgrade cycle pass.
  **Status:** Complete — revision `0001` was verified on an isolated PostgreSQL 16/pgvector
  database with an empty → upgrade → downgrade → upgrade cycle. The reproducible runner asserts
  the seven application tables, primary/unique/check/cascade-FK constraints, required btree/GIN
  indexes, `tsvector`, `vector(192)`, the vector extension, and the final Alembic revision.

- [x] **T05 — Create the versioned fixture catalog** `[task_executor]` _(R1, R6)_  
  Curate at least 120 variants, 8 families, and 20 near-duplicate groups with explicit synthetic/curated provenance.  
  **Verify:** fixture validator passes counts, references, uniqueness, provenance, and schema checks.

- [x] **T06 — Create the versioned grouped benchmark** `[task_executor]` _(R2, R3, R8)_  
  Curate at least 90 labeled noisy titles with required status counts, failure categories, casting families, and deterministic group splits.  
  **Verify:** manifest tests prove class minima, valid expected identities, no family overlap, frozen version/checksum, and test-label isolation.

- [ ] **T07 — Implement idempotent fixture ingestion** `[backend]` _(R6, R15)_  
  Load validated catalog files into PostgreSQL, preserve immutable IDs, and record catalog/index version metadata.  
  **Verify:** first and repeated ingestion produce identical rows; invalid/colliding fixtures fail transactionally.
  **Status:** Partial/deferred — in-memory fixture ingestion is idempotent and verified; PostgreSQL
  ingestion and transactional failure behavior are not implemented or tested.

- [x] **T08 — Implement generic signal extraction** `[backend]` _(R6, R7)_  
  Extract normalized syntax signals and generic token hints without product-specific series/variant conditionals.  
  **Verify:** parser unit suite covers noisy, missing, conflicting, Unicode, and multipack examples.

- [ ] **T09 — Implement PostgreSQL sparse retrieval** `[backend]` _(R5, R6, R9)_  
  Index canonical text and aliases with built-in full-text search and return ranked, typed candidates.  
  **Verify:** integration tests recover exact identifiers/rare terms and use parameterized queries.
  **Status:** Deferred — the verified sparse path is an in-memory token baseline. Parameterized SQL
  constants exist, but PostgreSQL FTS execution is not implemented or integration-tested.

- [ ] **T10 — Implement exact dense retrieval** `[backend]` _(R5, R9, R13, R15)_  
  Add pinned local CPU embeddings, deterministic catalog text construction, materialization/version checks, and exact pgvector search.  
  **Verify:** repeatable embeddings/index version, semantic-alias retrieval, offline execution, and missing-artifact readiness failure pass.
  **Status:** Partial/deferred — exact in-memory retrieval with deterministic `hashing-v1` is
  verified; it is not a neural embedding model, and pinned external artifacts plus pgvector search
  remain unimplemented.

- [x] **T11 — Implement structured candidate scoring** `[backend]` _(R5, R7, R9)_  
  Produce explicit match/conflict features and soft boosts/expansion without destructive attribute filters.  
  **Verify:** a correct candidate survives a deliberately wrong year/color signal while conflicts remain visible.

- [x] **T12 — Implement RRF fusion** `[backend]` _(R5, R9)_  
  Merge sparse/dense/structured candidates with deterministic RRF, deduplication, tie-breaking, and bounded depth.  
  **Verify:** formula fixtures and duplicate/tie/empty-source tests pass.

- [x] **T13 — Assemble the candidate retrieval service** `[backend]` _(R5, R7, R9, R15)_  
  Orchestrate retrievers, preserve per-source explanations, and fail closed on unapproved partial failure.  
  **Verify:** integration tests return bounded candidates and source ranks for normal/empty/failure cases.

- [ ] **T14 — Implement the local pointwise reranker** `[backend]` _(R5, R10, R11, R13, R15)_  
  Rerank at most 25 fused candidates using a pinned CPU model and expose typed scores/ranks.  
  **Verify:** batching/order/artifact-version tests pass and an offline hard-negative smoke case is correctly reordered.
  **Status:** Partial/deferred — `heuristic-v1` is implemented for opt-in ablation, but it is not a
  pinned cross-encoder. Its frozen-test Top-1 gain over RRF is `0.0`, so RRF remains the default.

- [x] **T15 — Implement calibration training and artifact metadata** `[backend]` _(R8, R12, R15)_  
  Fit logistic regression only on grouped training data, validate feature schema, and persist dataset/model/artifact versions.  
  **Verify:** deterministic training, no test access, finite probabilities, serialization round trip, and schema mismatch failure pass.

- [x] **T16 — Implement threshold selection and decision policy** `[backend]` _(R1–R3, R7, R12)_  
  Select thresholds on dev data and freeze score/margin/conflict rules for all three statuses.  
  **Verify:** policy unit tests cover clear, ambiguous, unknown, conflict, empty, and non-finite cases; test labels are not read.

- [x] **T17 — Assemble `ResolverService`** `[backend]` _(R1–R5, R7, R13, R15)_  
  Connect extraction, retrieval, fusion, reranking, calibration, decision, timings, and version metadata behind one interface.  
  **Verify:** service integration tests resolve canonical match, ambiguity, no-match, and dependency failure.

- [x] **T18 — Implement FastAPI `/resolve` and `/health`** `[backend]` _(R1–R5, R14, R15)_  
  Add documented endpoints, error mapping, request IDs, default-minimal response, bounded debug response, and readiness checks.  
  **Verify:** OpenAPI/schema snapshots and API tests cover success, validation, debug, readiness, and stack-trace omission.

- [x] **T19 — Add timing, tracing, and privacy-safe logging** `[backend]` _(R5, R13, R14)_  
  Instrument pipeline stages and errors without logging raw titles by default.  
  **Verify:** trace/timing tests assert stage presence, request correlation, and title redaction.

- [x] **T20 — Implement evaluation metrics and frozen runner** `[backend]` _(R8–R13, R16)_  
  Calculate retrieval/ranking/reliability/latency and ablations from one immutable test manifest after config freeze.  
  **Verify:** metric unit fixtures, zero-denominator handling, deterministic runs, and train/dev/test guard tests pass.

- [x] **T21 — Generate evaluation reports and plots** `[task_executor]` _(R9–R13, R16)_  
  Emit machine-readable JSON, Markdown tables, retrieval/reranker comparison, precision–coverage, and latency metadata with the non-production disclaimer.  
  **Verify:** report schema and required-disclosure checks pass; every headline number is traceable to raw counts/config.

- [x] **T22 — Build the minimal debug UI** `[frontend]` _(R4, R5, R14)_  
  Implement the single-page query/decision/signals/candidates/confidence/timings interface using safe text rendering and documented API fields only.  
  **Verify:** UI smoke tests cover loading, match, abstention, validation error, debug bounds, and markup-like title text.

- [x] **T23 — Add Docker Compose local runtime** `[backend]` _(R13, R15, R16)_  
  Package API and PostgreSQL/pgvector with migration, fixture-ingestion, model-cache, healthcheck, and reproducible startup instructions.  
  **Verify:** clean compose startup becomes ready, serves three E2E cases, and reports non-ready when an artifact is removed.
  **Status:** Complete for the Lite default offline runtime — the Python 3.12.14 image built and
  became healthy, served UI plus all three decision states, preserved non-root/read-only behavior,
  and failed closed in a dedicated missing-catalog container. PostgreSQL ingestion/retrieval and
  migration-cycle E2E remain deferred under T04/T07/T09/T10 rather than being claimed here.

- [x] **T24 — Run the full QA and benchmark gates** `[qa]` _(R1–R16)_  
  Execute unit, integration, API/E2E, UI smoke, data validation, and frozen benchmark suites on documented CPU hardware.  
  **Verify:** publish PASS/FAIL coverage mapping from every requirement to test/result; any failed metric remains visible.
  **Status:** Complete for the accepted Lite fixture scope — QA published **PASS WITH RISKS**, mapped
  R1–R16, kept the host suite 38/38 green, verified the Python 3.12 default container, reran mounted
  API/reporting suites, and validated frozen benchmark/report artifacts. PostgreSQL/pgvector,
  external models, live-browser UI, TLS/proxy/remote networking, and concurrency remain outside this
  completion claim.

- [x] **T25 — Record MVP decisions, evidence, and limits** `[doc_curator]` _(R6, R8–R16)_  
  Update decisions, architecture/evaluation docs, AI-eval evidence, README result disclosures, and `PROJECT-LOG.md` without inventing unmeasured claims.  
  **Verify:** documentation check links dataset/model/config versions, raw result artifact, hardware, known limitations, and deferred work.

- [x] **T26 — Import the reviewed real-noisy name-pair corpus** `[task_executor]` _(R8, R16, R17)_
  Convert the confirmed local labeling queue into a portable repository-owned JSON corpus, retain explicit no-candidate failures, freeze source/output checksums, and keep the corpus outside canonical accuracy and calibration gates until catalog IDs are assigned.
  **Verify:** importer reports 101 confirmed records, validators prove 91 paired initial names plus 10 explicit no-candidate cases, excluded source rows remain excluded, checksums match, and focused tests pass.

- [x] **T27 — Align reviewed names to the fixture catalog conservatively** `[backend]` _(R6, R16–R18)_
  Build a deterministic alignment artifact with exact structured matching, explicit family-only and unmapped outcomes, null identities for unresolved records, and checksums for both source datasets and generated output.
  **Verify:** all 101 records receive one alignment status; current coverage is truthfully reported as 0 canonical mappings, 2 exact casting-family-only matches, and 99 unmapped records; no unresolved record asserts a UUID; regeneration and full tests pass.

### Task order and handoff

Recommended dependency order:

```text
T01 → T02 → T03 → T04
               ├→ T05 → T07
               └→ T06
T08 → T09/T10/T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18/T19
T05/T06/T17 → T20 → T21
T18 → T22
T04/T07/T18 → T23
all implementation tasks → T24 → T25
```

After this brief is confirmed, hand T01 onward to `task_executor`, using `backend` for the service/retrieval/evaluation work, `frontend` only for T22, `qa` for T24, and `doc_curator` for T25. Architect, security, and performance agents are not default MVP participants; request a targeted security review before public exposure and a performance review only when moving beyond the fixture CPU smoke budget.
