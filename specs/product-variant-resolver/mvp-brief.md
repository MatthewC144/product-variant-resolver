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
- A 100-row, text-only Hot Wheels Wiki pilot frozen as review-only staging data with source
  revision, CC-BY-SA attribution, checksums, and no automatic canonical promotion.
- A deterministic cross-catalog review that separates exact existing-family candidates from
  possible new families while keeping every Wiki row on human-review hold.
- A human-adjudication queue that groups repeated releases into one casting-family decision,
  prioritizes exact candidates, and requires attributable evidence before promotion.
- A priority-1 evidence packet that presents Wiki releases and retained human-label evidence side
  by side while separating family-merge recommendations from unverified variants.
- A fail-closed decision applier that records attributable family confirmations separately from the
  original queue and cannot turn held variants into canonical or PostgreSQL records.
- A bounded priority-2 research packet that requires a dedicated casting page plus exact-name
  confirmation from a non-Fandom publisher before recommending a new family, while holding
  ambiguous names and every release variant.
- A fail-closed priority-2 decision layer that applies the project owner's batch response only
  when it covers and agrees with the frozen research packet, while preserving prior decisions and
  keeping new family decisions outside canonical and PostgreSQL storage.

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
- **R19 — Human-backed catalog draft:** WHEN confirmed human labels are converted into catalog knowledge, THE SYSTEM SHALL create stable casting and provisional-variant IDs, preserve every source case and label alias, deduplicate only exact normalized structured identities, and prevent unreviewed provisional variants from being returned as canonical ground truth.
- **R20 — Dual-source retrieval boundary:** WHEN a title is resolved, THE SYSTEM SHALL search both the canonical catalog and the human-backed review catalog, use only canonical candidates for the final identity decision, and expose bounded human-knowledge candidates with review status only when debug output is requested.
- **R21 — Governed external catalog pilot:** WHEN an external Wiki table is imported, THE SYSTEM SHALL use a documented API and identifiable client, freeze source revision/license/checksums, omit non-text media, retain unknown fields as null, and mark every record review-only without changing canonical resolution or evaluation labels.
- **R22 — Conservative external-catalog review:** WHEN staged Wiki records are compared with existing catalogs, THE SYSTEM SHALL use only exact normalized brand/casting family matches, expose candidate IDs and reasons, freeze all input/output checksums, disable fuzzy and identifier-only promotion, and retain null canonical identity until a human decision is recorded.
- **R23 — Attributable human-adjudication queue:** WHEN external pre-review is prepared for a person, THE SYSTEM SHALL group every source row exactly once by normalized casting family, prioritize exact existing-family candidates, permit only merge/create/hold/reject decisions, require reviewer/time/reason/evidence for completion, and keep every pending group ineligible for promotion.
- **R24 — Priority-1 family evidence:** WHEN a reviewer examines an exact existing-family candidate, THE SYSTEM SHALL show all contributing Wiki release rows, original and human-verified label evidence, target family ID, observed series/variant differences, a family-scoped recommendation, an explicit variant hold, and an empty reviewer confirmation without making the item promotion eligible.
- **R25 — Validated family-decision application:** WHEN an attributable reviewer decision batch is applied, THE SYSTEM SHALL require a permitted decision, valid timestamp, reviewer, provenance, reason, evidence, casting-family-only scope, held variants, and an exact candidate target for merges; update completed/pending counts in a derived artifact; and reject invalid targets without modifying the original queue or creating promotion-eligible records.
- **R26 — Bounded new-family research:** WHEN priority-2 possible-new families are researched, THE SYSTEM SHALL select a deterministic bounded batch, require a dedicated casting page and an exact-name confirmation from at least one non-Fandom publisher before recommending `create_new_casting`, hold disambiguated or insufficient identities, preserve source URLs and concise observed claims, keep reviewer confirmation pending, hold every release variant, and create no canonical or PostgreSQL record.
- **R27 — Validated priority-2 decision application:** WHEN the project owner approves a priority-2 research batch, THE SYSTEM SHALL record reviewer/time/provenance/reason/evidence in a separate decision file, require complete one-time coverage of the frozen research packets, require each outcome to match the approved recommendation, reject unsupported creation or widened variant scope, preserve earlier completed decisions, derive cumulative completed/pending/create/hold counts, and keep all affected families ineligible for canonical or PostgreSQL promotion.
- **R28 — Cumulative priority-2 research sequencing:** WHEN a later priority-2 research batch is built, THE SYSTEM SHALL verify and use the latest checksum-frozen cumulative adjudication queue, skip every completed family, select the next bounded pending families in queue order, hold a display name that maps to distinct homonymous casting tools, preserve two-source evidence and reviewer/variant/promotion boundaries, and reproduce both the earlier and current batch outputs deterministically.
- **R29 — Cumulative priority-2 owner decisions:** WHEN the project owner approves a later priority-2 research batch, THE SYSTEM SHALL bind that authorization to the exact frozen research packet, require complete recommendation-matching family-only decisions, append rather than replace all earlier decision-batch history, derive a new checksum-frozen cumulative queue, reject changed or incomplete outcomes, and keep every release variant and catalog/database promotion held.
- **R30 — Related-casting identity boundary:** WHEN a researched name has a related predecessor or similarly named casting page, THE SYSTEM SHALL retain the related page and an explicit distinction, classify the queued family by whether its exact name uniquely identifies the current casting tool, hold same-name homonyms, and avoid treating a differently named predecessor as either an automatic merge or an automatic hold.

The numeric gates above are deliberately modest fixture-MVP gates. Reports and README text must state dataset size, construction method, split strategy, hardware, model versions, and that the figures do not establish production accuracy.

## 3. Out-of-scope / deferred scope

- Bulk ingestion or synchronization of the proposed 8,000–30,000 real-world catalog beyond the
  accepted 100-row review-only pilot.
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
          SignalExtractor
                 |
   +-------------+-----------------------+
   |                                     |
Canonical catalog RAG             Human knowledge RAG
sparse + dense + structured       sparse + hashing dense
   |                                     |
RRF + optional reranker           provisional suggestions
   |                                     |
calibrator + policy                       |
   +-------------+-----------------------+
                 |
matched / ambiguous / no_match + bounded debug evidence
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

### 8.9 `HumanBackedCatalogDraft`

- One casting entity per exact normalized brand/casting pair, with a deterministic `casting_uuid`, readable `casting_id`, and all contributing source case IDs.
- Nested provisional variants group exact normalized series/variant labels and retain every human name, pricing keyword, initial name, failure category, and source case ID.
- Every provisional variant has a stable UUID/ID but remains `needs_canonical_review`; these identifiers support review and retrieval indexing and are not API canonical identities.

### 8.10 `HumanKnowledgeCandidate`

- Casting and provisional-variant IDs, human name examples, source case IDs, reviewed series/variant labels, and mandatory `needs_canonical_review` status.
- Sparse, dense, and RRF ranks/scores plus matched tokens for debug explanation.
- Human candidates never populate `ResolveResponse.canonical_uuid`, `canonical_id`, or `product`; those fields remain controlled by the canonical catalog policy.

### 8.11 `ExternalCatalogStagingRecord`

- Stable source-record ID, source table row, brand, year, toy/collector numbers, model label,
  parsed casting, optional variant note, series, series position, and intentionally nullable color.
- Source page/revision/timestamp/license metadata is repeated per record so exported review rows
  retain attribution.
- `canonical_uuid=null`, `review_status=needs_canonical_review`, and an explicit staging-only usage
  value prevent the external table from becoming implicit ground truth.
- Raw wikitext, normalized JSON, and a manifest are frozen separately with SHA-256 checksums. Photo
  columns are omitted and no image request is made.

### 8.12 `ExternalCatalogReviewRecord`

- Repeats the source row ID and review-relevant product fields, plus its normalized brand/casting
  family key.
- Records exact canonical-family IDs, exact human casting/variant IDs, match status, reason, and a
  recommended human-review action. Candidate IDs are evidence, not assigned identity.
- `promotion_decision=hold_for_human_review`, `promotion_eligible=false`, and null canonical fields
  remain mandatory until a separately reviewed promotion decision exists.
- The review manifest freezes the staging, canonical, human-backed, and review JSON checksums and
  reports both row-level and distinct-family-level counts.

### 8.13 `ExternalCatalogAdjudicationFamily`

- Stable family-review ID, priority, display and normalized family names, and all contributing
  source rows preserve the relationship between 100 releases and 53 casting decisions.
- Pre-review evidence includes exact candidate IDs plus a non-binding suggested action and reason.
- Reviewer decision permits `merge_existing_family`, `create_new_casting`, `hold`, or `reject` and
  requires reviewer, timestamp, written reason, and evidence references before completion.
- Pending decisions have null decision fields and `promotion_eligible=false`. The queue JSON,
  human-readable worksheet, and manifest are deterministically reproducible.

### 8.14 `PriorityOneFamilyEvidencePacket`

- Links one priority-1 family-review ID to its exact human casting ID/UUID and all contributing Wiki
  rows.
- Retains human label, initial source name, series, variant, failure categories, and source case IDs
  from each provisional human variant.
- Separately records exact family-name evidence, observed series equality, shared explicit variant
  tokens, and `variant_identity_verified=false`.
- Machine recommendation may propose `merge_existing_family` at `casting_family_only` scope, while
  reviewer confirmation stays pending and the variant decision stays `hold`.

### 8.15 `ExternalCatalogFamilyDecisionBatch`

- Batch ID, reviewer role, UTC decision timestamp, and conversation/source provenance apply to a
  bounded set of family decisions.
- Each decision references one stable family-review ID, a permitted decision, written reason,
  evidence references, `casting_family_only` scope, and `variant_decision=hold`.
- `merge_existing_family` requires its target to be an exact pre-review candidate; invalid,
  duplicate, unknown, anonymous, unsupported, or incomplete decisions fail closed.
- The derived adjudicated queue records completed and pending counts while retaining
  `promotion_eligible=false`; the original all-pending queue remains immutable.

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
    "human_knowledge_candidates": [],
    "timings_ms": {
      "signal_extraction": 0,
      "human_knowledge_retrieval": 0,
      "sparse": 0,
      "dense": 0,
      "structured": 0,
      "fusion": 0,
      "rerank": 0,
      "calibration": 0,
      "total": 0
    },
    "catalog_version": "fixture-v1",
    "human_catalog_version": "human-backed-catalog-v1",
    "model_versions": {}
  }
}
```

Canonical and human-knowledge debug entries share the request's `debug_candidate_limit`. Canonical
entries expose sparse/dense/RRF/reranker ranks and scores plus structured matches/conflicts. Human
entries expose reviewed names, provisional identity status, matched tokens, and hybrid retrieval
ranks. They never include embedding vectors or internal stack traces.

### 9.2 `GET /health`

- Returns liveness plus readiness of database, canonical catalog, human review catalog, both retrieval indexes, reranker artifact, and calibration artifact.
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
- Human-knowledge loader validation, deterministic hybrid ordering, bounded results, and no-shared-token behavior.

### 12.3 Integration tests

- Apply migrations, ingest fixture data idempotently, build exact vector and full-text indexes, and resolve known fixture cases against PostgreSQL/pgvector.
- Verify that catalog-only changes add knowledge without product-specific code edits.
- Verify readiness transitions for missing catalog/index/model/calibrator.
- Verify the human review catalog is queried independently and cannot assert canonical identity.
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

- [x] **T07 — Implement idempotent fixture ingestion** `[backend]` _(R6, R15)_
  Load validated catalog files into PostgreSQL, preserve immutable IDs, and record catalog/index version metadata.  
  **Verify:** first and repeated ingestion produce identical rows; invalid/colliding fixtures fail transactionally.
  **Status:** Complete for the Lite fixture scope — the SQLAlchemy repository writes product,
  alias, identifier, provenance, search-document, and version rows in one transaction. An isolated
  PostgreSQL 16/pgvector run proved exact repeated-ingestion stability, collision rollback, and
  refusal to interpret a missing snapshot row as an implicit product deletion. T09 and T10 later
  added the separately verified sparse and exact-dense query paths.

- [x] **T08 — Implement generic signal extraction** `[backend]` _(R6, R7)_  
  Extract normalized syntax signals and generic token hints without product-specific series/variant conditionals.  
  **Verify:** parser unit suite covers noisy, missing, conflicting, Unicode, and multipack examples.

- [x] **T09 — Implement PostgreSQL sparse retrieval** `[backend]` _(R5, R6, R9)_
  Index canonical text and aliases with built-in full-text search and return ranked, typed candidates.  
  **Verify:** integration tests recover exact identifiers/rare terms and use parameterized queries.
  **Status:** Complete for the Lite fixture scope — `PVR_BACKEND=postgres` validates installed
  catalog metadata and row counts, then uses parameter-bound `websearch_to_tsquery` plus
  `ts_rank_cd` for canonical sparse candidates. An isolated PostgreSQL 16 run verified identifier
  Top-1, 12/12 matched-case Recall@25, GIN-index compatibility, injection-shaped input safety,
  real HTTP resolution, and checksum-mismatch readiness failure. Dense retrieval remains the
  in-memory T10 baseline.

- [x] **T10 — Implement exact dense retrieval** `[backend]` _(R5, R9, R13, R15)_
  Add pinned local CPU embeddings, deterministic catalog text construction, materialization/version checks, and exact pgvector search.  
  **Verify:** repeatable embeddings/index version, semantic-alias retrieval, offline execution, and missing-artifact readiness failure pass.
  **Status:** Complete for the Lite deterministic baseline — the versioned `hashing-v1` catalog
  vectors are materialized transactionally into `vector(192)` rows and queried with exact cosine
  distance. Startup validates dense metadata plus every expected UUID/version/checksum. An isolated
  PostgreSQL 16.14 run proved 120/120 rows, identical repeated materialization, catalog-alias
  retrieval, 12/12 Recall@25, missing-row readiness failure, and real HTTP resolution. This is not
  a neural embedding model; external model selection remains deferred.

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
  and failed closed in a dedicated missing-catalog container. T04 now verifies PostgreSQL migration
  lifecycle, T07 verifies fixture ingestion, and T09/T10 verify PostgreSQL sparse+dense API
  retrieval in separate isolated runs.

- [x] **T24 — Run the full QA and benchmark gates** `[qa]` _(R1–R16)_  
  Execute unit, integration, API/E2E, UI smoke, data validation, and frozen benchmark suites on documented CPU hardware.  
  **Verify:** publish PASS/FAIL coverage mapping from every requirement to test/result; any failed metric remains visible.
  **Status:** Complete for the accepted Lite fixture scope — QA published **PASS WITH RISKS**, mapped
  R1–R16, kept the host suite 38/38 green, verified the Python 3.12 default container, reran mounted
  API/reporting suites, and validated frozen benchmark/report artifacts. Later isolated checks cover
  PostgreSQL FTS and exact pgvector at 120 rows; external models, live-browser UI,
  TLS/proxy/remote networking, concurrency, and 3,000-row performance remain outside this claim.

- [x] **T25 — Record MVP decisions, evidence, and limits** `[doc_curator]` _(R6, R8–R16)_  
  Update decisions, architecture/evaluation docs, AI-eval evidence, README result disclosures, and `PROJECT-LOG.md` without inventing unmeasured claims.  
  **Verify:** documentation check links dataset/model/config versions, raw result artifact, hardware, known limitations, and deferred work.

- [x] **T26 — Import the reviewed real-noisy name-pair corpus** `[task_executor]` _(R8, R16, R17)_
  Convert the confirmed local labeling queue into a portable repository-owned JSON corpus, retain explicit no-candidate failures, freeze source/output checksums, and keep the corpus outside canonical accuracy and calibration gates until catalog IDs are assigned.
  **Verify:** importer reports 101 confirmed records, validators prove 91 paired initial names plus 10 explicit no-candidate cases, excluded source rows remain excluded, checksums match, and focused tests pass.

- [x] **T27 — Align reviewed names to the fixture catalog conservatively** `[backend]` _(R6, R16–R18)_
  Build a deterministic alignment artifact with exact structured matching, explicit family-only and unmapped outcomes, null identities for unresolved records, and checksums for both source datasets and generated output.
  **Verify:** all 101 records receive one alignment status; current coverage is truthfully reported as 0 canonical mappings, 2 exact casting-family-only matches, and 99 unmapped records; no unresolved record asserts a UUID; regeneration and full tests pass.

- [x] **T28 — Build a versioned human-backed catalog draft** `[backend]` _(R6, R16–R19)_
  Convert confirmed labels into deterministic casting entities and provisional variant groups, preserve source provenance and aliases, and keep the draft eligible for retrieval/review but excluded from canonical API responses and model calibration.
  **Verify:** 101 reviewed records produce 97 unique casting entities and 100 provisional variants; one exact structured duplicate is merged without losing either source; IDs and checksums are stable; all variants require canonical review; full tests pass.

- [x] **T29 — Connect the human catalog as the second RAG source** `[backend/frontend]` _(R4–R6, R14–R16, R19–R20)_
  Load and validate the human-backed draft at startup, build deterministic sparse+dense retrieval over provisional variants, execute it independently from canonical retrieval, expose bounded debug candidates and health metadata, and render the review-only evidence safely in the debug UI.
  **Verify:** an exact reviewed BMW query ranks the correct provisional variant first while returning no canonical UUID; an unknown query returns no human suggestion; missing human catalog fails readiness; default responses omit debug evidence; traces/timings include the second retrieval stage; API/UI/full suites pass.

- [x] **T30 — Import a governed 100-row Hot Wheels Wiki pilot** `[backend]` _(R6, R16, R21)_
  Fetch one completed yearly list through the MediaWiki API, freeze its revision and license, parse
  the first 100 valid text rows into review-only staging records, and produce attribution plus
  checksum evidence without downloading images or changing the canonical catalog.
  **Verify:** parser tests cover markup, series, color-variant suffixes, markers, determinism, bounds,
  and image omission; the frozen validator proves 100 unique toy numbers, 100 null colors, 0
  canonical promotions, sequential source rows, and matching raw/normalized checksums.
  **Status:** Complete for the 2025 pilot at revision `790665`. The API reported `CC-BY-SA`; two
  identified requests retrieved rights metadata and one 93 KB revision rather than crawling 100
  item pages. The normalized dataset contains 100 records, including 45 explicit variant notes,
  and remains excluded from canonical resolution, calibration, and evaluation.

- [x] **T31 — Build the 100-row cross-catalog promotion review** `[backend]` _(R6, R16, R22)_
  Compare every Wiki staging row with the canonical fixture and human-backed draft using exact
  normalized brand/casting keys; freeze row-level reasons, candidate IDs, review actions, and all
  input/output checksums without issuing an identity or database write.
  **Verify:** the deterministic builder and checked-in report agree; 100 rows map to 53 distinct
  casting families; 9 rows / 4 families have exact human-family candidates; 91 rows / 49 families
  have no exact candidate; all 100 remain held and canonical promotion count is zero.
  **Status:** Complete. There are no exact canonical-fixture family matches. The four exact
  human-backed families are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and
  `Tesla Model S Plaid`; their existing IDs are review evidence only.

- [x] **T32 — Prepare the attributable 53-family adjudication queue** `[backend]` _(R6, R16, R23)_
  Collapse repeated Wiki releases into deterministic family review units, preserve every source
  row, prioritize the four exact existing-family candidates, define the reviewer decision
  contract, and emit both machine-readable JSON and a readable Markdown worksheet.
  **Verify:** all 100 unique source rows appear exactly once across 53 stable family IDs; priorities
  are 4 existing-candidate and 49 research-required families; all decisions are pending and all
  groups are promotion-ineligible; output checksums and `--check` regeneration pass.
  **Status:** Complete. No source or database request occurs. The decision contract permits only
  merge/create/hold/reject and requires reviewer, time, reason, and evidence. This milestone
  prepares human work but does not claim a human has completed it.

- [x] **T33 — Assemble priority-1 side-by-side family evidence** `[backend]` _(R6, R16, R24)_
  Join the four priority-1 queue groups with their retained human-backed source evidence, preserve
  all nine Wiki release rows, calculate only explicit comparison facts, and render deterministic
  JSON plus a readable Markdown reviewer packet.
  **Verify:** exactly four packets cover nine unique source rows; each has one exact human target;
  original/human names and source IDs are retained; Subaru's shared `zamac` token is visible but
  not treated as variant confirmation; all family recommendations are merge-only, all variant
  recommendations are hold, reviewer confirmations are empty, and output checksums regenerate.
  **Status:** Complete. The evidence supports proposing family-level merge for all four exact-name
  candidates, but differing or incomplete year/series/color evidence prevents any release-variant
  promotion. The project owner must still accept or reject each family recommendation.

- [x] **T34 — Apply the project-owner priority-1 family decisions** `[backend]` _(R6, R16, R25)_
  Record the project owner's follow-up authorization in a separate decision batch, validate every
  merge against its exact human-family candidate and evidence, and derive an adjudicated queue
  without changing the original queue, release variants, canonical catalog, or database.
  **Verify:** four decisions complete as attributable family-only merges; nine Wiki release rows
  remain held; 49 family decisions remain pending; promotion eligibility stays zero; an invalid
  merge target fails closed; hashes and `--check` deterministic regeneration pass.
  **Status:** Complete. The accepted targets are the existing human-backed families for `'67 Chevy
  C10`, `Purple Passion`, `Subaru BRZ`, and `Tesla Model S Plaid`. This records family linkage only;
  it creates no canonical UUID and grants no release-variant identity.

- [x] **T35 — Research priority-2 family batch 01** `[backend]` _(R6, R16, R26)_
  Select the first ten pending priority-2 families, record their dedicated Wiki casting-page
  status and non-Fandom exact-name evidence, derive conservative family-level recommendations,
  and freeze readable and machine-readable evidence without applying a reviewer decision.
  **Verify:** exactly ten families / nineteen Wiki rows are represented in queue order; nine have
  the evidence required for a `create_new_casting` recommendation; `'55 Chevy` is held because its
  source title disambiguates three casting tools; all reviewer confirmations remain pending, all
  variants remain held, promotion stays zero, invalid same-host evidence fails closed, and hashes
  plus deterministic regeneration pass.
  **Status:** Complete. The results are machine recommendations only. No catalog, PostgreSQL,
  runtime, calibration, or evaluation artifact changed.

- [x] **T36 — Apply project-owner priority-2 batch-01 decisions** `[backend]` _(R6, R16, R27)_
  Record the owner's follow-up approval in a separate decision batch, validate complete agreement
  with all ten frozen research packets, preserve the four prior family merges, and derive a new
  cumulative queue without mutating the T34 queue or any catalog/database.
  **Verify:** nine `create_new_casting` decisions and the `'55 Chevy` hold complete under
  `project_owner`; the cumulative queue reports fourteen completed / thirty-nine pending, four
  prior merges, nine accepted new-family decisions, one family hold, twenty-eight held variants,
  and zero promotion eligibility; changed outcomes and incomplete batches fail closed; hashes and
  deterministic regeneration pass.
  **Status:** Complete. New casting outcomes are accepted review-layer decisions only. They do not
  yet mint canonical UUIDs, verify release variants, or create PostgreSQL rows.

- [x] **T37 — Research priority-2 family batch 02 from the cumulative queue** `[backend]` _(R6, R16, R26, R28)_
  Verify the T36 adjudicated-queue checksum, select the next ten still-pending priority-2 families,
  record Wiki and non-Fandom exact-name evidence, distinguish one-page identities from homonymous
  casting tools, and freeze readable and machine-readable recommendations without applying them.
  **Verify:** exactly ten families / eighteen Wiki rows are selected after all fourteen completed
  families; nine meet the evidence rule for `create_new_casting`; `Batman and Robin Batmobile`
  remains held because the display name also identifies a separate 2004 100% Hot Wheels tool; all
  reviewer confirmations remain pending, all variants remain held, promotion stays zero, both
  batch checks regenerate, and checksums are frozen.
  **Status:** Complete. Batch 02 is research only. No reviewer decision, stable catalog entity,
  canonical UUID, PostgreSQL row, runtime behavior, calibration input, or evaluation label changed.

- [x] **T38 — Apply project-owner priority-2 batch-02 decisions** `[backend]` _(R6, R16, R27, R29)_
  Record the owner's follow-up authorization as a separate decision file, validate all ten outcomes
  against the frozen T37 recommendations, preserve both earlier owner batches, and derive a third
  cumulative queue checkpoint without mutating any prior queue, catalog, or database.
  **Verify:** nine batch-02 `create_new_casting` decisions and the Batman hold complete under
  `project_owner`; the cumulative queue reports twenty-four completed / twenty-nine pending, four
  earlier merges, eighteen accepted new-family decisions, two holds, forty-six held release
  variants, three ordered decision batches, and zero promotion eligibility; changed outcomes and
  incomplete coverage fail closed; both batch-01 and batch-02 outputs regenerate with frozen hashes.
  **Status:** Complete. The owner decisions accept only casting-family outcomes. No stable catalog
  ID, canonical variant, PostgreSQL row, runtime result, calibration input, or evaluation label was
  created.

- [x] **T39 — Research priority-2 family batch 03 from the cumulative queue** `[backend]` _(R6, R16, R26, R28, R30)_
  Verify the T38 cumulative queue checksum, select the next ten still-pending priority-2 families,
  retain Wiki plus non-Fandom exact-name evidence, and record related-casting distinctions where a
  nearby or predecessor tool could otherwise be confused with the queued family.
  **Verify:** exactly ten families / eighteen Wiki rows are selected after all twenty-four completed
  decisions; all ten have a dedicated exact-name casting page plus independent corroboration and
  receive machine `create_new_casting` recommendations; Fiat 500e remains distinct from Fiat 500,
  and the newer Hirohata Merc remains distinct from the earlier differently named `'51 Merc` tool;
  all reviewer confirmations remain pending, every variant remains held, promotion stays zero,
  and all three research batches regenerate with frozen hashes.
  **Status:** Complete. Batch 03 is research only. No owner decision, stable catalog entity,
  canonical UUID, PostgreSQL row, runtime behavior, calibration input, or evaluation label changed.

- [x] **T40 — Apply project-owner priority-2 batch-03 decisions** `[backend]` _(R6, R16, R27, R29, R30)_
  After the project owner reviews the exact frozen T39 packet, record only the explicitly approved
  family outcomes in a separate attributable decision file and derive the next cumulative queue
  while preserving all prior decision history and variant holds.
  **Verify:** authorization covers all ten frozen packets exactly once and matches the approved
  outcome; prior twenty-four decisions remain unchanged; changed, incomplete, duplicate, or widened
  decisions fail closed; no stable catalog ID, PostgreSQL row, or promotion-eligible variant is
  created.
  **Status:** Complete. The owner's ten family-only approvals are recorded in a separate decision
  layer. No release variant, stable catalog ID, canonical UUID, PostgreSQL row, runtime result,
  calibration input, or evaluation label was created.

- [x] **T41 — Research priority-2 family batch 04 from the cumulative queue** `[backend]` _(R6, R16, R26, R28, R30)_
  Verify the T40 cumulative queue checksum and research the next ten of nineteen pending
  priority-2 families with the same dedicated-page, independent exact-name, homonym, and related-
  lineage safeguards.
  **Verify:** completed families are skipped; exactly the next bounded queue slice is represented;
  source observations and hashes are frozen; reviewer confirmation remains pending; every release
  variant stays held; and earlier research and decision artifacts reproduce unchanged.
  **Status:** Complete. Eight families receive machine creation recommendations; Mazda MX-5 Miata
  and Nissan Skyline 2000GT-R LBWK remain held at family scope because their display names span
  separate same-scale casting tools. No owner decision or catalog/database/runtime data changed.

- [ ] **T42 — Apply project-owner priority-2 batch-04 decisions** `[backend]` _(R6, R16, R27, R29, R30)_
  After the owner reviews the exact frozen T41 packet, record only the explicitly approved eight-
  create/two-hold family outcomes in a separate attributable decision file and append the result to
  cumulative history without widening variant scope.
  **Verify:** all ten research packets are covered exactly once; outcomes match authorization; all
  prior decisions and history remain unchanged; altered, incomplete, duplicate, or widened batches
  fail closed; all twenty-three current release rows remain held; promotion stays zero.
  **Status:** Pending the project owner's review. Machine research must not be converted into owner
  decisions automatically.

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
